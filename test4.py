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
    

# class ProxionWorkflow:
#     def __init__(self, llm : ChatGroq, tool_llm_instance : ChatGroq, verbose=True):
#         self.llm : ChatGroq = llm
#         self.tool_llm : ChatGroq = tool_llm_instance
#         self.verbose = verbose
#         self.tools : List[BaseTool] = [wikipedia_tool, duckduckgo_search_tool]
        
#         self.super_agent_llm = self.llm.with_structured_output(SuperAgentOutput, method='json_mode')
        
#         self.workflow = self._build_workflow()

#         graph_png = self.workflow.get_graph(xray=True).draw_mermaid_png()
#         image_file = "NewAgentWorkflow.png"
#         with open(image_file, "wb") as file:
#             file.write(graph_png)

#     def _verbose_print(self, message: str):
#         if self.verbose:
#             print(f"\n\033[92m[VERBOSE] {message}\033[0m")
            

#     def _build_workflow(self):
#         builder = StateGraph(State)
        
#         # Define the core workflow components
#         builder.add_node('Main Agent', self.super_agent)
#         builder.add_node('Task Handler', self.dynamic_agent)
#         builder.add_node('Tool Executor', ToolNode)
        
#         # Define the starting flow
#         builder.add_edge(START, 'Main Agent')
#         builder.add_edge('Tool Executor', 'Task Handler')
        
#         # Determine the next step based on task completion
#         builder.add_conditional_edges(
#             'Main Agent',
#             lambda state: "FINISH" if state['next_agent'] == 'Task Completed' else "NOT FINISH",
#             {
#                 'NOT FINISH': 'Task Handler',
#                 'FINISH': END
#             },
#         )
        
#         # Decide whether to call tools or return to the main agent
#         builder.add_conditional_edges(
#             'Task Handler',
#             lambda state: "EXECUTE TOOL" if state["messages"][-1].tool_calls else "Main Agent",
#             {
#                 'Main Agent': 'Main Agent',
#                 'EXECUTE TOOL': "Tool Executor"
#             },
#         )

#         return builder.compile()



#     def super_agent(self, state: Dict) -> Dict:
#         self._verbose_print("Super Agent: Determining next agent and task prompt.")

#         agents_info = "\n".join([
#             f"- {agent['name']}: {agent['role']} (Tools: {', '.join(agent.get('tools', ['None']))})"
#             for agent in agents
#         ])

#         execution_prompt = (
#             "Based on the following available agents and their roles, determine the next best agent to handle the task for the user:\n"
#             f"{agents_info}\n\n"
#             "Provide the response in JSON format with the following fields:\n"
#             "- `next_agent` (str): The agent name that should handle the next part of the task. If no further agent is needed, return 'Task Completed'.\n"
#             "- `agent_prompt` (str): A concise instruction for the next agent on what they need to do. If no further steps are needed, return 'Task Completed'.\n"
#             "Make sure the selection is logical based on the query and the roles of available agents."
#         )


#         messages = [
#             *state["messages"],
#             HumanMessage(content=execution_prompt),
#         ]
        
#         response: SuperAgentOutput = self.super_agent_llm.invoke(messages)

#         self._verbose_print(f"Next Agent: {response.next_agent}")
#         self._verbose_print(f"Agent Prompt: {response.agent_prompt}")
        
#         new_message = AIMessage(content=f"Next Agent: {response.next_agent} : Prompt To Follow: {response.agent_prompt}")
        
#         return {
#             "messages": [new_message],
#             "next_agent": response.next_agent,
#             "agent_prompt": response.agent_prompt,
#         }


#     def dynamic_agent(self, state: Dict) -> Dict:
#         self._verbose_print("Dynamic Agent: Determining next agent and task prompt.")

#         next_agent_name = state.get("next_agent")  
#         previous_agent_prompt = state.get("agent_prompt", "") 

#         next_agent = next((agent for agent in agents if agent["name"] == next_agent_name), None)

#         if not next_agent:
#             raise ValueError(f"Agent '{next_agent_name}' not found in the agents list.")

#         execution_prompt = (
#             f"You are {next_agent['name']}.\n"
#             f"Your role: {next_agent['role']}.\n"
#             f"Your backstory: {next_agent['backstory']}.\n\n"
#             f"Your task: Generate a proper, accurate response based on the following instructions.\n"
#             f"Task Details: {previous_agent_prompt}\n\n"
#             "Respond with a detailed and structured answer relevant to your expertise."
#         )
        
#         messages = [
#             *state["messages"],
#             HumanMessage(content=execution_prompt),
#         ]

#         response = self.llm.invoke(messages)

#         self._verbose_print(f"Agent {next_agent_name} executed the task.")
        
#         new_message = AIMessage(content=f"{next_agent['name']} Agent Response: {response.content}")
#         return {
#             "messages": [new_message],
#         }
 

#     def run(self, user_query: str) -> str:
#         self._verbose_print(f"Running with user query: {user_query}")
#         initial_state = {
#                 "messages": [
#                     HumanMessage(content=user_query)
#                 ]
#             }
#         final_state = self.workflow.invoke(initial_state)
#         return final_state["messages"]

# -------------------------------
# Example Usage
# -------------------------------


# llm_instance = ChatGroq(model="llama3-70b-8192")

# tool_llm_instance = ChatGroq(model="deepseek-r1-distill-llama-70b")

# proxion = ProxionWorkflow(llm_instance, tool_llm_instance, verbose=True)
# # messages = proxion.run("Andromeda Galaxy Vs Milky Way Galaxy")

# # for message in messages:
# #     message.pretty_print()


import ast

def extract_code_chunks_from_file(file_path):
    """Reads a Python file and extracts imports, variables, functions, and classes in order."""
    
    # Read file content
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    tree = ast.parse(code)
    lines = code.splitlines()
    chunks = []

    for node in tree.body:
        start_line = node.lineno - 1
        end_line = getattr(node, "end_lineno", node.lineno)  # Python 3.8+ support
        chunk = "\n".join(lines[start_line:end_line])

        chunks.append(chunk)

    return chunks

# 🔥 File to Read (Update Path If Needed)
file_path = "test.py"  # Update this if the file is elsewhere

# Extract Chunks
chunks = extract_code_chunks_from_file(file_path)

# Print Chunks in Order
for idx, chunk in enumerate(chunks, 1):
    print(f"Chunk {idx} :\n{chunk}\n{'-'*40}")
