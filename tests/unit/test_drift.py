"""Drift is a pure comparison of two trace windows."""

import json

from fs_prod_agent.observe.decision_chain import TraceRecord
from fs_prod_agent.observe.drift import detect_shift
from tests.fitness.support import REPO, imported_modules


def test_drift_module_does_not_call_a_model():
    modules = set(imported_modules(REPO / "src" / "fs_prod_agent" / "observe" / "drift.py"))
    assert modules == {"pydantic", "fs_prod_agent.observe.decision_chain"}


def test_override_rate_jump_is_a_shift():
    window = json.loads((REPO / "evals" / "drift" / "override_shift.json").read_text(encoding="utf-8"))
    delta = window["override_rate_delta"]
    baseline = _traces(window["baseline"])
    current = _traces(window["current"])
    report = detect_shift(baseline, current, override_rate_delta=delta)
    assert report.override_rate_baseline == 0.0
    assert report.override_rate_current == 0.4
    assert report.shifted is True
    assert "human override rate increased" in report.reasons
    assert report.route_mix_current == {"agent": 0.4, "refuse": 0.2, "workflow": 0.4}
    confidences = [row["confidence"] for row in window["current"]]
    assert report.mean_confidence_current == sum(confidences) / len(confidences)

    steady = detect_shift(baseline, _traces(window["steady"]), override_rate_delta=delta)
    assert steady.shifted is False
    assert steady.reasons == []

    below_threshold = detect_shift(baseline, current, override_rate_delta=0.5)
    assert below_threshold.shifted is False


def test_empty_windows_are_not_a_shift():
    report = detect_shift([], [])
    assert report.shifted is False
    assert report.override_rate_baseline == 0.0
    assert report.override_rate_current == 0.0
    assert report.mean_confidence_current == 0.0
    assert report.route_mix_current == {}


def _traces(rows: list[dict]) -> list[TraceRecord]:
    traces: list[TraceRecord] = []
    for index, row in enumerate(rows):
        traces.append(
            TraceRecord(
                user_request="fixture",
                route=row["route"],
                evidence_ids=[],
                decision_contract_version="v1",
                answers=[],
                policy_verdict="review" if row["policy_overrode_decider"] else "approve",
                tool_name=None,
                outcome="fixture",
                session_id=f"s{index}",
                actor_id="analyst-1",
                policy_overrode_decider=row["policy_overrode_decider"],
                confidence=row["confidence"],
            )
        )
    return traces
