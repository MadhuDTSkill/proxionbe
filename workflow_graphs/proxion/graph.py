import time
import groq
from typing import List
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
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
        self.thinked_thoughts = str()
        self.llm : ChatGroq = llm
        self.memory = Memory.get_memory(str(chat.id), str(self.user.id), 3000, self.llm, True, False, 'human')
        self.tool_llm : ChatGroq = tool_llm_instance if tool_llm_instance else llm
        self.verbose = verbose
        self.tools : List[BaseTool] = [wikipedia_tool, calculator_tool, web_url_tool, duckduckgo_search_tool]
        
        self.cosmology_query_check = self.llm.with_structured_output(CosmologyQueryCheck, method="json_mode")
        self.section_generator = self.llm.with_structured_output(SectionsOutput, method="json_mode")
        self.evaluator = self.llm.with_structured_output(ResponseFeedback, method="json_mode")
        self.knowledge_retriever = self.tool_llm.bind_tools(self.tools)
        
        
        
        
        

    async def _verbose_print(self, message: str, state : WorkFlowState):
        if self.verbose:
            print(f"\n\033[92m[VERBOSE] {message}\033[0m")


    async def _yield_status(self, message : str, state : WorkFlowState):
        from helper.consumers import BaseChatAsyncJsonWebsocketConsumer
        consumer : BaseChatAsyncJsonWebsocketConsumer = state['_consumer']
        await consumer.send_status(message)

            
    async def _record_thinked_thoughts(self, thought :str, state : WorkFlowState):
        if not thought.startswith('\n'):
           thought  = f"\n{thought}" 
        self.thinked_thoughts += thought      
    
    
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
        await self._yield_status("🔍 Validating query...", state)
        await self._record_thinked_thoughts("\nI need to validate this user query and check if it's relevant.", state)
        
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

        await self._yield_status("⏳ Processing query...", state)
        await self._record_thinked_thoughts("\nI have prepared the validation prompt. Now, I will send it for processing.", state)

        result: CosmologyQueryCheck = await self.cosmology_query_check.ainvoke(await self._get_messages(query_prompt))

        await self._yield_status("✅ Validation complete", state)
        await self._record_thinked_thoughts("\nI received the validation result. Now, let me analyze it.", state)
        await self._record_thinked_thoughts(
            "\nHere's what I found:\n"
            f"- Is this query related to cosmology? {'Yes' if result.is_cosmology_related else 'No'}\n"
            f"- Generated response: {result.response}\n"
            f"- Does this require a tool call? {'Yes' if result.requires_tool_call else 'No'}\n",
            state
        )

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
        await self._yield_status("📝 Generating sections...", state)
        await self._record_thinked_thoughts("\nI need to break down the given topic into key sections.", state)

        
        query_prompt = (
            f"Break down the topic '{state['user_query']}' into key sections. "
            "Respond in JSON format with the following key: "
            "- `sections`: A list of section titles relevant to the topic."
        )

        await self._yield_status("⏳ Processing query...", state)
        await self._record_thinked_thoughts("\nI have prepared the structured prompt. Now, I will send it for processing.", state)
        
        result: SectionsOutput = await self.section_generator.ainvoke(query_prompt)

        await self._yield_status("✅ Sections generated successfully!", state)
        await self._record_thinked_thoughts("\nI have received the generated sections. Let me store them.", state)
        await self._record_thinked_thoughts(
            "\nHere are the sections I generated:\n"
            f"{result.sections}\n",
            state
        )
        await self._verbose_print("Sections Generated.", state)

        return {"sections": result.sections}


    async def extra_knowledge(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Fetching additional knowledge for the given query.", state)
        await self._yield_status("🔍 Fetching additional knowledge...", state)
        await self._record_thinked_thoughts("\nI need to gather extra knowledge to enhance the response.", state)

        user_query = state["user_query"]
        sections = state["sections"]
        sections_text = ", ".join(sections)

        await self._record_thinked_thoughts("\nI have the user query and topic breakdown. Now, I will formulate the retrieval prompt.", state)

        retrieval_prompt = (
            f"Given the following user query:\n\n"
            f"{user_query}\n\n"
            f"And the Topic breakdown sections:\n\n"
            f"{sections_text}\n\n"
            f"What additional knowledge or tool call suggestions would improve this response?"
        )

        await self._yield_status("🔍 Retrieving additional knowledge...", state)
        await self._record_thinked_thoughts("\nThe retrieval prompt is ready. I will now send it for processing.", state)

        response = self.knowledge_retriever.ainvoke(await self._get_messages(retrieval_prompt))
        tools_by_name = {tool.name: tool for tool in self.tools}
        tool_responses = {}

        await self._record_thinked_thoughts("\nI have received tool call suggestions. Now, I will process each one.", state)
        await self._yield_status("🛠️ Processing tool call suggestions...", state)

        for tool_call in response.tool_calls:
            tool = tools_by_name.get(tool_call["name"])
            if not tool:
                await self._record_thinked_thoughts(f"\nThe requested tool '{tool_call['name']}' does not exist. Skipping this call.", state)
                continue

            retries = 3
            for attempt in range(1, retries + 1):
                try:
                    await self._record_thinked_thoughts(f"\nAttempting to invoke the tool '{tool_call['name']}' (Attempt {attempt}/{retries}).", state)

                    observation = await tool.ainvoke(tool_call["args"])  
                    tool_responses[tool_call["name"]] = observation

                    await self._record_thinked_thoughts(f"\nSuccessfully received response from '{tool_call['name']}'. \nResponse: {observation}", state)
                    break  

                except groq.BadRequestError:
                    await self._record_thinked_thoughts(f"\nTool '{tool_call['name']}' invocation failed on attempt {attempt}. Retrying...", state)

                    if attempt == retries:
                        error_message = f"Error: Tool invocation failed after {retries} attempts."
                        tool_responses[tool_call["name"]] = error_message

                        await self._record_thinked_thoughts(f"\nMaximum retries reached for '{tool_call['name']}'. Storing failure response: {error_message}", state)

        await self._yield_status("📚 Extra knowledge retrieval complete!", state)
        await self._record_thinked_thoughts("\nTool responses have been processed. Returning final results.", state)

        return {"tool_responses": tool_responses}

    
    async def multi_step_thinking(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Generating response using structured sections.", state)
        await self._yield_status("📝 Generating structured response...", state)
        await self._record_thinked_thoughts("\nI need to generate a structured response using the provided sections.", state)

        user_query = state["user_query"]
        sections = state.get("sections", [])
        sections_text = ", ".join(sections) if sections else "No specific sections provided."

        await self._yield_status("🔍 Checking tool responses...", state)
        await self._record_thinked_thoughts("\nI have the user query and the topic breakdown. Now, I will check for additional tool responses.", state)

        tool_responses = state.get("tool_responses", {})
        if tool_responses:
            tool_responses_text = "\n".join(f"{tool}: {response}" for tool, response in tool_responses.items())
        else:
            tool_responses_text = "No additional tool responses available."

        await self._yield_status("🏗️ Constructing final structured prompt...", state)
        await self._record_thinked_thoughts("\nI have gathered the tool responses. Now, I will construct the final structured prompt.", state)

        prompt = (
            f"User Query: {user_query}\n\n"
            f"Using the following sections, generate a well-structured response:\n\n"
            f"Sections: {sections_text}\n\n"
            f"Additional tool responses:\n{tool_responses_text}\n\n"
            f"Ensure the response integrates the tool responses appropriately while maintaining coherence."
        )

        await self._yield_status("🤖 Generating response with LLM...", state)
        await self._record_thinked_thoughts("\nThe final prompt is ready. Now, I will generate a response.", state)

        try:
            response = await self.llm.ainvoke(await self._get_messages(prompt))
            generated_response = response.content
        except Exception as e:
            generated_response = f"Error: Unable to generate a response due to {str(e)}."
            await self._record_thinked_thoughts(f"\nLLM invocation failed: {str(e)}", state)

        await self._yield_status("✅ Response generation completed.", state)
        await self._record_thinked_thoughts(f"\nResponse generation completed. Generated Response:\n\n{generated_response}", state)

        return {"generated_response": generated_response}


    async def apply_explanation_mode(self, state: WorkFlowState) -> dict:
        base_response = state.get("generated_response", "No response available.")
        user_query = state.get("user_query", "No query provided.")
        mode = state.get("selected_mode", "Casual")
        
        await self._yield_status(f"📝 Applying explanation mode: {mode}...", state)
        await self._record_thinked_thoughts(f"\nI need to modify the response based on the selected mode: {mode}.", state)

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

        if mode in explanation_prompts:
            
            await self._yield_status(f"💡 Generating {mode}-mode response...", state)
            await self._record_thinked_thoughts(f"\nI have identified the explanation mode ({mode}). Now, I will re-invoke the model.", state)
            await self._verbose_print(f"Re-invoking model for {mode} mode.", state)

            try:
                response = await self.llm.ainvoke(await self._get_messages(explanation_prompts[mode]))
                modified_response = response.content
                await self._yield_status(f"✅ {mode} transformation completed.", state)
                await self._record_thinked_thoughts(f"\nMode ({mode}) applied successfully. Transformed Response:\n\n{modified_response}", state)
            except Exception as e:
                modified_response = f"Error: Unable to apply {mode} mode due to {str(e)}."
                await self._record_thinked_thoughts(f"\nError applying {mode} mode: {str(e)}", state)
                await self._yield_status(f"❌ Failed to apply {mode} mode.", state)
        else:
            modified_response = base_response  
            await self._record_thinked_thoughts(f"\nThe selected mode ({mode}) is invalid. Keeping the original response.", state)
            await self._yield_status(f"⚠️ Invalid mode ({mode}). Keeping original response.", state)

        return {"refined_response": modified_response}


    async def evaluate_response(self, state: WorkFlowState) -> dict:
        await self._yield_status("🔍 Evaluating response...", state)

        user_query = state.get("user_query", "No query provided.")
        refined_response = state.get("refined_response", "No response available.")

        await self._record_thinked_thoughts("\nI need to evaluate the response for accuracy, completeness, and Markdown formatting.", state)

        evaluation_prompt = (
            f"User Query: {user_query}\n\n"
            f"Evaluate the following response for:\n"
            f"- Accuracy ✅\n"
            f"- Completeness 📚\n"
            f"- Relevance 🎯\n"
            f"- Proper Markdown formatting 📝 (headings, lists, inline code, code blocks if needed)\n\n"
            f"Response:\n{refined_response}\n\n"
            "Respond strictly in **JSON format** with the following keys:\n"
            "- `is_satisfactory` (bool): Indicates whether the response meets quality standards.\n"
            "- `feedback` (str): Provides detailed feedback on response quality and Markdown structure.\n"
        )

        try:
            
            await self._yield_status("🚀 Sending response for evaluation...", state)

            evaluation = await self.evaluator.ainvoke(await self._get_messages(evaluation_prompt))
            
            if not hasattr(evaluation, "is_satisfactory") or not hasattr(evaluation, "feedback"):
                raise ValueError("Invalid response format from evaluator.")

            await self._record_thinked_thoughts(f"\nEvaluation completed. Quality check result: {evaluation.is_satisfactory}", state)
            await self._yield_status("✅ Evaluation completed!", state)
            await self._verbose_print(f"Evaluation Result: {evaluation.is_satisfactory}\nFeedback:\n{evaluation.feedback}", state)

            return {
                "is_satisfactory": evaluation.is_satisfactory,
                "feedback": evaluation.feedback
            }
        
        except Exception as e:
            error_message = f"Error during evaluation: {str(e)}"
            
            await self._record_thinked_thoughts(f"\nEvaluation failed: {error_message}", state)
            await self._yield_status("❌ Evaluation failed. Check logs for details.", state)

            return {
                "is_satisfactory": False,
                "feedback": error_message
            }


    async def refine_response(self, state: WorkFlowState) -> dict:
        await self._yield_status("🔄 Refining response...", state)

        user_query = state.get("user_query", "No query provided.")
        initial_response = state.get("refined_response", "No response available.")
        feedback = state.get("feedback", "No feedback provided.")
        tool_responses = state.get("tool_responses", {})

        await self._record_thinked_thoughts("\nI need to refine the response based on feedback and tool responses.", state)
        
        if tool_responses:
            tool_responses_text = "\n".join([f"{tool}: {response}" for tool, response in tool_responses.items()])
        else:
            tool_responses_text = "**No additional tool responses available.**"

        refinement_prompt = (
            f"User Query:\n{user_query}\n\n"
            f"Initial Response:\n{initial_response}\n\n"
            f"Feedback on Response:\n{feedback}\n\n"
            f"Tool Responses:\n{tool_responses_text}\n\n"
            f"Instructions:\n"
            f"- Improve the response based on the provided feedback.\n"
            f"- Incorporate any relevant tool responses while ensuring factual accuracy.\n"
            f"- Maintain clarity, coherence, and structured formatting (Markdown where applicable).\n"
            f"- Ensure the final response remains highly relevant to the user query."
        )

        try:
            
            await self._yield_status("🚀 Sending refinement request...", state)

            improved_response = await self.llm.ainvoke(await self._get_messages(refinement_prompt))
            
            if not hasattr(improved_response, "content") or not improved_response.content.strip():
                raise ValueError("Invalid or empty response from LLM.")
            
            await self._record_thinked_thoughts("\nRefinement completed. Evaluating improvements.", state)
            await self._yield_status("✅ Refinement completed!", state)

            return {"refined_response": improved_response.content}

        except Exception as e:
            error_message = f"Refinement failed: {str(e)}. Retaining the previous response."

            await self._record_thinked_thoughts(f"\n{error_message}", state)
            await self._yield_status("❌ Refinement failed. Using the initial response.", state)

            return {"refined_response": initial_response}


    async def final_response(self, state: WorkFlowState) -> dict:
        await self._verbose_print("Generating final response...", state)
        await self._yield_status("✅ Generating final response...", state)
        
        final_response = {
            "chat": str(self.chat.id),
            "prompt": state["user_query"],
            "response": state["refined_response"],
            "tool_responses": state.get("tool_responses", {}),
            "is_thoughted": state.get("is_cosmology_related", False),
            "thinked_thoughts": self.thinked_thoughts,
        }
        return {"final_response": final_response}


    async def ainvoke(self, user_query: str, selected_mode: str = "Casual") -> str:
        self.memory.add_user_message(user_query)
        initial_state = {
            "user_query": user_query, 
            "selected_mode": selected_mode,
            "_consumer" : self.consumer,
        }
        start_time = time.time()

        await self._verbose_print(f"Running with user query: {user_query} and selected mode: {selected_mode}", initial_state)
        self.thinked_thoughts = str()
        final_state = await self.workflow.ainvoke(initial_state)

        end_time = time.time()
        time_taken = round(end_time - start_time, 2)
        final_state["final_response"]["time_taken"] = time_taken
        self.memory.add_ai_message(final_state["final_response"]["response"])
        return final_state["final_response"]
    
    
    async def get_flow_image(self):
        graph_png = self.workflow.get_graph(xray=True).draw_mermaid_png()
        image_file = "ProxionWorkflow.png"
        with open(image_file, "wb") as file:
            file.write(graph_png)
            
        print(f"Graph saved as {image_file}")
        
        
    @classmethod
    async def init_graph(cls, *args, **kwargs):
        graph = cls(*args, **kwargs)
        graph.workflow = await graph._build_workflow()
        await graph.get_flow_image()
        return graph
        
