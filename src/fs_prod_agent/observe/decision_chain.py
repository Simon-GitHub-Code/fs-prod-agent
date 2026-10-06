"""One record can answer who asked, what was decided, what policy did, and what ran."""

from pydantic import BaseModel, ConfigDict, Field

from fs_prod_agent.decisions.contract import Answer


class TraceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_request: str
    route: str | None
    workflow_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    decision_contract_version: str
    answers: list[Answer] = Field(default_factory=list)
    policy_verdict: str
    tool_name: str | None
    outcome: str
    session_id: str
    actor_id: str
    policy_overrode_decider: bool
    confidence: float | None = None


TRACE_FIELDS = (
    "user_request",
    "route",
    "evidence_ids",
    "decision_contract_version",
    "answers",
    "policy_verdict",
    "tool_name",
    "outcome",
    "session_id",
    "actor_id",
    "policy_overrode_decider",
    "confidence",
)
