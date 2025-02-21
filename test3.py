import operator
from typing import TypedDict, List, Literal, Dict, Sequence
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool, BaseTool
from typing import Annotated
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
import re
from duckduckgo_search.exceptions import RatelimitException


AGENT_SYSTEM_MESSAGE = (
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


agents = [
    {"name": "Content Researcher", "role": "Research and provide raw content", "backstory": "Expert in research."},
    {"name": "Content Writer", "role": "Convert research into a structured blog", "backstory": "Professional writer."},
    {"name": "Editor", "role": "Proofread and improve the blog", "backstory": "Ensures clarity and correctness."},
]


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


# -------------------------------
# Define Data Schemas & State & LLMs
# -------------------------------

class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_agent: str
    agent_prompt: str


class SuperAgentOutput(BaseModel):
    next_agent: str = Field(
        ..., description="The name of the next agent that should handle the task. If no further agent is required, return 'Task Completed'."
    )
    agent_prompt: str = Field(
        ..., description="A guide for the next agent, explaining what needs to be done in the next step. If no further steps are needed, return 'Task Completed'."
    )
    

class ProxionWorkflow:
    def __init__(self, llm : ChatGroq, tool_llm_instance : ChatGroq, verbose=True):
        self.llm : ChatGroq = llm
        self.tool_llm : ChatGroq = tool_llm_instance
        self.verbose = verbose
        self.tools : List[BaseTool] = [wikipedia_tool, duckduckgo_search_tool]
        
        self.super_agent_llm = self.llm.with_structured_output(SuperAgentOutput, method='json_mode')
        
        self.workflow = self._build_workflow()

        # graph_png = self.workflow.get_graph(xray=True).draw_mermaid_png()
        # image_file = "NewAgentWorkflow.png"
        # with open(image_file, "wb") as file:
        #     file.write(graph_png)

    def _verbose_print(self, message: str):
        if self.verbose:
            print(f"\n\033[92m[VERBOSE] {message}\033[0m")
            

    def _build_workflow(self):
        builder = StateGraph(State)
        
        builder.add_node('Super Agent', self.super_agent)
        builder.add_node('Dynamic Agent', self.dynamic_agent)
        
        builder.add_edge(START, 'Super Agent')
        builder.add_edge('Dynamic Agent', 'Super Agent')
        
        builder.add_conditional_edges(
            'Super Agent',
            lambda state: "END" if state['next_agent'] == 'Task Completed' else "Dynamic Agent",
            {
                'Dynamic Agent': 'Dynamic Agent',
                'END': END
            },
        )
    
        return builder.compile()


    def super_agent(self, state: Dict) -> Dict:
        self._verbose_print("Super Agent: Determining next agent and task prompt.")

        agents = [
            {"name": "Content Researcher", "role": "Research and provide raw content"},
            {"name": "Content Writer", "role": "Convert research into a structured blog"},
        ]

        agents_info = "\n".join([f"- {agent['name']}: {agent['role']}" for agent in agents])

        execution_prompt = (
            "Based on the following available agents and their roles, determine the next best agent to handle the task for the user:\n"
            f"{agents_info}\n\n"
            "Provide the response in JSON format with the following fields:\n"
            "- `next_agent` (str): The agent name that should handle the next part of the task. If no further agent is needed, return 'Task Completed'.\n"
            "- `agent_prompt` (str): A concise instruction for the next agent on what they need to do. If no further steps are needed, return 'Task Completed'.\n"
            "Make sure the selection is logical based on the query and the roles of available agents."
        )


        messages = [
            *state["messages"],
            HumanMessage(content=execution_prompt),
        ]
        
        response: SuperAgentOutput = self.super_agent_llm.invoke(messages)

        self._verbose_print(f"Next Agent: {response.next_agent}")
        self._verbose_print(f"Agent Prompt: {response.agent_prompt}")
        
        new_message = AIMessage(content=f"Next Agent: {response.next_agent} : Prompt To Follow: {response.agent_prompt}")
        
        return {
            "messages": [new_message],
            "next_agent": response.next_agent,
            "agent_prompt": response.agent_prompt,
        }


    def dynamic_agent(self, state: Dict) -> Dict:
        self._verbose_print("Dynamic Agent: Determining next agent and task prompt.")

        agents = [
            {"name": "Content Researcher", "role": "Research and provide raw content", "backstory": "Expert in research."},
            {"name": "Content Writer", "role": "Convert research into a structured blog", "backstory": "Professional writer."},
        ]

        next_agent_name = state.get("next_agent")  
        previous_agent_prompt = state.get("agent_prompt", "") 

        next_agent = next((agent for agent in agents if agent["name"] == next_agent_name), None)

        if not next_agent:
            raise ValueError(f"Agent '{next_agent_name}' not found in the agents list.")

        execution_prompt = (
            f"You are {next_agent['name']}.\n"
            f"Your role: {next_agent['role']}.\n"
            f"Your backstory: {next_agent['backstory']}.\n\n"
            f"Your task: Generate a proper, accurate response based on the following instructions.\n"
            f"Task Details: {previous_agent_prompt}\n\n"
            "Respond with a detailed and structured answer relevant to your expertise."
        )
        
        messages = [
            *state["messages"],
            HumanMessage(content=execution_prompt),
        ]

        response = self.llm.invoke(messages)

        self._verbose_print(f"Agent {next_agent_name} executed the task.")
        
        new_message = AIMessage(content=f"{next_agent['name']} Agent Response: {response.content}")
        return {
            "messages": [new_message],
        }
 

    def run(self, user_query: str) -> str:
        self._verbose_print(f"Running with user query: {user_query}")
        initial_state = {
                "messages": [
                    HumanMessage(content=user_query)
                ]
            }
        final_state = self.workflow.invoke(initial_state)
        return final_state["messages"]

# -------------------------------
# Example Usage
# -------------------------------


llm_instance = ChatGroq(model="llama3-70b-8192")

tool_llm_instance = ChatGroq(model="deepseek-r1-distill-llama-70b")

proxion = ProxionWorkflow(llm_instance, tool_llm_instance, verbose=True)
messages = proxion.run("Andromeda Galaxy Vs Milky Way Galaxy")

for message in messages:
    message.pretty_print()
