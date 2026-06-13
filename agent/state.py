from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # Full conversation history — add_messages means
    # new messages get appended, not overwritten
    messages: Annotated[list, add_messages]

    # Customer name if they mention it (starts as None)
    customer_name: str | None

    # Last tool called — useful for logging later
    last_tool_called: str | None