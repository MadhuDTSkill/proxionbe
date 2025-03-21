import groq
from typing import TypedDict, List, Literal, Dict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool, BaseTool
from typing import Annotated
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_community.document_loaders import UnstructuredURLLoader
import re
from duckduckgo_search.exceptions import RatelimitException


PROXION_SYSTEM_MESSAGE = (
                "You are Proxion, an AI developed by Madhu Bagamma Gari, a Python Full Stack Generative AI Developer. "
                "Proxion specializes in cosmology and space sciences, providing accurate and engaging responses based on scientific principles."
                "\n\n"
                "## Capabilities:\n"
                "- Understands & generates Markdown-formatted responses (headings, lists, code blocks).\n"
                "- Adapts explanations based on user expertise (beginner, intermediate, advanced).\n"
                "- Encourages scientific curiosity and deeper exploration.\n"
                "\n\n"
                "## Handling Speculative Questions:\n"
                "- If a query involves speculation, Proxion provides scientifically accepted theories while avoiding unfounded claims.\n"
                "- Acknowledges uncertainties where necessary.\n"
                "\n\n"
                "## Why Proxion Exists:\n"
                "Madhu envisions AI as a bridge between humanity and the universe, providing accessible knowledge about space \n"
                "and fostering scientific curiosity through intelligent conversation.\n"
                "\n\n"
                "## Conversational Style:\n"
                "- Uses curiosity-driven language (e.g., 'That’s a fascinating question! Let’s explore it scientifically.')\n"
                "- Encourages further learning (e.g., 'Would you like to learn about related topics, such as dark matter?')\n"
            )


@tool("Wikipedia")
def wikipedia_tool(query: Annotated[str, "The search term to find relevant information from Wikipedia."]) -> str:
    """
    Retrieves a summary from Wikipedia based on the provided query.

    Returns:
        str: A brief summary of the information retrieved from Wikipedia.
    """
    api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=2000)
    wiki = WikipediaQueryRun(api_wrapper=api_wrapper)
    return wiki.run(query)


@tool("DuckDuckGo")
def duckduckgo_search_tool(query: Annotated[str, "The search term to find information from DuckDuckGo."]) -> str:
    """
    Searches the web using DuckDuckGo and returns the results.

    Returns:
        str: The search results obtained from DuckDuckGo or a rate limiting error message.
    """
    try:
        search = DuckDuckGoSearchRun(name="Search")
        return search.run(query)
    except RatelimitException:
        return "Failed to get context from the web due to rate limiting."


@tool("Web URL")
def web_url_tool(url: Annotated[str, "A single URL to retrieve content from."]) -> str:
    """
    Web Scrap the content from the given URL.

    Returns:
        str: A string summarizing the content retrieved from the URL.
    """
    if not url:
        return "No URL provided."

    loader: UnstructuredURLLoader = UnstructuredURLLoader(urls=[url])  
    docs: list = loader.load()  
    content: str = ""  

    for doc in docs:
        content += f"Content: {doc.page_content.strip()}\n\n"  
    return content  


@tool("Calculator")
def calculator_tool(expression: Annotated[str, "A string containing a mathematical expression"]) -> float:
    """
    Evaluates a basic arithmetic expression and returns the result.
        
    Returns:
        float: The result of the evaluated expression or an error message if invalid.
    """
    
    valid_pattern = r'^[\d\s+\-*/().]+$'
    
    
    if not re.match(valid_pattern, expression):
        return "Error: Invalid expression. Only numbers and +, -, *, / operators are allowed."
    
    try:
        # Evaluate the expression
        result = eval(expression)
        return result
    except Exception as e:
        return f"Error: {str(e)}"

# -------------------------------
# Define Data Schemas & State & LLMs
# -------------------------------

class State(TypedDict):
    is_cosmology_related: bool
    user_query: str
    sections: List[str]
    expansion_sections : List[str]
    selected_mode: Literal["Casual", "Scientific", "Story", "Kids"]
    generated_response: str
    tool_responses : Dict[str, str]
    refined_response: str
    final_response: str
    is_satisfactory: bool
    requires_tool_call : bool
    feedback: str


class SectionsOutput(BaseModel):
    sections: List[str] = Field(
        description="Relevant sections for this topic. The response will always contain general sections based on the user query. "
                    "If the question involves speculative ideas or hypotheses, additional perspectives will be appended: "
                    "Scientific View (scientific explanation based on physics and cosmology), "
                    "Theoretical View (hypotheses and speculative models), "
                    "Philosophical View (exploring meaning and existential implications), "
                    "Proxion View (AI-generated perspective creatively inferred from knowledge)."
    )
    
    
class CosmologyQueryCheck(BaseModel):
    is_cosmology_related: bool = Field(
        description="Indicates whether the user query is specifically related to cosmology. "
                    "If true, the query requires further processing to generate a detailed response. "
                    "If false, the query might be a greeting, farewell, or a general question about the chatbot (Proxion) itself, "
                    "which can be answered directly without additional refinement."
    )
    response: str = Field(
        description="If the query is not related to cosmology:\n"
                    "- For greetings (e.g., 'Hi', 'Hello'), respond warmly (e.g., 'Hi! How can I assist you today?').\n"
                    "- For farewells (e.g., 'Goodbye', 'See you'), respond appropriately (e.g., 'Goodbye! Have a great day!').\n"
                    "- For chatbot-related queries (e.g., 'Who are you?'), provide relevant details (e.g., 'I am Proxion, an AI assistant created by Madhu Bagamma Gari, specializing in cosmology and space sciences.').\n"
                    "- For completely unrelated questions (e.g., 'Who is Modi?'), politely inform the user that Proxion only focuses on cosmology (e.g., 'I focus only on cosmology-related topics. Let’s talk about the wonders of the universe!')."
    )
    requires_tool_call: bool = Field(
        description="Indicates whether external knowledge, real-time data, or the latest sources (e.g., Wikipedia, Arxiv, DuckDuckGo) "
                    "are required to enhance the response based on the user query."
    )
  

class ResponseFeedback(BaseModel):
    is_satisfactory: bool = Field(description="Indicates if the response is scientifically accurate and complete.")
    feedback: str = Field(description="Feedback on how to improve the answer if needed.")


class ProxionWorkflow:
    def __init__(self, llm : ChatGroq, tool_llm_instance : ChatGroq, verbose=False):
        self.llm : ChatGroq = llm
        self.tool_llm : ChatGroq = tool_llm_instance
        self.verbose = verbose
        self.tools : List[BaseTool] = [wikipedia_tool, calculator_tool, web_url_tool, duckduckgo_search_tool]
        
        self.cosmology_query_check = self.llm.with_structured_output(CosmologyQueryCheck, method="json_mode")
        self.section_generator = self.llm.with_structured_output(SectionsOutput, method="json_mode")
        self.evaluator = self.llm.with_structured_output(ResponseFeedback, method="json_mode")
        self.knowledge_retriever = self.tool_llm.bind_tools(self.tools)
        self.workflow = self._build_workflow()

        graph_png = self.workflow.get_graph(xray=True).draw_mermaid_png()
        image_file = "ProxionWorkflow.png"
        with open(image_file, "wb") as file:
            file.write(graph_png)

    def _verbose_print(self, message: str):
        if self.verbose:
            print(f"\n\033[92m[VERBOSE] {message}\033[0m")
            
    
    def _get_history(self):
        return [
            # HumanMessage(content="What is black hole?"),
            # AIMessage(content= "Introduction to Black Holes: A black hole is a region in space where the gravitational pull is so strong that nothing, including light, can escape. It is formed when a massive star collapses in on itself, causing a massive amount of matter to be compressed into an incredibly small space, resulting in an intense gravitational field. Gravity and Attraction: The gravity of a black hole is so strong because it is directly related to the mass and density of the object. The more massive and dense the object, the stronger its gravitational pull. This means that any object that gets too close to a black hole will be pulled towards it, regardless of its composition or size. Effects on Space and Time: The intense gravity of a black hole also affects the fabric of space and time around it. According to Einstein's theory of general relativity, the gravity of a black hole warps the space-time continuum, causing strange effects such as time dilation and gravitational lensing. Comparison to Other Celestial Objects: Black holes are often compared to other celestial objects such as neutron stars and white dwarfs, but they are unique in their ability to warp space and time. While other objects may have strong gravitational fields, only black holes have the power to distort the fabric of space and time in such an extreme way."),
            # HumanMessage(content="Is that powerful ?"),
            # AIMessage(content= "[Technical Explanation] Introduction to Power: Black holes are among the most powerful objects in the universe, with an enormous amount of energy contained within them. This energy is a result of the massive amount of matter that is compressed into an incredibly small space, resulting in an intense gravitational field. Gravitational Pull: The gravity of a black hole is so strong because it is directly related to the mass and density of the object. The more massive and dense the object, the stronger its gravitational pull. This means that any object that gets too close to a black hole will be pulled towards it, regardless of its composition or size. Comparison to Other Objects: Black holes are often compared to other celestial objects such as neutron stars and white dwarfs, but they are unique in their ability to warp space and time. While other objects may have strong gravitational fields, only black holes have the power to distort the fabric of space and time in such an extreme way. Effects on Space and Time: The intense gravity of a black hole also affects the fabric of space and time around it. According to Einstein's theory of general relativity, the gravity of a black hole warps the space-time continuum, causing strange effects such as time dilation and gravitational lensing."),
        ]
      
            
    def _get_messages(self, new_message : str):
        messages = [
            SystemMessage(content=PROXION_SYSTEM_MESSAGE),
            *self._get_history(),
            HumanMessage(content=new_message)
        ]
        return messages


    def _build_workflow(self):
        builder = StateGraph(State)
        
        
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


    def validate_query(self, state: State) -> dict:
        self._verbose_print("Validating user query.")

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

        result: CosmologyQueryCheck = self.cosmology_query_check.invoke(query_prompt)

        self._verbose_print(f"Needs Refinement : {'Yes' if result.is_cosmology_related else 'No'}")

        return {
            "is_cosmology_related": result.is_cosmology_related, 
            "final_response": result.response, 
            "requires_tool_call": result.requires_tool_call
        }


    def generate_sections(self, state: State) -> dict:
        self._verbose_print("Generating sections for the given query.")

        # Constructing a structured prompt to enforce JSON format
        query_prompt = (
            f"Break down the topic '{state['user_query']}' into key sections. "
            "Respond in JSON format with the following key: "
            "- `sections`: A list of section titles relevant to the topic."
        )

        # Invoking the section generator with structured output
        result: SectionsOutput = self.section_generator.invoke(query_prompt)

        self._verbose_print(f"Generated Sections: {result.sections}")

        return {"sections": result.sections}


    def extra_knowledge(self, state: State) -> dict:
        self._verbose_print("Fetching additional knowledge for the given query.")
        
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

        response = self.knowledge_retriever.invoke(self._get_messages(retrieval_prompt))
        tools_by_name = {tool.name: tool for tool in self.tools}
        tool_responses = {}

        for tool_call in response.tool_calls:
            tool = tools_by_name.get(tool_call["name"])
            if not tool:
                self._verbose_print(f"Warning: Tool '{tool_call['name']}' not found.")
                continue

            retries = 3
            for attempt in range(1, retries + 1):
                try:
                    observation = tool.invoke(tool_call["args"])
                    tool_responses[tool_call["name"]] = observation
                    self._verbose_print(f"{tool_call['name']} Tool Response: \n\n {observation}")
                    break  
                except groq.BadRequestError as e:
                    self._verbose_print(f"Attempt {attempt} failed for tool '{tool_call['name']}': {str(e)}")
                    if attempt == retries:
                        self._verbose_print(f"Max retries reached for tool '{tool_call['name']}'. Skipping...")
                        tool_responses[tool_call["name"]] = "Error: Tool invocation failed after 3 attempts."

        return {"tool_responses": tool_responses}


    def multi_step_thinking(self, state: State) -> dict:
        self._verbose_print("Generating response using structured sections.")
        
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

        response = self.llm.invoke(self._get_messages(prompt))
        
        self._verbose_print(f"Generated Response: {response.content}")
        
        return {"generated_response": response.content}


    def apply_explanation_mode(self, state: State) -> dict:
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
            self._verbose_print(f"Re-invoking model for {mode} mode.")
            modified_response = self.llm.invoke(self._get_messages(explanation_prompts[mode]))
            modified_response = modified_response.content
        else:
            modified_response = base_response  

        self._verbose_print(f"Applied Mode ({mode}): {modified_response}")
        return {"refined_response": modified_response}


    def evaluate_response(self, state: State) -> dict:
        self._verbose_print("Evaluating response for accuracy, completeness, and Markdown formatting.")

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

        evaluation: ResponseFeedback = self.evaluator.invoke(self._get_messages(evaluation_prompt))

        self._verbose_print(
            f"Evaluation Result: {evaluation.is_satisfactory}, "
            f"Feedback: {evaluation.feedback}"
        )

        return {
            "is_satisfactory": evaluation.is_satisfactory,
            "feedback": evaluation.feedback
        }


    def refine_response(self, state: State) -> dict:
        self._verbose_print("Refining response based on feedback and tool responses.")

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

        improved = self.llm.invoke(self._get_messages(refinement_prompt))
        
        self._verbose_print(f"Refined Response: {improved.content}")
        return {"refined_response": improved.content}

    
    def final_response(self, state: State) -> dict:
        self._verbose_print("Generating final response.")

        refined_response = state["refined_response"]
        return {"final_response": refined_response}


    def run(self, user_query: str, selected_mode: str = "Casual") -> str:
        self._verbose_print(f"Running with user query: {user_query} and selected mode: {selected_mode}")
        initial_state = {"user_query": user_query, "selected_mode": selected_mode}
        final_state = self.workflow.invoke(initial_state)
        return final_state["final_response"]

# -------------------------------
# Example Usage
# -------------------------------


# llm_instance = ChatGroq(model="llama-3.3-70b-versatile")
llm_instance = ChatGroq(model="llama3-70b-8192")
# llm_instance = ChatGroq(model="mixtral-8x7b-32768")
# llm_instance = ChatGroq(model="deepseek-r1-distill-llama-70b")

tool_llm_instance = ChatGroq(model="deepseek-r1-distill-llama-70b")

proxion = ProxionWorkflow(llm_instance, tool_llm_instance, verbose=True)
answer = proxion.run("Hi ?", selected_mode="Kids")
print("\n\nProxion:", answer)
