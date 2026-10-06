"""Deterministic authority. A model signal never grants permission by itself."""

from enum import Enum

from fs_prod_agent.decisions.contract import DecisionResult
from fs_prod_agent.domain.models import Action, Effect, Principal

CONFIDENCE_THRESHOLD = 0.8
HUMAN_THRESHOLD = 0.5


class Verdict(str, Enum):
    approve = "approve"
    review = "review"
    reject = "reject"
    failed = "failed"
    uncertain = "uncertain"


def _unusable(decision: DecisionResult) -> Verdict | None:
    if not decision.available or decision.invalid:
        return Verdict.failed
    return None


def _route_signal(decision: DecisionResult) -> Verdict | None:
    route = decision.answers.get("route")
    if route is None:
        return None
    if route.confidence is None or route.confidence < CONFIDENCE_THRESHOLD:
        return Verdict.uncertain
    if route.choice == "refuse":
        return Verdict.reject
    if route.choice == "clarify":
        return Verdict.uncertain
    return None


def _needs_human(decision: DecisionResult) -> bool:
    answer = decision.answers.get("needs_human")
    return answer is not None and answer.noul is not None and answer.noul >= HUMAN_THRESHOLD


def admit(decision: DecisionResult) -> Verdict:
    """Whether the ingress route may start. This does not execute a tool."""
    blocked = _unusable(decision)
    if blocked is not None:
        return blocked
    route_verdict = _route_signal(decision)
    if route_verdict is not None:
        return route_verdict
    if _needs_human(decision):
        return Verdict.review
    route = decision.answers.get("route")
    if route is not None and route.choice in {"workflow", "agent"}:
        return Verdict.approve
    return Verdict.uncertain


def authorize(principal: Principal, action: Action, decision: DecisionResult) -> Verdict:
    """Whether a proposed tool call may run.

    Unavailable or invalid decisions fail closed. Missing scope rejects.
    A mutating tool is always review, including when the decision says proceed.
    Approve is only a confident proceed on a read tool the principal may call.
    """
    blocked = _unusable(decision)
    if blocked is not None:
        return blocked
    if not principal.allows(action.tool_name):
        return Verdict.reject
    if action.effect is Effect.mutate:
        return Verdict.review
    route_verdict = _route_signal(decision)
    if route_verdict is not None:
        return route_verdict
    gate = decision.answers.get("tool_gate")
    if gate is not None:
        if gate.confidence is None or gate.confidence < CONFIDENCE_THRESHOLD:
            return Verdict.uncertain
        if gate.choice in {"confirm", "guide"}:
            return Verdict.review
        if gate.choice == "deny":
            return Verdict.reject
        if gate.choice != "proceed":
            return Verdict.failed
    if _needs_human(decision):
        return Verdict.review
    if action.effect is Effect.read and gate is not None and gate.choice == "proceed":
        return Verdict.approve
    # Same verdict as the return below, so a mutated condition changes nothing.
    if action.effect is Effect.draft:  # pragma: no mutate
        return Verdict.review
    return Verdict.review


def overrode(decision: DecisionResult, verdict: Verdict) -> bool:
    """True when policy refused to follow a confident proceed."""
    gate = decision.answers.get("tool_gate")
    if gate is None or gate.choice != "proceed":
        return False
    if gate.confidence is None or gate.confidence < CONFIDENCE_THRESHOLD:
        return False
    return verdict is not Verdict.approve
