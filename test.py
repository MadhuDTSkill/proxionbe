from typing import TypedDict, List, Literal, Dict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models.base import LanguageModelInput
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool, BaseTool
from typing import Annotated
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_community.document_loaders import UnstructuredURLLoader
import re
from duckduckgo_search.exceptions import RatelimitException


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

@tool("Developer Biography")
def developer_biography_tool() -> str:
    """
    Returns Developer Biography.

    Returns:
        str: A detailed biography of Madhu.
    """
    biography = """
    Madhu Bagamma Gari is an innovative Python Full Stack Developer with a passion for building advanced applications. Born on 28th March 2000 in Velgode, Nandyal District, Andhra Pradesh, India, Madhu is currently single.

    He completed a Bachelor of Science in Computer Science with a CGPA of 7.5 in December 2021. Madhu's skill set includes Python, Pandas, Data Structures, Numpy, Beautiful Soup, Django, Django ORM, Django Rest Framework, Django Channels (Websockets), MySQL, PostgreSQL, MongoDB, and React.js. He has also developed expertise in generative AI, focusing on utilizing open-source LLM models for creating intelligent applications.

    Currently, Madhu is the lead developer of **Proxima**, a cutting-edge platform similar to ChatGPT that leverages open-source LLM models. The name "Proxima" reflects his fascination with cosmology and is inspired by the Proxima Centauri star system, which captures his interest in the mysteries of the universe.

    Madhu has a deep interest in:
    1. **Cosmology**: Fascinated by the universe, he loves exploring theories about space and time.
    2. **Science Fiction Movies**: Enjoys films that challenge the boundaries of science and imagination, particularly **Prometheus**, which is his favorite Hollywood movie.
    3. **Treasure Hunting**: Captivated by adventure films, especially treasure hunting stories like **Sahasam** from Tollywood.
    4. **AI Ethics**: Advocating for responsible AI use and transparency in AI systems.
    5. **Game Development**: Exploring the intersection of AI and gaming, with plans for a simple game project.
    6. **Community Building**: Actively participates in local tech meetups to foster knowledge sharing and networking among developers.
    7. **Music Production**: Enjoys creating music and experimenting with sound engineering during his free time.
    8. **Traveling**: A passionate traveler, he documents his adventures through vlogs and blogs, sharing insights about different cultures.
    9. **Volunteering**: Engages in various social causes, particularly focusing on education for underprivileged children.
    10. **Fitness Enthusiast**: Regularly practices yoga and jogging to maintain a balanced lifestyle and improve mental health.

    In his free time, Madhu enjoys browsing tech innovations, gaming, and coding, always seeking to learn more about the latest advancements in technology.
    """
    return biography

@tool("Calculator")
def calculator_tool(expression: Annotated[str, "A string containing a mathematical expression"]) -> float:
    """
    Evaluates a basic arithmetic expression and returns the result.
        
    Returns:
        float: The result of the evaluated expression or an error message if invalid.
    """
    # Regular expression to match valid expressions
    valid_pattern = r'^[\d\s+\-*/().]+$'
    
    # Validate the expression
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
    is_valid: bool
    user_query: str
    sections: List[str]
    selected_mode: Literal["Casual", "Scientific", "Story"]
    generated_response: str
    tool_responses : Dict[str, str]
    refined_response: str
    final_response: str
    is_satisfactory: bool
    feedback: str

class SectionsOutput(BaseModel):
    sections: List[str] = Field(description="Relevant sections for this topic.")
    
class ValidationOutput(BaseModel):
    is_valid: bool = Field(description="Indicates if the user query is related to cosmology or asking about chatbot name or developer details.")
    response: str = Field(description="If the query is not related to cosmology or asking about chatbot name or developer details, this response informs the user about the model’s purpose. It provides a clear message that the model is specifically designed for answering cosmology-related questions. If the query is a greeting or farewell, it responds accordingly with an appropriate greeting or farewell message.")
    
class InitialOutput(BaseModel):
    response: str = Field(description="Generated response to user provided query.")

class ResponseFeedback(BaseModel):
    is_satisfactory: bool = Field(description="Indicates if the response is scientifically accurate and complete.")
    feedback: str = Field(description="Feedback on how to improve the answer if needed.")

class ProxionWorkflow:
    def __init__(self, llm : ChatGroq, verbose=False):
        self.llm : ChatGroq = llm
        self.verbose = verbose
        self.tools : List[BaseTool] = [wikipedia_tool, calculator_tool, web_url_tool, developer_biography_tool, duckduckgo_search_tool]
        
        self.validation = self.llm.with_structured_output(ValidationOutput)
        self.section_generator = self.llm.with_structured_output(SectionsOutput)
        self.initial_output = self.llm.with_structured_output(InitialOutput)
        self.evaluator = self.llm.with_structured_output(ResponseFeedback)
        self.knowledge_retriever = self.llm.bind_tools(self.tools)
        self.workflow = self._build_workflow()

        graph_png = self.workflow.get_graph(xray=True).draw_mermaid_png()
        image_file = "ProxionWorkflow.png"
        with open(image_file, "wb") as file:
            file.write(graph_png)

    def _verbose_print(self, message: str):
        if self.verbose:
            print(f"\033[92m[VERBOSE] {message}\033[0m")
            
    
    def _get_history(self):
        return [
            HumanMessage(content="What is black hole?"),
            AIMessage(content= "Introduction to Black Holes: A black hole is a region in space where the gravitational pull is so strong that nothing, including light, can escape. It is formed when a massive star collapses in on itself, causing a massive amount of matter to be compressed into an incredibly small space, resulting in an intense gravitational field. Gravity and Attraction: The gravity of a black hole is so strong because it is directly related to the mass and density of the object. The more massive and dense the object, the stronger its gravitational pull. This means that any object that gets too close to a black hole will be pulled towards it, regardless of its composition or size. Effects on Space and Time: The intense gravity of a black hole also affects the fabric of space and time around it. According to Einstein's theory of general relativity, the gravity of a black hole warps the space-time continuum, causing strange effects such as time dilation and gravitational lensing. Comparison to Other Celestial Objects: Black holes are often compared to other celestial objects such as neutron stars and white dwarfs, but they are unique in their ability to warp space and time. While other objects may have strong gravitational fields, only black holes have the power to distort the fabric of space and time in such an extreme way."),
            HumanMessage(content="Is that powerful ?"),
            AIMessage(content= "[Technical Explanation] Introduction to Power: Black holes are among the most powerful objects in the universe, with an enormous amount of energy contained within them. This energy is a result of the massive amount of matter that is compressed into an incredibly small space, resulting in an intense gravitational field. Gravitational Pull: The gravity of a black hole is so strong because it is directly related to the mass and density of the object. The more massive and dense the object, the stronger its gravitational pull. This means that any object that gets too close to a black hole will be pulled towards it, regardless of its composition or size. Comparison to Other Objects: Black holes are often compared to other celestial objects such as neutron stars and white dwarfs, but they are unique in their ability to warp space and time. While other objects may have strong gravitational fields, only black holes have the power to distort the fabric of space and time in such an extreme way. Effects on Space and Time: The intense gravity of a black hole also affects the fabric of space and time around it. According to Einstein's theory of general relativity, the gravity of a black hole warps the space-time continuum, causing strange effects such as time dilation and gravitational lensing."),
        ]
            
    def _get_message(self, new_message : str):
        messages = [
            SystemMessage(content="You are Proxion, an AI by Madhu Sunil, specialized in cosmology and space sciences. Answer only related questions, acknowledge uncertainties, avoid speculation, and adapt explanations based on user knowledge. Keep responses concise, accurate, and engaging while encouraging scientific curiosity."),
            *self._get_history(),
            HumanMessage(content=new_message)
        ]
        return messages

    def _build_workflow(self):
        builder = StateGraph(State)
        
        # Updating node names to be more descriptive
        builder.add_node("Query Validation", self.validate_query)
        builder.add_node("Generate Relevant Sections", self.generate_sections)
        builder.add_node("Generate Initial Response", self.multi_step_thinking)
        builder.add_node("Apply Explanation Mode", self.apply_explanation_mode)
        builder.add_node("Evaluate Response Quality", self.evaluate_response)
        builder.add_node("Refine Response", self.refine_response)
        builder.add_node("Retrieve Knowledge & Tool Insights", self.extra_knowledge)
        builder.add_node("Finalize and Provide Response", self.final_response)

        builder.add_edge(START, "Query Validation")
        builder.add_edge("Generate Relevant Sections", "Generate Initial Response")
        builder.add_edge("Generate Initial Response", "Apply Explanation Mode")
        builder.add_edge("Apply Explanation Mode", "Evaluate Response Quality")
        builder.add_edge("Refine Response", "Evaluate Response Quality")
        builder.add_edge("Retrieve Knowledge & Tool Insights", "Refine Response")
        builder.add_edge("Finalize and Provide Response", END)

        builder.add_conditional_edges(
            "Query Validation",
            lambda state: "No Further Processing" if not state["is_valid"] else "Proceed with Response Generation",
            {"No Further Processing": END, "Proceed with Response Generation": "Generate Relevant Sections"}
        )

        builder.add_conditional_edges(
            "Evaluate Response Quality",
            lambda state: "Needs Refinement" if not state["is_satisfactory"] else "Response is Final",
            {"Needs Refinement": "Retrieve Knowledge & Tool Insights", "Response is Final": "Finalize and Provide Response"}
        )

        return builder.compile()

    
    def validate_query(self, state: State) -> dict:
        self._verbose_print("Validating user query.")
        result : ValidationOutput = self.validation.invoke(self._get_message(f"Is the query '{state['user_query']}' related to cosmology or asking about chatbot name or developer details?"))
        self._verbose_print(f"Validation Result: {result.is_valid}")
        return {"is_valid": result.is_valid, "final_response": result.response}

    def generate_sections(self, state: State) -> dict:
        self._verbose_print("Generating sections for the given query.")
        result : SectionsOutput = self.section_generator.invoke(self._get_message(
            f"Break down the topic '{state['user_query']}' into key sections."
        ))
        self._verbose_print(f"Generated Sections: {result.sections}")
        return {"sections": result.sections}

    def multi_step_thinking(self, state: State) -> dict:
        self._verbose_print("Generating response using structured sections.")
        sections_text = " ".join([f"Section: {s}" for s in state["sections"]])
        response : InitialOutput = self.initial_output.invoke(self._get_message(f"Using the following sections, generate a well-structured response: {sections_text}"))
        self._verbose_print(f"Generated Response: {response.response}")
        return {"generated_response": response.response}
    
    def apply_explanation_mode(self, state: State) -> dict:
        base_response = state["generated_response"]
        mode = state.get("selected_mode", "Casual")
        
        # Define different explanation prompts
        explanation_prompts = {
            "Scientific": f"Provide a technical and detailed explanation of the following response with precise terminology and a formal tone:\n\n{base_response}",
            "Story": f"Transform the following response into an engaging and imaginative story format:\n\n{base_response}",
            "Casual": f"Rephrase the following response in a friendly, easy-to-understand manner suitable for everyday conversation:\n\n{base_response}"
        }
        
        if mode in explanation_prompts:
            self._verbose_print(f"Re-invoking model for {mode} mode.")
            modified_response = self.llm.invoke(self._get_message(explanation_prompts[mode]))
            modified_response = modified_response.content
        else:
            modified_response = base_response  # Default to original response if mode is not recognized

        self._verbose_print(f"Applied Mode ({mode}): {modified_response}")
        return {"refined_response": modified_response}


    def evaluate_response(self, state: State) -> dict:
        self._verbose_print("Evaluating response for accuracy and Markdown formatting.")

        evaluation_prompt = (
            f"Evaluate the following response for accuracy and completeness. Also, ensure that the response follows proper Markdown formatting "
            f"with correct usage of headings, lists, code blocks (if needed), and inline formatting.\n\n"
            f"Response:\n{state['refined_response']}\n\n"
            f"Return feedback on both the response quality and Markdown structure."
        )
        
        evaluation : ResponseFeedback = self.evaluator.invoke(self._get_message(evaluation_prompt))

        self._verbose_print(f"Evaluation Result: {evaluation.is_satisfactory}, Feedback: {evaluation.feedback}")

        return {"is_satisfactory": evaluation.is_satisfactory, "feedback": evaluation.feedback}

    def extra_knowledge(self, state: State) -> dict:
        self._verbose_print("Fetching additional knowledge for the given query.")
        
        user_query = state["user_query"]
        refined_response = state["refined_response"]
        feedback = state.get["feedback"]
        
        # Constructing the query for the knowledge retriever
        retrieval_prompt = (
            f"Given the following user query:\n\n"
            f"{user_query}\n\n"
            f"And the refined response:\n\n"
            f"{refined_response}\n\n"
            f"Along with feedback: {feedback}\n\n"
            f"What additional knowledge or tool call suggestions would improve this response?"
        )

        response = self.knowledge_retriever.invoke(self._get_message(retrieval_prompt))
        tools_by_name = {tool.name: tool for tool in self.tools}
        tool_responses = {}

        for tool_call in response.tool_calls:
            tool = tools_by_name[tool_call["name"]]
            observation = tool.invoke(tool_call["args"])
            tool_responses[tool_call["name"]] = observation
            self._verbose_print(f"{tool_call['name']} Tool Response: \n\n {observation}")

        return {"tool_responses": tool_responses}
        
    def refine_response(self, state: State) -> dict:
        self._verbose_print("Refining response based on feedback and tool responses.")

        tool_responses = state.get("tool_responses", {})
        tool_responses_text = "\n".join([f"{tool}: {response}" for tool, response in tool_responses.items()])

        refinement_prompt = (
            f"Refine the following response:\n\n"
            f"{state['refined_response']}\n\n"
            f"Based on the feedback: {state['feedback']}\n\n"
            f"And using the following tool responses:\n{tool_responses_text}"
        )

        improved = self.llm.invoke(self._get_message(refinement_prompt))
        
        self._verbose_print(f"Refined Response: {improved.content}")
        return {"refined_response": improved.content}

    
    def final_response(self, state: State) -> dict:
        return {"final_response": state["refined_response"]}

    def run(self, user_query: str, selected_mode: str = "Casual") -> str:
        initial_state = {"user_query": user_query, "selected_mode": selected_mode}
        final_state = self.workflow.invoke(initial_state)
        return final_state["final_response"]

# -------------------------------
# Example Usage
# -------------------------------


llm_instance = ChatGroq(model="llama-3.3-70b-versatile")

proxion = ProxionWorkflow(llm_instance, verbose=True)
# answer = proxion.run("How it forms ?", selected_mode="Scientific")
# print("\n\nProxion:", answer)
