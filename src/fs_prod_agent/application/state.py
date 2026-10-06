"""State handed to the decision port. Built by the application, not by a model."""

from pydantic import BaseModel, ConfigDict, Field

from fs_prod_agent.domain.models import Action, Principal


class AgentState(BaseModel):
    model_config = ConfigDict(frozen=True)

    request: str
    evidence_ids: list[str] = Field(default_factory=list)
    proposed_action: Action | None = None
    principal: Principal
    workflow_result: str | None = None


def build_agent_state(
    request: str,
    evidence: list[str],
    proposed_action: Action | None,
    principal: Principal,
    workflow_result: str | None = None,
) -> AgentState:
    return AgentState(
        request=request,
        evidence_ids=list(evidence),
        proposed_action=proposed_action,
        principal=principal,
        workflow_result=workflow_result,
    )
