"""Each route choice starts one runner. The pipeline starts a runner only after admit approves."""

import pytest

from fs_prod_agent.adapters.local.fakes import (
    InMemoryMemory,
    InMemoryReview,
    JsonlTrace,
    LocalGateway,
    ScriptedModel,
    StaticRetriever,
    default_principal,
)
from fs_prod_agent.application.pipeline import Pipeline, Services
from fs_prod_agent.application.router import dispatch_route
from fs_prod_agent.application.state import build_agent_state
from fs_prod_agent.decisions.contract import Answer, DecisionResult
from fs_prod_agent.policy.authorize import Verdict


class _Runner:
    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        self.calls = calls

    def run(self, *args: object) -> str:
        self.calls.append(self.name)
        return self.name


@pytest.mark.parametrize("route", ["workflow", "agent", "clarify", "refuse"])
def test_each_route_invokes_exactly_one_runner(route: str):
    calls: list[str] = []
    workflow = _Runner("workflow", calls)
    agent = _Runner("agent", calls)

    def clarify(state: object) -> str:
        calls.append("clarify")
        return "clarify"

    def refuse(state: object) -> str:
        calls.append("refuse")
        return "refuse"

    state = build_agent_state("question", ["ips-excerpt"], None, default_principal())
    chosen = dispatch_route(_decision(route), state, workflow, agent, clarify, refuse)
    assert chosen == route
    assert calls == [route]


@pytest.mark.parametrize(
    ("route", "expected_verdict", "expected_runner"),
    [
        ("workflow", Verdict.approve, "workflow"),
        ("agent", Verdict.approve, "agent"),
        ("refuse", Verdict.reject, None),
        ("clarify", Verdict.uncertain, None),
    ],
)
def test_pipeline_starts_a_runner_only_when_admit_approves(
    route: str,
    expected_verdict: Verdict,
    expected_runner: str | None,
):
    calls: list[str] = []
    workflow = _Runner("workflow", calls)
    agent = _Runner("agent", calls)
    pipeline = Pipeline(
        Services(
            decision=_Fixed(_decision(route)),
            model=ScriptedModel(),
            memory=InMemoryMemory(),
            gateway=LocalGateway(),
            retriever=StaticRetriever(),
            trace=JsonlTrace(),
            human_review=InMemoryReview(),
            workflow=workflow,
            agent=agent,
        )
    )
    trace = pipeline.run("question", default_principal(), "session-1")
    assert trace.policy_verdict == expected_verdict.value
    assert calls == ([] if expected_runner is None else [expected_runner])


def test_failed_decision_stops_without_a_runner():
    calls: list[str] = []
    pipeline = Pipeline(
        Services(
            decision=_Fixed(DecisionResult(contract_version="v1", available=False, error="down")),
            model=ScriptedModel(),
            memory=InMemoryMemory(),
            gateway=LocalGateway(),
            retriever=StaticRetriever(),
            trace=JsonlTrace(),
            human_review=InMemoryReview(),
            workflow=_Runner("workflow", calls),
            agent=_Runner("agent", calls),
        )
    )
    trace = pipeline.run("question", default_principal(), "session-1")
    assert trace.policy_verdict == Verdict.failed.value
    assert trace.outcome == "failed"
    assert calls == []


class _Fixed:
    def __init__(self, result: DecisionResult) -> None:
        self.result = result

    def evaluate(self, state: object, contract: str) -> DecisionResult:
        return self.result


def _decision(route: str) -> DecisionResult:
    workflow_id = "performance_pack" if route == "workflow" else "none"
    return DecisionResult(
        contract_version="v1",
        available=True,
        answers={
            "route": Answer(question_id="route", type="choice", choice=route, confidence=0.95),
            "workflow_id": Answer(question_id="workflow_id", type="choice", choice=workflow_id, confidence=0.95),
            "materiality": Answer(question_id="materiality", type="score", score=1.0, confidence=0.95),
            "needs_human": Answer(question_id="needs_human", type="noul", noul=0.1, confidence=0.1),
        },
    )
