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
    new_discussion: str
    is_discussion_done : str
    discussions : str
    generated_response: str
    refined_response: str
    final_response: str
    requires_tool_call : bool


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
  

class ResponseDiscussion(BaseModel): 
    """
    Represents the discussion response state, tracking the ongoing conversation and determining if further discussion is needed.
    """
    new_discussion: str = Field(..., description="The latest generated discussion text in response to the ongoing conversation.")
    is_discussion_done: bool = Field(..., description="Indicates whether the discussion has reached a satisfactory conclusion.")
    
    

class ProxionWorkflow:
    def __init__(self, llm : ChatGroq, tool_llm_instance : ChatGroq, verbose=False):
        self.llm : ChatGroq = llm
        self.tool_llm : ChatGroq = tool_llm_instance
        self.verbose = verbose
        self.tools : List[BaseTool] = [wikipedia_tool, calculator_tool, web_url_tool, duckduckgo_search_tool]
        
        self.discussion_llm = self.llm.with_structured_output(ResponseDiscussion, method="json_mode")
        self.knowledge_retriever = self.tool_llm.bind_tools(self.tools)
        self.workflow = self._build_workflow()

        graph_png = self.workflow.get_graph(xray=True).draw_mermaid_png()
        image_file = "ProxionWorkflow.png"
        with open(image_file, "wb") as file:
            file.write(graph_png)

    def _verbose_print(self, message: str, state = None):
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
        
        builder.add_node('Proxion', self.proxion_node)
        builder.add_node('Proxion Soul', self.proxion_soul_node)

        builder.add_edge(START, 'Proxion')
        
        builder.add_conditional_edges(
            'Proxion',
            lambda state: "Dicussion Is Done" if state['is_discussion_done'] else "Need More Discussion",
            {
                "Need More Discussion" :  'Proxion Soul',
                "Dicussion Is Done" : END
            }
        )
        
        builder.add_conditional_edges(
            'Proxion Soul',
            lambda state: "Dicussion Is Done" if state['is_discussion_done'] else "Need More Discussion",
            {
                "Need More Discussion" :  'Proxion',
                "Dicussion Is Done" : END
            }
        )
    
        return builder.compile()


    def proxion_node(self, state: State) -> dict:
        # self._verbose_print("Proxion Node: Generating discussion response.", state)

        execution_prompt = (
            f"User Query: {state['user_query']}\n"
            f"Discussion so far: {state['discussions']}\n"
            "Respond in the following JSON format:\n"
            "- `new_discussion` (str): Your contribution to the conversation, continuing from the previous discussion while adding or refining points.\n"
            "- `is_discussion_done` (bool): Set to True if the discussion feels complete, otherwise False.\n"
            "Respond with a direct continuation of the conversation. Do not acknowledge the previous response, just continue by:\n"
            "- Evaluating the last point discussed.\n"
            "- Asking relevant doubts or making necessary corrections.\n"
            "- Ensuring the discussion progresses toward resolving the user's query.\n"
            "Do not praise or acknowledge the other node's response. Be focused on solving the query.\n"
            "Once you think the discussion is complete, set `is_discussion_done` to True."
        )

        response : ResponseDiscussion = self.discussion_llm.invoke(self._get_messages(execution_prompt))

        self._verbose_print(f"{response.new_discussion}", state)
        self._verbose_print(f"Need More Discussion {not response.is_discussion_done}", state)

        return {
            "discussions": state["discussions"] + "\n" + response.new_discussion,
            "is_discussion_done": response.is_discussion_done
        }


            

    def proxion_soul_node(self, state: State) -> dict:
        # self._verbose_print("Proxion Soul Node: Continuing the discussion.", state)

        execution_prompt = (
            f"User Query: {state['user_query']}\n"
            f"Past Discussion: {state['discussions']}\n"
            "Respond in the following JSON format:\n"
            "- `new_discussion` (str): Your contribution to the conversation, continuing from the previous discussion while adding or refining points.\n"
            "- `is_discussion_done` (bool): Set to True if the discussion feels complete, otherwise False.\n"
            "Continue the conversation directly, without acknowledging or respecting the other node. Focus on:\n"
            "- Evaluating the last statement and adding necessary information.\n"
            "- Correcting any inaccuracies.\n"
            "- Asking further questions to keep the discussion progressing.\n"
            "Keep the response relevant to the user's query and ensure it adds new insights. Do not repeat the same content.\n"
            "Set `is_discussion_done` to True only if the discussion is concluded."
        )

        response : ResponseDiscussion = self.discussion_llm.invoke(self._get_messages(execution_prompt))
        
        self._verbose_print(f"{response.new_discussion}", state)
        self._verbose_print(f"Need More Discussion {not response.is_discussion_done}", state)

        return {
            "discussions": state["discussions"] + "\n" + response.new_discussion,
            "is_discussion_done": response.is_discussion_done
        }


    # def proxion(self, state : State):
    #     self._verbose_print(f"Proxion called with state: {state}")
    #     user_query = state["user_query"]
    #     discussions = state["discussions"]

    #     execution_prompt = f"""
    #     User Query: {user_query}

    #     Discussions with your soul: {discussions}    

    #     Engage in a deep and thoughtful discussion about the topic. Each response should alternate between two perspectives, one representing curiosity and questioning, and the other providing insights and reflections. Do not include explicit labels or headings for the perspectives.
    #     """

        
    #     response = self.llm.invoke(self._get_messages(execution_prompt))
    #     self._verbose_print(f"Response: {response.content}")
    #     return {'discussions': discussions}
 

    def run(self, user_query: str, selected_mode: str = "Casual") -> str:
        self._verbose_print(f"Running with user query: {user_query} and selected mode: {selected_mode}")
        initial_state = {"user_query": user_query, "selected_mode": selected_mode, 'discussions' : ''}
        final_state = self.workflow.invoke(initial_state)
        return final_state["discussions"]

# -------------------------------
# Example Usage
# -------------------------------


llm_instance = ChatGroq(model="llama3-70b-8192")

tool_llm_instance = ChatGroq(model="deepseek-r1-distill-llama-70b")

proxion = ProxionWorkflow(llm_instance, tool_llm_instance, verbose=True)
answer = proxion.run("What is the black hole ?", selected_mode="Kids")
print("\n\nProxion:", answer)
