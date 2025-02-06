import operator
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict, Annotated
from typing import Sequence, Any, Final

class WorkFlowState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    consumer: Any

