from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["sales", "knowledge", "customers", "inventory"]


class OrchestratorOutput(BaseModel):
    """
    Structured output from the Orchestrator Agent.
    """
    agents: list[AgentName] = Field(
        description="Names of the agents to invoke in order to fulfill the query."
    )
    policies: list[str] = Field(
        description="Relevant policies that may apply to the query (e.g. refund policy, return policies)."
    )