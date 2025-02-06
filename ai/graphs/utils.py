import functools
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage
from ai import prompts

def create_agent(llm, tools):
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

def agent_node(state, agent, name):
    result = agent.invoke(state)
        
    if isinstance(result, ToolMessage):
        pass
    else:
        result = AIMessage(**result.dict(exclude={"type", "name"}), name=name)
    return {
        "messages": [result],
        "sender": name,
    }
    
def create_agent_node(agent, name:str):
    return functools.partial(agent_node, agent=agent, name=name)
