import os
import operator
from collections import defaultdict
from typing import Sequence
from typing_extensions import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph import END, StateGraph, START
import importlib
from .utils import create_agent_node, create_agent


class WorkFlowState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    sender : str

def get_tool_node(tools: list):
    return ToolNode(tools=tools)

def router(state):
    messages = state["messages"]
    last_message = messages[-1]
    try:
        if last_message.tool_calls:
            return "call_tool"
        elif last_message.content == '':
            return "redirect"
    except:
        pass
    return "forward"


class ProxionAgentGraph:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name = "llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
            api_key = os.environ.get("GROQ_API_KEY")
        )
        self.all_tools = []
    
    def create_graph(self):
        graph = StateGraph(WorkFlowState)
        proxion_agent = create_agent(self.llm, self.all_tools)
        graph.add_node("Tools", get_tool_node(self.all_tools))
        graph.add_node("Proxion", create_agent_node(proxion_agent, "Proxion"))

        graph.add_edge(START, "Proxion")
        graph.add_conditional_edges(
                "Proxion",
                router,
                {
                    "call_tool": "Tools",
                    "forward": END,
                }
            )
        graph.add_conditional_edges(
            "Tools",
            lambda state: state["sender"],
            {
                "Proxion": "Proxion",
            }
        )
        return graph.compile()
    
    def init_graph(self):
        graph = self.create_graph()
        return graph
    
    def get_image(self, graph):
        graph_png = graph.get_graph(xray=True).draw_mermaid_png()
        image_file = "sequential_multiagent_graph.png"
        with open(image_file, "wb") as file:
            file.write(graph_png)
        return 'Saved image to ' + image_file
    
    def get_result(self, graph, input_message):
        result = graph.invoke(
            {
                "messages": [
                    HumanMessage(content=input_message)
                ]
            },
        )
        return result['messages']
    
    def run(self, input_message):
        graph = self.init_graph()
        return self.get_image(graph)
        return self.get_result(graph, input_message)
    
    
p = ProxionAgentGraph()
p.run("What is the weather in New York?")