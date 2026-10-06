"""A completed fixture run writes one decision-chain record."""

import json

from fs_prod_agent.adapters.local.books import QUARTERLY_SNAPSHOT
from fs_prod_agent.composition import build
from fs_prod_agent.domain.oversight import performance_briefing
from fs_prod_agent.observe.decision_chain import TRACE_FIELDS
from tests.fitness.support import REPO


def test_quarterly_run_writes_the_trace_schema():
    request = json.loads((REPO / "evals" / "tasks" / "performance_pack.json").read_text(encoding="utf-8"))["request"]
    app = build("local")
    trace = app.invoke({"actor_id": "analyst-1", "request": request}, "quarterly-session")
    recorded = app.trace.records()
    assert recorded == [trace]
    dumped = trace.model_dump()
    for field in TRACE_FIELDS:
        assert field in dumped
    assert trace.user_request == request
    assert trace.route == "workflow"
    assert trace.workflow_id == "performance_pack"
    assert trace.evidence_ids == ["ips-excerpt", "saa-policy"]
    assert trace.decision_contract_version == "v1"
    assert trace.policy_verdict == "approve"
    assert trace.tool_name is None
    assert trace.outcome == performance_briefing(QUARTERLY_SNAPSHOT).body
    assert trace.session_id == "quarterly-session"
    assert trace.actor_id == "analyst-1"
    assert trace.policy_overrode_decider is False
    assert trace.confidence is not None
    assert trace.answers
    for answer in trace.answers:
        assert answer.confidence is not None or answer.probabilities
