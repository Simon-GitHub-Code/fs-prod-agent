"""Ports. Adapters implement these. Application code depends on them."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from fs_prod_agent.application.state import AgentState
    from fs_prod_agent.decisions.contract import DecisionResult
    from fs_prod_agent.domain.models import Principal
    from fs_prod_agent.observe.decision_chain import TraceRecord
    from fs_prod_agent.observe.review import ReviewItem


class DecisionPort(Protocol):
    def evaluate(self, state: AgentState, contract: str) -> DecisionResult: ...


class ModelPort(Protocol):
    def complete(self, prompt: str) -> str: ...


class MemoryPort(Protocol):
    def append_turn(self, actor_id: str, session_id: str, text: str) -> None: ...

    def load_session(self, actor_id: str, session_id: str) -> list[str]: ...

    def remember(self, actor_id: str, kind: str, text: str) -> None: ...

    def recall(self, actor_id: str, kind: str) -> list[str]: ...


class GatewayPort(Protocol):
    def call(self, tool_name: str, arguments: dict[str, str]) -> str: ...


class IdentityPort(Protocol):
    def principal(self, actor_id: str) -> Principal: ...


class RetrieverPort(Protocol):
    def retrieve(self, request: str) -> list[str]: ...


class RuntimePort(Protocol):
    def invoke(self, payload: dict[str, str], session_id: str) -> TraceRecord: ...


class TracePort(Protocol):
    def record(self, trace: TraceRecord) -> None: ...

    def records(self) -> list[TraceRecord]: ...


class HumanReviewPort(Protocol):
    def enqueue(self, session_id: str, actor_id: str, tool_name: str) -> ReviewItem: ...

    def pending(self, session_id: str) -> list[ReviewItem]: ...


class WorkflowRunner(Protocol):
    def run(self, workflow_id: str, state: AgentState) -> str: ...


class AgentRunner(Protocol):
    def run(self, state: AgentState) -> str: ...
