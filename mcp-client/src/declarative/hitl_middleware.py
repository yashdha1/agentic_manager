from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.agents.middleware.human_in_the_loop import InterruptOnConfig
from langchain_core.tools import BaseTool


def make_hitl_middleware(agent_tools: list[BaseTool]) -> HumanInTheLoopMiddleware | None:
    """Build HITL middleware for every tool whose name ends with '_hitl'.

    Tools keep their full '_hitl'-suffixed names. The middleware intercepts
    calls to those tools and raises a LangGraph interrupt for human review
    before the tool body executes. The action is only committed after the
    operator approves.
    """
    hitl_tools = [t for t in agent_tools if t.name.endswith("_hitl")]
    if not hitl_tools:
        return None

    return HumanInTheLoopMiddleware(
        interrupt_on={
            t.name: InterruptOnConfig(allowed_decisions=["approve", "edit", "reject"])
            for t in hitl_tools
        }
    )
