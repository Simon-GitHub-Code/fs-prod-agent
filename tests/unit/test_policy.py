"""Policy owns authority. A confident proceed is not permission."""

import pytest

from fs_prod_agent.decisions.contract import Answer, DecisionResult, validate_decision
from fs_prod_agent.decisions.v1.route import INGRESS_QUESTIONS
from fs_prod_agent.domain.models import Action, Effect, Principal, Role
from fs_prod_agent.policy.authorize import (
    CONFIDENCE_THRESHOLD,
    HUMAN_THRESHOLD,
    Verdict,
    admit,
    authorize,
    overrode,
)


def test_unavailable_or_invalid_decisions_fail():
    unavailable = DecisionResult(contract_version="v1", available=False, error="down")
    invalid = DecisionResult(contract_version="v1", available=True, invalid=True, error="schema")
    action = Action(tool_name="search_policy", effect=Effect.read)
    principal = _principal(["search_policy"])
    for decision in (unavailable, invalid):
        assert admit(decision) is Verdict.failed
        assert authorize(principal, action, decision) is Verdict.failed


def test_unknown_choice_is_invalid_and_fails():
    raw = _ingress(route="invent")
    decision = validate_decision(raw, INGRESS_QUESTIONS)
    assert decision.invalid is True
    assert decision.error == "unknown choice for route"
    assert admit(decision) is Verdict.failed


def test_low_route_confidence_is_uncertain():
    below = CONFIDENCE_THRESHOLD - 0.01
    assert admit(_ingress(route="workflow", confidence=below)) is Verdict.uncertain
    assert admit(_ingress(route="agent", confidence=below)) is Verdict.uncertain
    assert admit(_ingress(route="workflow", confidence=None)) is Verdict.uncertain


def test_route_confidence_at_the_threshold_may_start():
    assert admit(_ingress(route="workflow", confidence=CONFIDENCE_THRESHOLD)) is Verdict.approve
    assert admit(_ingress(route="agent", confidence=CONFIDENCE_THRESHOLD)) is Verdict.approve


def test_refuse_rejects_and_clarify_is_uncertain():
    assert admit(_ingress(route="refuse")) is Verdict.reject
    assert admit(_ingress(route="clarify")) is Verdict.uncertain


def test_clarify_stays_uncertain_when_a_person_is_required():
    assert admit(_ingress(route="clarify", needs_human=HUMAN_THRESHOLD)) is Verdict.uncertain


def test_a_decision_with_no_route_does_not_start():
    decision = DecisionResult(contract_version="v1", available=True, answers={})
    assert admit(decision) is Verdict.uncertain


def test_needs_human_reviews_a_confident_workflow():
    assert admit(_ingress(route="workflow", needs_human=0.5)) is Verdict.review


@pytest.mark.parametrize(
    ("effect", "in_scope", "expected"),
    [
        (Effect.read, True, Verdict.approve),
        (Effect.read, False, Verdict.reject),
        (Effect.draft, True, Verdict.review),
        (Effect.draft, False, Verdict.reject),
        (Effect.mutate, True, Verdict.review),
        (Effect.mutate, False, Verdict.reject),
    ],
)
def test_approve_is_only_a_confident_read_in_scope(effect: Effect, in_scope: bool, expected: Verdict):
    tool = "submit_committee_paper" if effect is Effect.mutate else "search_policy"
    if effect is Effect.draft:
        tool = "draft_briefing"
    scopes = [tool] if in_scope else []
    verdict = authorize(_principal(scopes), Action(tool_name=tool, effect=effect), _gate("proceed", 0.99))
    assert verdict is expected


def test_tool_gate_choices_do_not_grant_a_mutating_call():
    principal = _principal(["search_policy", "submit_committee_paper"])
    read = Action(tool_name="search_policy", effect=Effect.read)
    assert authorize(principal, read, _gate("deny", 0.99)) is Verdict.reject
    assert authorize(principal, read, _gate("guide", 0.99)) is Verdict.review
    assert authorize(principal, read, _gate("confirm", 0.99)) is Verdict.review
    assert authorize(principal, read, _gate("proceed", CONFIDENCE_THRESHOLD - 0.01)) is Verdict.uncertain


def test_tool_gate_at_the_threshold_approves_a_read():
    verdict = authorize(
        _principal(["search_policy"]),
        Action(tool_name="search_policy", effect=Effect.read),
        _gate("proceed", CONFIDENCE_THRESHOLD),
    )
    assert verdict is Verdict.approve


def test_a_tool_gate_without_confidence_is_uncertain():
    decision = _gate("proceed", CONFIDENCE_THRESHOLD)
    answers = dict(decision.answers)
    answers["tool_gate"] = Answer(question_id="tool_gate", type="choice", choice="proceed", confidence=None)
    verdict = authorize(
        _principal(["search_policy"]),
        Action(tool_name="search_policy", effect=Effect.read),
        decision.model_copy(update={"answers": answers}),
    )
    assert verdict is Verdict.uncertain


def test_a_refused_route_rejects_the_tool_even_when_the_gate_says_proceed():
    decision = DecisionResult(
        contract_version="v1",
        available=True,
        answers={
            "route": _choice("route", "refuse", CONFIDENCE_THRESHOLD),
            "tool_gate": _choice("tool_gate", "proceed", CONFIDENCE_THRESHOLD),
        },
    )
    verdict = authorize(
        _principal(["search_policy"]),
        Action(tool_name="search_policy", effect=Effect.read),
        decision,
    )
    assert verdict is Verdict.reject


def test_needs_human_reviews_a_confident_proceed():
    decision = _with_needs_human(_gate("proceed", CONFIDENCE_THRESHOLD), HUMAN_THRESHOLD)
    verdict = authorize(
        _principal(["search_policy"]),
        Action(tool_name="search_policy", effect=Effect.read),
        decision,
    )
    assert verdict is Verdict.review


def test_needs_human_below_the_threshold_can_still_approve():
    decision = _with_needs_human(_gate("proceed", CONFIDENCE_THRESHOLD), HUMAN_THRESHOLD - 0.01)
    verdict = authorize(
        _principal(["search_policy"]),
        Action(tool_name="search_policy", effect=Effect.read),
        decision,
    )
    assert verdict is Verdict.approve


def test_policy_override_is_a_confident_proceed_that_did_not_run():
    proceed = _gate("proceed", CONFIDENCE_THRESHOLD)
    assert overrode(proceed, Verdict.review) is True
    assert overrode(proceed, Verdict.approve) is False
    assert overrode(_gate("proceed", CONFIDENCE_THRESHOLD - 0.01), Verdict.review) is False
    assert overrode(_gate("deny", CONFIDENCE_THRESHOLD), Verdict.reject) is False
    missing = _gate("proceed", CONFIDENCE_THRESHOLD)
    answers = dict(missing.answers)
    answers["tool_gate"] = Answer(question_id="tool_gate", type="choice", choice="proceed", confidence=None)
    assert overrode(missing.model_copy(update={"answers": answers}), Verdict.review) is False


def _principal(scopes: list[str]) -> Principal:
    return Principal(actor_id="analyst-1", role=Role.analyst, scopes=scopes)


def _ingress(
    route: str,
    confidence: float | None = 0.95,
    workflow_id: str = "performance_pack",
    needs_human: float = 0.1,
) -> DecisionResult:
    return DecisionResult(
        contract_version="v1",
        available=True,
        answers={
            "route": _choice("route", route, confidence),
            "workflow_id": _choice("workflow_id", workflow_id, confidence),
            "materiality": Answer(question_id="materiality", type="score", score=1.0, confidence=confidence),
            "needs_human": Answer(question_id="needs_human", type="noul", noul=needs_human, confidence=needs_human),
        },
    )


def _gate(choice: str, confidence: float) -> DecisionResult:
    return DecisionResult(
        contract_version="v1",
        available=True,
        answers={
            "tool_gate": _choice("tool_gate", choice, confidence),
            "arguments_grounded": Answer(question_id="arguments_grounded", type="noul", noul=0.9, confidence=0.9),
            "required_info_missing": Answer(
                question_id="required_info_missing", type="noul", noul=0.05, confidence=0.05
            ),
            "call_premature": Answer(question_id="call_premature", type="noul", noul=0.05, confidence=0.05),
        },
    )


def _with_needs_human(decision: DecisionResult, noul: float) -> DecisionResult:
    answers = dict(decision.answers)
    answers["needs_human"] = Answer(question_id="needs_human", type="noul", noul=noul, confidence=noul)
    return decision.model_copy(update={"answers": answers})


def _choice(question_id: str, choice: str, confidence: float | None) -> Answer:
    probabilities = {} if confidence is None else {choice: confidence}
    return Answer(
        question_id=question_id,
        type="choice",
        choice=choice,
        confidence=confidence,
        probabilities=probabilities,
    )
