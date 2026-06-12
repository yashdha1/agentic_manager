from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import interrupt as _lg_interrupt

import src.declarative.agent_static as agent_static
from src.core import chat_persistence
from src.core.logger import logger
from src.declarative.AgentSpec import AgentsTool, get_tools_for
from src.models.AgentOutput import AgentName, OrchestratorOutput

graph = None # OBJ


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
    thread_id: str
    selected_agents: list[AgentName]
    policies: list[str]
    # Accumulated by all parallel sub-agent nodes before aggregator runs.
    agent_responses: Annotated[dict[str, str], _merge_dicts]
    final_response: str
    # Conversation history — persisted in Redis per thread_id via the checkpointer.
    messages: Annotated[list[BaseMessage], add_messages]

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


# Maximum number of prior messages forwarded to each sub-agent for context.
_SUB_AGENT_HISTORY_LIMIT = 10


def _build_sub_agent_messages(state: State) -> list[BaseMessage]:
    """Return the conversation history plus the current query as a HumanMessage.

    The last N messages from the thread are forwarded to sub-agents so that
    follow-up questions (e.g. user providing a missing order_id after the agent
    asked for it) are visible within the same execution context.  The current
    query is always appended last so it is the agent's primary instruction.
    """
    history: list[BaseMessage] = list(state.get("messages", []) or [])
    # Drop the last message if it is already the current HumanMessage we are
    # about to append (avoids duplication when history was built by chat.py).
    if history and isinstance(history[-1], HumanMessage) and history[-1].content == state["query"]:
        history = history[:-1]
    prior = history[-_SUB_AGENT_HISTORY_LIMIT:] if len(history) > _SUB_AGENT_HISTORY_LIMIT else history
    return prior + [HumanMessage(content=state["query"])]


# ── Per-agent prompt directory ────────────────────────────────────────────────
_AGENTS_DIR = Path(__file__).parent / "agents"


def _load_md(filename: str) -> str:
    return (_AGENTS_DIR / filename).read_text(encoding="utf-8")


def _ensure_tool_str(v) -> str:
    """Coerce a tool result to a plain string for ToolMessage content."""
    if isinstance(v, str):
        return v
    try:
        return _json.dumps(v, default=str)
    except Exception:
        return str(v)


async def _run_agent_loop(
    model,
    tools_by_name: dict,
    hitl_tool_names: set[str],
    messages: list,
) -> str:
    """Run an agent tool-call loop with direct interrupt() for HITL tools.

    HITL tools are intercepted and surfaced via langgraph's interrupt() called
    directly inside this function (which executes within an outer workflow node).
    This ensures the outer graph's checkpointer handles pause/resume — compiled
    sub-graphs invoked via ainvoke() swallow GraphInterrupt internally and their
    scratchpad never carries resume values, so HITL can never properly resume.
    """
    while True:
        response: AIMessage = await model.ainvoke(messages)
        messages = [*messages, response]

        if not response.tool_calls:
            content = response.content
            if isinstance(content, list):
                return "".join(
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            return content or ""

        # ── Separate HITL vs. auto-approved tool calls ────────────────────────
        hitl_calls = [tc for tc in response.tool_calls if tc["name"] in hitl_tool_names]
        auto_calls = [tc for tc in response.tool_calls if tc["name"] not in hitl_tool_names]

        tool_results: list[ToolMessage] = []

        # ── Execute auto-approved tools immediately ───────────────────────────
        for tc in auto_calls:
            tool = tools_by_name.get(tc["name"])
            if tool is None:
                outcome = _ensure_tool_str({"error": f"Tool '{tc['name']}' not found"})
            else:
                try:
                    raw = await tool.ainvoke(tc["args"])
                    outcome = _ensure_tool_str(raw)
                except Exception as exc:
                    outcome = _ensure_tool_str({"error": str(exc)})
            tool_results.append(
                ToolMessage(content=outcome, name=tc["name"], tool_call_id=tc["id"])
            )

        # ── HITL tools: single interrupt() call for the whole batch ───────────
        if hitl_calls:
            hitl_request = {
                "action_requests": [
                    {
                        "name": tc["name"],
                        "args": tc["args"],
                        "description": (
                            f"Tool execution requires approval\n\n"
                            f"Tool: {tc['name']}\nArgs: {tc['args']}"
                        ),
                    }
                    for tc in hitl_calls
                ],
                "review_configs": [
                    {
                        "action_name": tc["name"],
                        "allowed_decisions": ["approve", "edit", "reject"],
                    }
                    for tc in hitl_calls
                ],
            }
            result = _lg_interrupt(hitl_request)
            decisions: list[dict] = result["decisions"]

            for i, tc in enumerate(hitl_calls):
                decision = decisions[i] if i < len(decisions) else {"type": "approve"}
                dtype = decision.get("type", "approve")

                if dtype == "reject":
                    outcome = _ensure_tool_str(
                        {"status": "rejected", "message": decision.get("message", "")}
                    )
                elif dtype == "edit":
                    edited = decision.get("edited_action", {})
                    exec_name = edited.get("name", tc["name"])
                    exec_args = edited.get("args", tc["args"])
                    tool = tools_by_name.get(exec_name)
                    if tool is None:
                        outcome = _ensure_tool_str({"error": f"Tool '{exec_name}' not found"})
                    else:
                        try:
                            raw = await tool.ainvoke(exec_args)
                            outcome = _ensure_tool_str(raw)
                        except Exception as exc:
                            outcome = _ensure_tool_str({"error": str(exc)})
                else:  # approve
                    tool = tools_by_name.get(tc["name"])
                    if tool is None:
                        outcome = _ensure_tool_str({"error": f"Tool '{tc['name']}' not found"})
                    else:
                        try:
                            raw = await tool.ainvoke(tc["args"])
                            outcome = _ensure_tool_str(raw)
                        except Exception as exc:
                            outcome = _ensure_tool_str({"error": str(exc)})

                tool_results.append(
                    ToolMessage(content=outcome, name=tc["name"], tool_call_id=tc["id"])
                )

        messages = [*messages, *tool_results]


async def _sales_node(state: State, config: RunnableConfig) -> dict:
    tools = get_tools_for(AgentsTool.SALES)
    tools_by_name = {t.name: t for t in tools}
    hitl_tools = {t.name for t in tools if t.name.endswith("_hitl")}
    model = agent_static._model_light.bind_tools(tools)
    msgs = [SystemMessage(content=_load_md("sales.md"))] + _build_sub_agent_messages(state)
    result = await _run_agent_loop(model, tools_by_name, hitl_tools, msgs)
    return {"agent_responses": {"sales": result}}


async def _customers_node(state: State, config: RunnableConfig) -> dict:
    tools = get_tools_for(AgentsTool.CUSTOMER)
    tools_by_name = {t.name: t for t in tools}
    hitl_tools = {t.name for t in tools if t.name.endswith("_hitl")}
    model = agent_static._model_light.bind_tools(tools)
    msgs = [SystemMessage(content=_load_md("customer_support.md"))] + _build_sub_agent_messages(state)
    result = await _run_agent_loop(model, tools_by_name, hitl_tools, msgs)
    return {"agent_responses": {"customers": result}}


async def _inventory_node(state: State, config: RunnableConfig) -> dict:
    tools = get_tools_for(AgentsTool.INVENTORY)
    tools_by_name = {t.name: t for t in tools}
    hitl_tools = {t.name for t in tools if t.name.endswith("_hitl")}
    model = agent_static._model_light.bind_tools(tools)
    msgs = [SystemMessage(content=_load_md("inventory.md"))] + _build_sub_agent_messages(state)
    result = await _run_agent_loop(model, tools_by_name, hitl_tools, msgs)
    return {"agent_responses": {"inventory": result}}


async def _knowledge_node(state: State, config: RunnableConfig) -> dict:
    tools = get_tools_for(AgentsTool.KNOWLEDGE)
    tools_by_name = {t.name: t for t in tools}
    hitl_tools = {t.name for t in tools if t.name.endswith("_hitl")}
    model = agent_static._model_light.bind_tools(tools)
    msgs = [SystemMessage(content=_load_md("knowledge.md"))] + _build_sub_agent_messages(state)
    result = await _run_agent_loop(model, tools_by_name, hitl_tools, msgs)
    return {"agent_responses": {"knowledge": result}}


async def _aggregator_node(state: State) -> dict:
    policies_text = "\n".join(state.get("policies", [])) or "None"
    agent_sections = "\n".join(
        f"### {name.capitalize()} Agent:\n{resp}"
        for name, resp in state.get("agent_responses", {}).items()
    )
    # Enrich the current turn with gathered agent data.
    context = (
        f"User Query: {state['query']}\n\n"
        f"Policies:\n{policies_text}\n\n"
        f"Agent Responses:\n{agent_sections}"
    )
    # Build messages: prior conversation history (all messages except the latest
    # raw HumanMessage which we replace with the enriched context), so the
    # aggregator sees the full thread history and can answer follow-up questions.
    history: list[BaseMessage] = state.get("messages", [])  # type: ignore[assignment]
    if history and isinstance(history[-1], HumanMessage):
        messages_for_agg = list(history[:-1]) + [HumanMessage(content=context)]
    else:
        messages_for_agg = list(history) + [HumanMessage(content=context)]
    response = await agent_static.aggregator_agent.ainvoke(
        {"messages": messages_for_agg}
    )
    final = _msg_content(response)
    # Persist to PostgreSQL (durable chat history).
    _thread_id = state.get("thread_id", "")
    if _thread_id:
        try: 
            await chat_persistence.ensure_thread(_thread_id, state["query"][:100])
            await chat_persistence.save_conversation(
                thread_id=_thread_id,
                human_msg=state["query"],
                ai_msg=final,
                tool_calls=_json.dumps(state.get("agent_responses", {})),
            )
        except Exception as _exc:
            logger.error("PG persist failed for thread {}: {}", _thread_id, _exc)

    return {
        "final_response": final,
        # Append the AI response to the persisted message history.
        "messages": [AIMessage(content=final)],
    }


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

    # Each sub-agent feeds into the aggregator.
    builder.add_edge("sales", "aggregator")
    builder.add_edge("customers", "aggregator")
    builder.add_edge("inventory", "aggregator")
    builder.add_edge("knowledge", "aggregator")

    builder.add_edge("aggregator", END)

    graph = builder.compile(checkpointer=checkpointer)
