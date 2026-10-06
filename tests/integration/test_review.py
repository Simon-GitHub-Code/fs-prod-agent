"""A mutating verdict waits for a person. The agent cannot mark it approved."""

import json

import pytest
from pydantic import ValidationError

from fs_prod_agent.composition import build
from fs_prod_agent.observe.review import ReviewItem
from tests.fitness.support import REPO


def test_committee_paper_stops_in_the_human_queue():
    case = json.loads(
        (REPO / "evals" / "decision_contracts" / "v1" / "committee_paper.json").read_text(encoding="utf-8")
    )
    app = build("local")
    calls: list[str] = []

    class _Gateway:
        def call(self, tool_name: str, arguments: dict[str, str]) -> str:
            calls.append(tool_name)
            return "called"

    app.pipeline.services.gateway = _Gateway()
    trace = app.invoke(
        {
            "actor_id": case["actor_id"],
            "request": case["request"],
            "tool_name": case["tool_name"],
            "effect": case["effect"],
        },
        "committee-session",
    )
    assert trace.policy_verdict == "review"
    assert trace.tool_name is None
    assert trace.outcome == "pending_review"
    assert trace.policy_overrode_decider is True
    assert calls == []
    pending = app.human_review.pending("committee-session")
    assert len(pending) == 1
    item = pending[0]
    assert item.tool_name == "submit_committee_paper"
    assert item.actor_id == "analyst-1"
    assert item.status == "pending"
    assert item.resume_token
    assert not hasattr(ReviewItem, "approve")
    with pytest.raises(ValidationError):
        item.status = "approve"
