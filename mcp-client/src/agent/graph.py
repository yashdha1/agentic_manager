from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


builder = StateGraph(State)


def placeholder(state: State) -> State:
    """Placeholder node — replace with real agent logic."""
    return state


builder.add_node("placeholder", placeholder)
builder.set_entry_point("placeholder")
builder.add_edge("placeholder", END)

graph = builder.compile()
