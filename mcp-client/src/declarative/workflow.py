from __future__ import annotations

from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph

import src.declarative.agent_static as agent_static
from src.models.AgentOutput import AgentName, OrchestratorOutput

_AGENTS_DIR = Path(__file__).parent / "agents"

_AGGREGATOR_PROMPT = (_AGENTS_DIR / "Aggregator.md").read_text(encoding="utf-8")

graph = None

def _merge_dicts(a: dict, b: dict) -> dict:
    """Reducer that merges parallel agent-response dicts."""
    return {**a, **b}


class State(TypedDict):
    query: str
    orchestrator_output: OrchestratorOutput
    selected_agents: list[AgentName]
    policies: list[str]
    # Accumulated by all parallel sub-agent nodes before aggregator runs.
    agent_responses: Annotated[dict[str, str], _merge_dicts]
    final_response: str

async def _orchestrator_node(state: State) -> dict:
    response = await agent_static.orchestrator.ainvoke(
        {"messages": [HumanMessage(content=state["query"])]}
    )
    output: OrchestratorOutput = response["structured_response"]
    return {
        "orchestrator_output": output,
        "selected_agents": list(output.agents),
        "policies": output.policies,
    }


async def _sales_node(state: State) -> dict:
    response = await agent_static.sales_agent.ainvoke(
        {"messages": [HumanMessage(content=state["query"])]}
    )
    return {"agent_responses": {"sales": response["messages"][-1].content}}


async def _customers_node(state: State) -> dict:
    response = await agent_static.customer_agent.ainvoke(
        {"messages": [HumanMessage(content=state["query"])]}
    )
    return {"agent_responses": {"customers": response["messages"][-1].content}}


async def _inventory_node(state: State) -> dict:
    response = await agent_static.inventory_agent.ainvoke(
        {"messages": [HumanMessage(content=state["query"])]}
    )
    return {"agent_responses": {"inventory": response["messages"][-1].content}}


async def _knowledge_node(state: State) -> dict:
    response = await agent_static.knowledge_agent.ainvoke(
        {"messages": [HumanMessage(content=state["query"])]}
    )
    return {"agent_responses": {"knowledge": response["messages"][-1].content}}


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
    response = await agent_static._model.ainvoke(
        [SystemMessage(content=_AGGREGATOR_PROMPT), HumanMessage(content=context)]
    )
    return {"final_response": response.content}


def _route_to_agents(state: State):
    """Fan-out to all agents selected by the orchestrator (runs in parallel)."""
    return [Send(agent_name, state) for agent_name in state["selected_agents"]]

def init_workflow() -> None:
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

    # Orchestrator parallel workflow
    builder.add_conditional_edges("orchestrator", _route_to_agents)

    # Each sub-agent feeds into the aggregator.
    builder.add_edge("sales", "aggregator")
    builder.add_edge("customers", "aggregator")
    builder.add_edge("inventory", "aggregator")
    builder.add_edge("knowledge", "aggregator")

    builder.add_edge("aggregator", END)

    graph = builder.compile()
