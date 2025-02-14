import groq
from typing import List
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool, BaseTool
from .prompts import PROXION_SYSTEM_MESSAGE
from .schemas import WorkFlowState, SectionsOutput, CosmologyQueryCheck, ResponseFeedback
from .tools import wikipedia_tool, calculator_tool, web_url_tool, duckduckgo_search_tool
from chats_app.models import Chat
from auth_app.models import User
from .memory import Memory



class ProxionWorkflow:
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
        self.section_generator = self.llm.with_structured_output(SectionsOutput, method="json_mode")
        self.evaluator = self.llm.with_structured_output(ResponseFeedback, method="json_mode")
        self.knowledge_retriever = self.tool_llm.bind_tools(self.tools)
        
        # graph_png = self.workflow.get_graph(xray=True).draw_mermaid_png()
        # image_file = "ProxionWorkflow.png"
        # with open(image_file, "wb") as file:
        #     file.write(graph_png)

    async def _verbose_print(self, message: str, state : WorkFlowState):
        if self.verbose:
            from helper.consumers import BaseChatAsyncJsonWebsocketConsumer
            consumer : BaseChatAsyncJsonWebsocketConsumer = state['_consumer']
            await consumer.send_status(message)
            print(f"\n\033[92m[VERBOSE] {message}\033[0m")
            
    
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
        builder.add_node("Generate Relevant Sections", self.generate_sections)
        builder.add_node("Generate Extra Knowledge", self.extra_knowledge)
        builder.add_node("Generate Initial Response", self.multi_step_thinking)
        builder.add_node("Apply Explanation Mode", self.apply_explanation_mode)
        builder.add_node("Evaluate Response Quality", self.evaluate_response)
        builder.add_node("Refine Response", self.refine_response)
        builder.add_node("Finalize and Provide Response", self.final_response)

        builder.add_edge(START, "Query Validation")
        builder.add_edge("Generate Extra Knowledge", "Generate Initial Response")
        builder.add_edge("Generate Initial Response", "Apply Explanation Mode")
        builder.add_edge("Apply Explanation Mode", "Evaluate Response Quality")
        builder.add_edge("Refine Response", "Evaluate Response Quality")
        builder.add_edge("Finalize and Provide Response", END)

        builder.add_conditional_edges(
            "Query Validation",
            lambda state: "Unreleted To Cosmology" if not state["is_cosmology_related"] else "Releted To Cosmology",
            {"Unreleted To Cosmology": END, "Releted To Cosmology": "Generate Relevant Sections"}
        )
        
        builder.add_conditional_edges(
            "Generate Relevant Sections",
            lambda state: "No Extra Knowledge is needed" if not state["requires_tool_call"] else "Extra Knowledge is needed",
            {"No Extra Knowledge is needed": "Generate Initial Response", "Extra Knowledge is needed": "Generate Extra Knowledge"}
        )
        
        builder.add_conditional_edges(
            "Evaluate Response Quality",
            lambda state: "Needs Refinement" if not state["is_satisfactory"]  else "Response is Final",
            {"Needs Refinement": "Refine Response", "Response is Final": "Finalize and Provide Response"}
        )

        return builder.compile()


    async def validate_query(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Validating user query.", state)

        # Constructing the structured prompt to enforce JSON format
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
            "- `requires_tool_call` (bool): Always include this field. If the query requires external data sources (e.g., real-time space data), set this to `true`. Otherwise, set it to `false`."
        )

        result: CosmologyQueryCheck = await self.cosmology_query_check.ainvoke(await self._get_messages(query_prompt))

        # await self._verbose_print(f"Needs Refinement : {'Yes' if result.is_cosmology_related else 'No'}", state)

        return {
            "is_cosmology_related": result.is_cosmology_related, 
            "final_response": {
                "chat": str(self.chat.id),
                "prompt": state["user_query"],
                "response": result.response,
                "tool_responses": state.get("tool_responses", {}),
            }, 
            "requires_tool_call": result.requires_tool_call
        }


    async def generate_sections(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Generating sections for the given query.", state)

        # Constructing a structured prompt to enforce JSON format
        query_prompt = (
            f"Break down the topic '{state['user_query']}' into key sections. "
            "Respond in JSON format with the following key: "
            "- `sections`: A list of section titles relevant to the topic."
        )

        # Invoking the section generator with structured output
        result: SectionsOutput = await self.section_generator.ainvoke(query_prompt)

        await self._verbose_print(f"Sections Generated ...", state)

        return {"sections": result.sections}


    async def extra_knowledge(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Fetching additional knowledge for the given query.", state)
        
        user_query = state["user_query"]
        sections = state["sections"]
        sections_text = ", ".join(sections)
        
        retrieval_prompt = (
            f"Given the following user query:\n\n"
            f"{user_query}\n\n"
            f"And the Topic break down sections:\n\n"
            f"{sections_text}\n\n"
            f"What additional knowledge or tool call suggestions would improve this response?"
        )

        response = self.knowledge_retriever.ainvoke(await self._get_messages(retrieval_prompt))
        tools_by_name = {tool.name: tool for tool in self.tools}
        tool_responses = {}

        for tool_call in response.tool_calls:
            tool = tools_by_name.get(tool_call["name"])
            if not tool:
                # self._verbose_print(f"Warning: Tool '{tool_call['name']}' not found.", state)
                continue

            retries = 3
            for attempt in range(1, retries + 1):
                try:
                    observation = tool.ainvoke(tool_call["args"])
                    tool_responses[tool_call["name"]] = observation
                    # self._verbose_print(f"{tool_call['name']} Tool Response: \n\n {observation}", state)
                    break  
                except groq.BadRequestError as e:
                    # await self._verbose_print(f"Attempt {attempt} failed for tool '{tool_call['name']}': {str(e)}", state)
                    if attempt == retries:
                        # self._verbose_print(f"Max retries reached for tool '{tool_call['name']}'. Skipping...", state)
                        tool_responses[tool_call["name"]] = "Error: Tool invocation failed after 3 attempts."

        return {"tool_responses": tool_responses}


    async def multi_step_thinking(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Generating response using structured sections.", state)
        
        user_query = state["user_query"]
        sections_text = ", ".join(state["sections"])
        tool_responses = state.get("tool_responses", {})        
        tool_responses_text = "\n".join([f"{tool}: {response}" for tool, response in tool_responses.items()]) or "No additional tool responses available."

        prompt = (
            f"User Query: {user_query}\n\n"
            f"Using the following sections, generate a well-structured response:\n\n"
            f"Sections: {sections_text}\n\n"
            f"Additional tool responses:\n{tool_responses_text}\n\n"
            f"Ensure the response integrates the tool responses appropriately while maintaining coherence."
        )

        response = await self.llm.ainvoke(await self._get_messages(prompt))
        
        # await self._verbose_print(f"Generated Response: {response.content}", state)
        
        return {"generated_response": response.content}


    async def apply_explanation_mode(self, state: WorkFlowState) -> dict:
        base_response = state["generated_response"]
        user_query = state["user_query"]  
        mode = state.get("selected_mode", "Casual")
        
        
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
                f"Explain the following response in a very simple and fun way so that a child can understand. Use short sentences and easy words with emojies:\n\n{base_response}"
            ),
        }
        
        if mode in explanation_prompts:
            self._verbose_print(f"Re-invoking model for {mode} mode.", state)
            modified_response = await self.llm.ainvoke(await self._get_messages(explanation_prompts[mode]))
            modified_response = modified_response.content
        else:
            modified_response = base_response  

        # await self._verbose_print(f"Applied Mode ({mode}): {modified_response}", state)
        return {"refined_response": modified_response}


    async def evaluate_response(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Evaluating response ...", state)

        user_query = state["user_query"]

        evaluation_prompt = (
            f"User Query: {user_query}\n\n"
            f"Evaluate the following response for accuracy, completeness, and relevance to the user query. "
            f"Ensure that the response follows proper Markdown formatting, including correct usage of headings, lists, "
            f"code blocks (if needed), and inline formatting.\n\n"
            f"Response:\n{state['refined_response']}\n\n"
            "Respond in JSON format with the following keys:\n"
            "- `is_satisfactory` (bool): Indicates whether the response meets quality standards.\n"
            "- `feedback` (str): Provides detailed feedback on response quality and Markdown structure.\n"
        )

        evaluation: ResponseFeedback = await self.evaluator.ainvoke(await self._get_messages(evaluation_prompt))

        # self._verbose_print(
        #     f"Evaluation Result: {evaluation.is_satisfactory} "
        #     # f"Feedback: {evaluation.feedback}",
        #     state
        # )

        return {
            "is_satisfactory": evaluation.is_satisfactory,
            "feedback": evaluation.feedback
        }


    async def refine_response(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Refining response ...", state)

        user_query = state["user_query"]  
        tool_responses = state.get("tool_responses", {})
        
        tool_responses_text = "\n".join([f"{tool}: {response}" for tool, response in tool_responses.items()]) or "No additional tool responses available."

        refinement_prompt = (
            f"User Query:\n{user_query}\n\n"
            f"Initial Response:\n{state['refined_response']}\n\n"
            f"Feedback:\n{state['feedback']}\n\n"
            f"Tool Responses:\n{tool_responses_text}\n\n"
            f"Refine the response based on the feedback and tool responses while ensuring it remains accurate, well-structured, and relevant to the user query."
        )

        improved = await self.llm.ainvoke(await self._get_messages(refinement_prompt))
        
        # await self._verbose_print(f"Refined Response: {improved.content}", state)
        return {"refined_response": improved.content}

    
    async def final_response(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Generating final response...", state)
        final_response = {
            "chat": str(self.chat.id),
            "prompt": state["user_query"],
            "response": state["refined_response"],
            "tool_responses": state.get("tool_responses", {}),
        }
        return {"final_response": final_response}


    async def ainvoke(self, user_query: str, selected_mode: str = "Casual") -> str:
        self.memory.add_user_message(user_query)
        initial_state = {
            "user_query": user_query, 
            "selected_mode": selected_mode,
            "_consumer" : self.consumer
        }
        # await self._verbose_print(f"Running with user query: {user_query} and selected mode: {selected_mode}", initial_state)
        final_state = await self.workflow.ainvoke(initial_state)
        self.memory.add_ai_message(final_state["final_response"]["response"])
        return final_state["final_response"]
    
    @classmethod
    async def init_graph(cls, *args, **kwargs):
        graph = cls(*args, **kwargs)
        graph.workflow = await graph._build_workflow()
        return graph
        
