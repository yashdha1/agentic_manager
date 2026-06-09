from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.agents.middleware.human_in_the_loop import InterruptOnConfig
from langchain_core.tools import BaseTool


def make_hitl_middleware(agent_tools: list[BaseTool]) -> HumanInTheLoopMiddleware | None:
    """Build HITL middleware for every tool whose name ends with '_hitl'.

    The middleware intercepts the tool call BEFORE the tool executes and raises
    a LangGraph interrupt so a human operator can approve or reject it.
    If approved the original tool call proceeds; if rejected a ToolMessage with
    status='error' is injected and the tool never runs.
    """
    hitl_names = [t.name for t in agent_tools if t.name.endswith("_hitl")]
    if not hitl_names:
        return None
    return HumanInTheLoopMiddleware(
        interrupt_on={
            name: InterruptOnConfig(allowed_decisions=["approve", "edit", "reject"])
            for name in hitl_names
        }
    )
