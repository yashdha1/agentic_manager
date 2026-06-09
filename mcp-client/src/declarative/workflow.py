from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph

import src.declarative.agent_static as agent_static
from src.models.AgentOutput import AgentName, OrchestratorOutput

graph = None


def _msg_content(response: dict) -> str:
    """Extract the string content from the last message of an agent's ainvoke response.

    After an interrupt/resume cycle LangGraph can deserialise message objects back
    as plain dicts rather than LangChain message instances.  This helper handles
    both forms so the outer workflow nodes never crash on attribute access.
    """
    msgs = response.get("messages") or []
    if not msgs:
        return ""
    last = msgs[-1]
    if hasattr(last, "content"):
        val = last.content
    elif isinstance(last, dict):
        val = last.get("content", "")
    else:
        return str(last)
    # Multi-modal / Claude-style content is a list of typed blocks.
    if isinstance(val, list):
        return "".join(
            block.get("text", "")
            for block in val
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return val or ""

def _merge_dicts(a: dict, b: dict) -> dict:
    """Reducer that merges parallel agent-response dicts."""
    return {**a, **b}


class State(TypedDict):
    query: str
    selected_agents: list[AgentName]
    policies: list[str]
    # Accumulated by all parallel sub-agent nodes before aggregator runs.
    agent_responses: Annotated[dict[str, str], _merge_dicts]
    final_response: str

async def _orchestrator_node(state: State) -> dict:
    # Pass an explicit empty-configurable config so the orchestrator sub-graph
    # does NOT inherit the outer graph's Redis checkpointer via context vars.
    response = await agent_static.orchestrator.ainvoke(
        {"messages": [HumanMessage(content=state["query"])]},
        {"configurable": {}, "recursion_limit": 25},
    )
    output: OrchestratorOutput = response["structured_response"]
    return {
        "selected_agents": list(output.agents),
        "policies": output.policies,
    }


_SUB_AGENT_CONFIG = {"configurable": {}, "recursion_limit": 25}


async def _sales_node(state: State) -> dict:
    response = await agent_static.sales_agent.ainvoke(
        {"messages": [HumanMessage(content=state["query"])]},
        _SUB_AGENT_CONFIG,
    )
    return {"agent_responses": {"sales": _msg_content(response)}}


async def _customers_node(state: State) -> dict:
    response = await agent_static.customer_agent.ainvoke(
        {"messages": [HumanMessage(content=state["query"])]},
        _SUB_AGENT_CONFIG,
    )
    return {"agent_responses": {"customers": _msg_content(response)}}


async def _inventory_node(state: State) -> dict:
    response = await agent_static.inventory_agent.ainvoke(
        {"messages": [HumanMessage(content=state["query"])]},
        _SUB_AGENT_CONFIG,
    )
    return {"agent_responses": {"inventory": _msg_content(response)}}


async def _knowledge_node(state: State) -> dict:
    response = await agent_static.knowledge_agent.ainvoke(
        {"messages": [HumanMessage(content=state["query"])]},
        _SUB_AGENT_CONFIG,
    )
    return {"agent_responses": {"knowledge": _msg_content(response)}}


async def _aggregator_node(state: State) -> dict:
    policies_text = "\n".join(state.get("policies", [])) or "None"
    agent_sections = "\n".join(
        f"### {name.capitalize()} Agent:\n{resp}"
        for name, resp in state.get("agent_responses", {}).items()
    )
    context = (
        f"User Query: {state['query']}\n\n"
        f"Policies:\n{policies_text}\n\n"
        f"Agent Responses:\n{agent_sections}"
    )
    response = await agent_static.aggregator_agent.ainvoke(
        {"messages": [HumanMessage(content=context)]}
    )
    return {"final_response": _msg_content(response)}


def _route_to_agents(state: State):
    """Fan-out to all agents selected by the orchestrator (runs in parallel)."""
    return [Send(agent_name, state) for agent_name in state["selected_agents"]]

def init_workflow(checkpointer) -> None:
    """Build and compile the LangGraph workflow. Called once at startup."""
    global graph

    builder = StateGraph(State)

    builder.add_node("orchestrator", _orchestrator_node)
    builder.add_node("sales", _sales_node)
    builder.add_node("customers", _customers_node)
    builder.add_node("inventory", _inventory_node)
    builder.add_node("knowledge", _knowledge_node)
    builder.add_node("aggregator", _aggregator_node)

    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges("orchestrator", _route_to_agents)
    builder.add_edge("orchestrator", "aggregator") 

    # Each sub-agent feeds into the aggregator.
    builder.add_edge("sales", "aggregator")
    builder.add_edge("customers", "aggregator")
    builder.add_edge("inventory", "aggregator")
    builder.add_edge("knowledge", "aggregator")

    builder.add_edge("aggregator", END)

    graph = builder.compile(checkpointer=checkpointer)
