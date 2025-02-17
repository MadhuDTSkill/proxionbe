import time
import groq
from typing import List
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from .prompts import PROXION_SYSTEM_MESSAGE, PROXION_THINKING_PROMPT
from .schemas import WorkFlowState, CosmologyQueryCheck, ThinkingOutput
from .tools import wikipedia_tool, calculator_tool, web_url_tool, duckduckgo_search_tool
from chats_app.models import Chat
from auth_app.models import User
from .memory import Memory



class ProxionThinkWorkflow:
    def __init__(self, chat : Chat, user : User, consumer : object, llm : ChatGroq, tool_llm_instance : ChatGroq = None, verbose=True):
        self.chat = chat
        self.user = user
        self.consumer = consumer
        self.llm : ChatGroq = llm
        self.memory = Memory.get_memory(str(chat.id), str(self.user.id), 3000, self.llm, True, False, 'human')
        self.tool_llm : ChatGroq = tool_llm_instance if tool_llm_instance else llm
        self.verbose = verbose
        self.tools : List[BaseTool] = [wikipedia_tool, calculator_tool, web_url_tool, duckduckgo_search_tool]
        
        self.cosmology_query_check = self.llm.with_structured_output(CosmologyQueryCheck, method="json_mode")
        self.thinking = self.llm.with_structured_output(ThinkingOutput, method="json_mode")
        self.knowledge_retriever = self.tool_llm.bind_tools(self.tools)
        
        

    async def _verbose_print(self, message: str, state : WorkFlowState):
        if self.verbose:
            print(f"\n\033[92m[VERBOSE] {message}\033[0m")


    async def _yield_status(self, message : str, state : WorkFlowState):
        from helper.consumers import BaseChatAsyncJsonWebsocketConsumer
        consumer : BaseChatAsyncJsonWebsocketConsumer = state['_consumer']
        await consumer.send_status(message)

    
    async def _get_history(self):
        return self.memory.messages
      
            
    async def _get_messages(self, new_message : str):
        history = await self._get_history()
        messages = [
            SystemMessage(content=PROXION_SYSTEM_MESSAGE),
            *history,
            HumanMessage(content=new_message)
        ]        
        return messages


    async def _build_workflow(self):
        builder = StateGraph(WorkFlowState)
        
        
        builder.add_node("Query Validation", self.validate_query)
        builder.add_node("Internal Thinking" , self.internal_thinking)
        builder.add_node("Generate Initial Response" , self.initial_response)
        builder.add_node("Generate Extra Knowledge", self.extra_knowledge)
        builder.add_node("Apply Explanation Mode", self.apply_explanation_mode)
        builder.add_node("Finalize and Provide Response", self.final_response)

        builder.add_edge(START, "Query Validation")
        builder.add_edge("Generate Extra Knowledge", "Generate Initial Response")
        builder.add_edge("Generate Initial Response", "Apply Explanation Mode")
        builder.add_edge("Apply Explanation Mode", "Finalize and Provide Response")
        builder.add_edge("Finalize and Provide Response", END)
        
        builder.add_conditional_edges(
            "Query Validation",
            lambda state: "Unreleted To Cosmology" if not state["is_cosmology_related"] else "Releted To Cosmology",
            {"Unreleted To Cosmology": "Finalize and Provide Response", "Releted To Cosmology": "Internal Thinking"}
        )
        
        builder.add_conditional_edges(
            "Internal Thinking",
            lambda state: "No Extra Knowledge is needed" if not state["requires_tool_call"] else "Extra Knowledge is needed",
            {"No Extra Knowledge is needed": "Generate Initial Response", "Extra Knowledge is needed": "Generate Extra Knowledge"}
        )

        return builder.compile()


    async def validate_query(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Validating user query.", state)
        await self._yield_status("🔍 Validating query...", state)
        
        
        query_prompt = (
            f"Validate if the query '{state['user_query']}' is related to cosmology or "
            f"asking about chatbot name or developer details. "
            "Respond in JSON format with the following keys:\n"
            "- `is_cosmology_related` (bool): Indicates whether the query is valid.\n"
            "- `response` (str): If the query is not related to cosmology:\n"
            "  - For greetings (e.g., 'Hi', 'Hello'), respond warmly (e.g., 'Hi! How can I assist you today? 😊').\n"
            "  - For farewells (e.g., 'Goodbye', 'See you'), respond appropriately (e.g., 'Goodbye! Have a great day!').\n"
            "  - For chatbot-related queries (e.g., 'Who are you?'), provide relevant details (e.g., 'I am Proxion, an AI assistant created by Madhu Bagamma Gari, specializing in cosmology and space sciences.').\n"
            "  - For completely unrelated questions (e.g., 'Who is Modi?'), politely inform the user that Proxion only focuses on cosmology (e.g., 'I focus only on cosmology-related topics. Let’s talk about the wonders of the universe!').\n"
        )

        result: CosmologyQueryCheck = await self.cosmology_query_check.ainvoke(await self._get_messages(query_prompt))

        return {
            "is_cosmology_related": result.is_cosmology_related, 
            "refined_response": result.response
        }


    async def internal_thinking(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Performing internal thinking.", state)        
        await self._yield_status("⏳ Thinking...", state)
        
        execution_prompt = f"""
            {PROXION_THINKING_PROMPT.format(
                user_query=state["user_query"]
            )}
            
            Once the internal thoughts are generated, return the response in JSON format with the following keys:

            - "thoughts": A detailed explanation of your internal thoughts and discussion on the user's query.
            - "requires_tool_call": A boolean value indicating whether an external tool call is needed (e.g., if real-time data, sources, or external knowledge are required to enhance the response).    
            
        """
        response : ThinkingOutput = await self.thinking.ainvoke(await self._get_messages(execution_prompt))

        await self._verbose_print("Internal thinking completed.", state)

        return {
            "thoughts": response.thoughts,
            "requires_tool_call": response.requires_tool_call,
        }


    async def extra_knowledge(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Fetching additional knowledge for the given query.", state)
        await self._yield_status("🔍 Fetching additional knowledge...", state)
        

        user_query = state["user_query"]
        sections = state["sections"]
        sections_text = ", ".join(sections)

        

        retrieval_prompt = (
            f"Given the following user query:\n\n"
            f"{user_query}\n\n"
            f"And the Topic breakdown sections:\n\n"
            f"{sections_text}\n\n"
            f"What additional knowledge or tool call suggestions would improve this response?"
        )        

        response = self.knowledge_retriever.ainvoke(await self._get_messages(retrieval_prompt))
        tools_by_name = {tool.name: tool for tool in self.tools}
        tool_responses = {}

        for tool_call in response.tool_calls:
            tool = tools_by_name.get(tool_call["name"])
            if not tool:
                
                continue

            retries = 3
            for attempt in range(1, retries + 1):
                try:
                    

                    observation = await tool.ainvoke(tool_call["args"])  
                    tool_responses[tool_call["name"]] = observation

                    
                    break  

                except groq.BadRequestError:
                    

                    if attempt == retries:
                        error_message = f"Error: Tool invocation failed after {retries} attempts."
                        tool_responses[tool_call["name"]] = error_message        

        return {"tool_responses": tool_responses}

    
    async def initial_response(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Generating response.", state)
        await self._yield_status("📝 Generating initial response...", state)

        user_query = state["user_query"]
        previous_thoughts = state.get("thoughts", "No previous thoughts generated.")
        tool_responses = state.get("tool_responses", {})

        if tool_responses:
            tool_responses_text = "\n".join(f"{tool}: {response}" for tool, response in tool_responses.items())
        else:
            tool_responses_text = "No additional tool responses available."

        prompt = (
            f"User Query: {user_query}\n\n"
            f"Additional tool responses:\n{tool_responses_text}\n\n"
            f"Previous internal thoughts & discussions:\n{previous_thoughts}\n\n"
            f"Generate a detailed response based on the user query and incorporate previous thoughts and tool responses."
        )


        try:
            response = await self.llm.ainvoke(await self._get_messages(prompt))
            generated_response = response.content
        except Exception as e:
            generated_response = f"Error: Unable to generate a response due to {str(e)}."

        return {"generated_response": generated_response}


    async def apply_explanation_mode(self, state: WorkFlowState) -> dict:
        base_response = state.get("generated_response", "No response available.")
        user_query = state.get("user_query", "No query provided.")
        mode = state.get("selected_mode", "Casual")
        
        await self._yield_status(f"💡 Applying explanation mode: {mode}...", state)
        

        explanation_prompts = {
            "Scientific": (
                f"User Query: {user_query}\n\n"
                f"Provide a technical and detailed explanation of the following response with precise terminology and a formal tone:\n\n{base_response}"
            ),
            "Story": (
                f"User Query: {user_query}\n\n"
                f"Transform the following response into an engaging and imaginative story format:\n\n{base_response}"
            ),
            "Casual": (
                f"User Query: {user_query}\n\n"
                f"Rephrase the following response in a friendly, easy-to-understand manner suitable for everyday conversation:\n\n{base_response}"
            ),
            "Kids": (
                f"User Query: {user_query}\n\n"
                f"Explain the following response in a very simple and fun way so that a child can understand. Use short sentences and easy words with emojis:\n\n{base_response}"
            ),
        }

        await self._verbose_print(f"Re-invoking model for {mode} mode.", state)

        response = await self.llm.ainvoke(await self._get_messages(explanation_prompts[mode]))
        modified_response = response.content

        return {"refined_response": modified_response}


    async def final_response(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Generating final response...", state)
        await self._yield_status("✅ Generating final response...", state)
        
        final_response = {
            "chat": str(self.chat.id),
            "prompt": state["user_query"],
            "response": state["refined_response"],
            "tool_responses": state.get("tool_responses", {}),
            "is_thoughted": state.get("is_cosmology_related", False),
            "thinked_thoughts": state.get("thoughts", "No thoughts generated."),
        }
        return {"final_response": final_response}


    async def ainvoke(self, user_query: str, selected_mode: str = "Casual") -> str:
        self.memory.add_user_message(user_query)
        initial_state = {
            "user_query": user_query, 
            "selected_mode": selected_mode,
            "_consumer" : self.consumer,
            "thoughts" : str()
        }
        start_time = time.time()

        await self._verbose_print(f"Running with user query: {user_query} and selected mode: {selected_mode}", initial_state)
        final_state = await self.workflow.ainvoke(initial_state)

        end_time = time.time()
        time_taken = round(end_time - start_time, 2)
        final_state["final_response"]["time_taken"] = time_taken
        self.memory.add_ai_message(final_state["final_response"]["response"])
        return final_state["final_response"]
   
    
    async def get_flow_image(self):
        graph_png = self.workflow.get_graph(xray=True).draw_mermaid_png()
        image_file = "ProxionThinkWorkflow.png"
        with open(image_file, "wb") as file:
            file.write(graph_png)
            
        print(f"Graph saved as {image_file}")
        
        
    @classmethod
    async def init_graph(cls, *args, **kwargs):
        graph = cls(*args, **kwargs)
        graph.workflow = await graph._build_workflow()
        await graph.get_flow_image()
        return graph

        
