import functools
import asyncio
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage
from ai import prompts
from .tools import get_tool_status

async def create_agent(llm, tools):
    """Create an AI Proxion Agent."""

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""
                    {prompts.PROXION}
                """
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    return prompt | llm.bind_tools(tools)

async def agent_node(state, agent, name):
    result = await agent.ainvoke(state)
        
    if isinstance(result, ToolMessage):
        pass
    else:
        result = AIMessage(**result.dict(exclude={"type", "name"}), name=name)
    return {
        "messages": [result],
        "sender": name,
    }
    
async def create_agent_node(agent, name:str):
    return functools.partial(agent_node, agent=agent, name=name)

async def get_source_name_from_message(message):
    tool_slug = message.tool_calls[0]['name']
    return get_tool_status(tool_slug)