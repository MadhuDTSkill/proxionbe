import operator
from typing import TypedDict, List, Literal, Dict, Sequence
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
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


example_agents = [
    # Blog Creation Workflow
    [
        {"name": "Content Researcher", "role": "Research and provide raw content", "backstory": "Expert in research.", "tools": ["duckduckgo_search_tool", "wikipedia_tool"]},
        {"name": "Content Writer", "role": "Convert research into a structured blog", "backstory": "Professional writer."},
        {"name": "Editor", "role": "Proofread and improve the blog", "backstory": "Ensures clarity and correctness."},
    ],
    
    # Social Media Content Creation
    [
        {"name": "Trend Analyst", "role": "Analyze current social media trends", "backstory": "Keeps track of viral trends and audience behavior.", "tools": ["duckduckgo_search_tool"]},
        {"name": "Content Strategist", "role": "Plan engaging content strategies", "backstory": "Expert in social media growth and engagement."},
        {"name": "Graphic Designer", "role": "Design visually appealing posts", "backstory": "Creates eye-catching graphics and layouts."},
        {"name": "Social Media Manager", "role": "Schedule and post content", "backstory": "Ensures timely and effective content publishing."},
    ],

    # AI-Powered Code Development
    [
        {"name": "Requirement Analyst", "role": "Understand and define software requirements", "backstory": "Ensures clear, structured problem definitions."},
        {"name": "Code Generator", "role": "Write functional code snippets", "backstory": "AI-powered assistant for generating efficient code."},
        {"name": "Code Reviewer", "role": "Analyze and optimize code", "backstory": "Detects inefficiencies and suggests improvements."},
        {"name": "Deployment Engineer", "role": "Deploy and monitor applications", "backstory": "Manages cloud-based or on-premise deployments."},
    ],

    # Data Science & Machine Learning Pipeline
    [
        {"name": "Data Collector", "role": "Gather relevant datasets", "backstory": "Specialist in data sourcing and preprocessing.", "tools": ["duckduckgo_search_tool", "wikipedia_tool"]},
        {"name": "Data Cleaner", "role": "Process and clean raw data", "backstory": "Handles missing values, normalization, and formatting."},
        {"name": "Feature Engineer", "role": "Extract meaningful features", "backstory": "Transforms raw data into useful inputs for models."},
        {"name": "Model Trainer", "role": "Train ML models on prepared data", "backstory": "Optimizes model performance and hyperparameters."},
        {"name": "Model Evaluator", "role": "Validate model accuracy and performance", "backstory": "Performs statistical analysis and cross-validation."},
    ],

    # Marketing & Advertising Workflow
    [
        {"name": "Market Researcher", "role": "Analyze competitors and market needs", "backstory": "Gathers insights on audience behavior.", "tools": ["duckduckgo_search_tool", "wikipedia_tool"]},
        {"name": "Copywriter", "role": "Write compelling marketing copy", "backstory": "Specializes in persuasive and engaging content."},
        {"name": "SEO Specialist", "role": "Optimize content for search engines", "backstory": "Ensures higher ranking in search results."},
        {"name": "Marketing Strategist", "role": "Develop marketing strategies", "backstory": "Plans and executes promotional campaigns."},
        {"name": "Ad Manager", "role": "Manage and optimize online ads", "backstory": "Handles PPC campaigns and performance tracking."},
    ],

    # Customer Support Automation
    [
        {"name": "Support Bot", "role": "Handle basic customer queries", "backstory": "AI-powered assistant for quick customer support."},
        {"name": "Ticket Manager", "role": "Assign unresolved queries to agents", "backstory": "Sorts customer issues efficiently."},
        {"name": "Customer Support Agent", "role": "Resolve complex customer issues", "backstory": "Expert in troubleshooting and user satisfaction."},
        {"name": "Feedback Analyst", "role": "Analyze customer feedback", "backstory": "Extracts insights to improve services."},
    ],

    # Video Content Production
    [
        {"name": "Scriptwriter", "role": "Write engaging scripts for videos", "backstory": "Crafts compelling narratives and dialogues."},
        {"name": "Storyboard Artist", "role": "Visualize video sequences", "backstory": "Creates rough sketches for scene planning."},
        {"name": "Video Editor", "role": "Edit and enhance raw footage", "backstory": "Specializes in post-production editing."},
        {"name": "Voice Over Artist", "role": "Provide professional narration", "backstory": "Delivers engaging and clear voiceovers."},
        {"name": "Animator", "role": "Create motion graphics and animations", "backstory": "Brings visuals to life with animations."},
    ],

    # Cybersecurity & Threat Analysis
    [
        {"name": "Threat Analyst", "role": "Identify and analyze security threats", "backstory": "Specialist in cybersecurity risk assessment.", "tools": ["duckduckgo_search_tool"]},
        {"name": "Penetration Tester", "role": "Simulate cyber attacks to find vulnerabilities", "backstory": "Finds security weaknesses before hackers do."},
        {"name": "Incident Responder", "role": "Mitigate and respond to security breaches", "backstory": "Handles real-time threat response."},
        {"name": "Compliance Officer", "role": "Ensure security policies are followed", "backstory": "Keeps systems in line with regulations."},
    ],

    # Legal Document & Contract Review
    [
        {"name": "Legal Researcher", "role": "Analyze laws and regulations", "backstory": "Expert in legal research and case studies.", "tools": ["duckduckgo_search_tool", "wikipedia_tool"]},
        {"name": "Contract Drafter", "role": "Write and format legal agreements", "backstory": "Ensures contracts are clear and enforceable."},
        {"name": "Legal Reviewer", "role": "Proofread and refine legal documents", "backstory": "Checks for compliance and accuracy."},
        {"name": "Negotiation Expert", "role": "Assist in contract negotiations", "backstory": "Helps parties reach favorable terms."},
    ],

    # E-Commerce Optimization
    [
        {"name": "Product Analyst", "role": "Research best-selling products", "backstory": "Analyzes trends to recommend profitable items.", "tools": ["duckduckgo_search_tool"]},
        {"name": "Listing Optimizer", "role": "Improve product descriptions and SEO", "backstory": "Ensures high visibility on search engines."},
        {"name": "Pricing Strategist", "role": "Optimize pricing strategies", "backstory": "Finds the balance between profit and competitiveness."},
        {"name": "Customer Experience Specialist", "role": "Enhance shopping experience", "backstory": "Improves website usability and checkout flow."},
    ],

    # Human Resource Management
    [
        {"name": "Talent Scout", "role": "Identify potential job candidates", "backstory": "Expert in recruitment and talent acquisition.", "tools": ["duckduckgo_search_tool"]},
        {"name": "Resume Screener", "role": "Review and shortlist resumes", "backstory": "Finds the best candidates for job roles."},
        {"name": "Interview Coach", "role": "Prepare candidates for interviews", "backstory": "Guides job seekers to perform well."},
        {"name": "HR Policy Advisor", "role": "Develop and review company policies", "backstory": "Ensures legal compliance and employee well-being."},
    ],
]


agents = example_agents[0]

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

        graph_png = self.workflow.get_graph(xray=True).draw_mermaid_png()
        image_file = "NewAgentWorkflow.png"
        with open(image_file, "wb") as file:
            file.write(graph_png)

    def _verbose_print(self, message: str):
        if self.verbose:
            print(f"\n\033[92m[VERBOSE] {message}\033[0m")
            

    def _build_workflow(self):
        builder = StateGraph(State)
        
        # Define the core workflow components
        builder.add_node('Main Agent', self.super_agent)
        builder.add_node('Task Handler', self.dynamic_agent)
        builder.add_node('Tool Executor', ToolNode)
        
        # Define the starting flow
        builder.add_edge(START, 'Main Agent')
        builder.add_edge('Tool Executor', 'Task Handler')
        
        # Determine the next step based on task completion
        builder.add_conditional_edges(
            'Main Agent',
            lambda state: "FINISH" if state['next_agent'] == 'Task Completed' else "NOT FINISH",
            {
                'NOT FINISH': 'Task Handler',
                'FINISH': END
            },
        )
        
        # Decide whether to call tools or return to the main agent
        builder.add_conditional_edges(
            'Task Handler',
            lambda state: "EXECUTE TOOL" if state["messages"][-1].tool_calls else "Main Agent",
            {
                'Main Agent': 'Main Agent',
                'EXECUTE TOOL': "Tool Executor"
            },
        )

        return builder.compile()



    def super_agent(self, state: Dict) -> Dict:
        self._verbose_print("Super Agent: Determining next agent and task prompt.")

        agents_info = "\n".join([
            f"- {agent['name']}: {agent['role']} (Tools: {', '.join(agent.get('tools', ['None']))})"
            for agent in agents
        ])

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


llm_instance = ChatGroq(model="gemma2-9b-it")

tool_llm_instance = ChatGroq(model="gemma2-9b-it")

proxion = ProxionWorkflow(llm_instance, tool_llm_instance, verbose=True)
messages = proxion.run("Andromeda Galaxy Vs Milky Way Galaxy")

for message in messages:
    message.pretty_print()
