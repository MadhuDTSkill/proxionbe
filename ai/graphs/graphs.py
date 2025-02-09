import os
import asyncio
import operator
from typing import Sequence, Any
from typing_extensions import TypedDict, Annotated
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph import END, StateGraph, START
from .utils import create_agent_node, create_agent, get_source_name_from_message
from .tools import wikipedia_tool, duckduckgo_search_tool, calculator_tool, developer_biography_tool, web_url_tool
from .memory import Memory
from chats_app.models import Chat
from auth_app.models import User

class WorkFlowState(TypedDict):
    consumer: Any
    messages: Annotated[Sequence[BaseMessage], operator.add]
    sender : str

async def get_tool_node(tools: list):
    return ToolNode(tools=tools)

async def router(state):
    messages = state["messages"]
    last_message = messages[-1]
    try:
        if last_message.tool_calls:
            from helper.consumers import BaseChatAsyncJsonWebsocketConsumer
            consumer : BaseChatAsyncJsonWebsocketConsumer = state['consumer']
            source_status = await get_source_name_from_message(last_message)
            await consumer.send_status(source_status)
            return "call_tool"
    except Exception as e:
        print(e)
    return "forward"

def sync_router_wrapper(state):
    return asyncio.run(router(state))


class ProxionAgentGraph:
    def __init__(self, chat : Chat, user : User, consumer : object):
        self.llm = ChatGroq(
            model = "llama3-70b-8192",
            temperature=0.1
        )
        self.chat = chat
        self.user = user
        self.consumer = consumer
        self.all_tools = [wikipedia_tool, duckduckgo_search_tool, calculator_tool, developer_biography_tool, web_url_tool]
        self.memory = Memory.get_memory(str(chat.id), str(self.user.id), 3000, self.llm, True, False, 'human')
    
    async def create_graph(self):
        graph = StateGraph(WorkFlowState)
        proxion_agent = await create_agent(self.llm, self.all_tools)
        proxion_agent_node = await create_agent_node(proxion_agent, "Proxion")
        tool_node = await get_tool_node(self.all_tools)
        
        graph.add_node("Tools", tool_node)
        graph.add_node("Proxion", proxion_agent_node)

        graph.add_edge(START, "Proxion")
        graph.add_edge("Tools", "Proxion")
        graph.add_conditional_edges(
                "Proxion",
                sync_router_wrapper,
                {
                    "call_tool": "Tools",
                    "forward": END,
                }
            )
        return graph.compile()
    
    async def init_graph(self):
        self.graph = await self.create_graph()
    
    async def get_image(self):
        graph_png = self.graph.get_graph(xray=True).draw_mermaid_png()
        image_file = "ProxionAgentGraph.png"
        with open(image_file, "wb") as file:
            file.write(graph_png)
        return 'Saved image to ' + image_file
    
    async def get_result(self, input_message):
        history = self.memory.messages

        messages = history + [HumanMessage(content=input_message)]
        result = await self.graph.ainvoke(
            {
                "messages": messages,
                "consumer": self.consumer,
            }
        )
        response_messsages = result['messages']
        last_message = response_messsages[-1]
        answer_message = last_message.content
        tool_responses = []
        
        self.memory.add_user_message(input_message)
        self.memory.add_ai_message(input_message)

        for message in response_messsages:
            if message.type == "tool":
                tool_response = {
                    "tool_name": message.name,
                    "tool_response": message.content,
                }
                tool_responses.append(tool_response)     
        
        response = {
            "chat": str(self.chat.id),
            "prompt": input_message,
            "response": answer_message,
            "tool_responses": tool_responses,
        }
        return response
                
    
    async def invoke(self, input_message):
        # return await self.get_image()
        response = await self.get_result(input_message)
        return response