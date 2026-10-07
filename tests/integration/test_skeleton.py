"""The local fixture pipeline runs the oversight desk's three paths."""

import json

import pytest

from fs_prod_agent.adapters.local.books import IPS, QUARTERLY_SNAPSHOT
from fs_prod_agent.composition import build
from fs_prod_agent.domain.models import Action, Effect, Principal, Role
from fs_prod_agent.domain.oversight import performance_briefing, range_breaches
from tests.fitness.support import REPO


def test_quarterly_pack_mandate_check_and_open_question_take_one_path_each():
    app = build("local")
    quarterly = _task("performance_pack")
    mandate = _task("mandate_check")
    analyst = _task("oversight_analyst")
    order = _contract("refuse_order")

    pack = app.invoke({"actor_id": "analyst-1", "request": quarterly["request"]}, "pack")
    assert pack.route == "workflow"
    assert pack.workflow_id == "performance_pack"
    assert pack.policy_verdict == "approve"
    assert [answer.score for answer in pack.answers if answer.question_id == "materiality"] == [1.0]
    assert performance_briefing(QUARTERLY_SNAPSHOT).body in pack.outcome

    checked = app.invoke({"actor_id": "analyst-1", "request": mandate["request"]}, "mandate")
    assert checked.route == "workflow"
    assert checked.workflow_id == "mandate_check"
    assert checked.policy_verdict == "approve"
    assert [answer.score for answer in checked.answers if answer.question_id == "materiality"] == [1.0, 2.0]
    breaches = range_breaches(QUARTERLY_SNAPSHOT.holdings, IPS.ranges)
    assert [item.asset_class for item in breaches] == ["private_markets"]
    assert "private_markets 8% outside 0%-5%" in checked.outcome

    open_question = app.invoke({"actor_id": "analyst-1", "request": analyst["request"]}, "analyst")
    assert open_question.route == "agent"
    assert open_question.workflow_id is None
    assert open_question.policy_verdict == "approve"
    called = app.pipeline.services.gateway.calls
    assert called
    listed = [part.strip() for part in open_question.outcome.split("tools:", 1)[1].split(",")]
    assert listed == called

    refused = app.invoke({"actor_id": "analyst-1", "request": order["request"]}, "order")
    assert refused.route == "refuse"
    assert refused.policy_verdict == "reject"
    assert refused.outcome == "refused"
    assert refused.workflow_id is None


def test_read_tool_in_scope_reaches_the_gateway():
    app = build("local")
    calls: list[str] = []

    class _Gateway:
        def call(self, tool_name: str, arguments: dict[str, str]) -> str:
            calls.append(tool_name)
            return f"{tool_name}:ok"

    app.pipeline.services.gateway = _Gateway()
    trace = app.invoke(
        {
            "actor_id": "analyst-1",
            "request": "Show the holdings snapshot.",
            "tool_name": "get_holdings",
            "effect": "read",
        },
        "holdings",
    )
    assert trace.policy_verdict == "approve"
    assert trace.tool_name == "get_holdings"
    assert trace.outcome == "get_holdings:ok"
    assert trace.policy_overrode_decider is False
    assert calls == ["get_holdings"]


def test_sessions_do_not_share_turns():
    app = build("local")
    quarterly = _task("performance_pack")["request"]
    analyst = _task("oversight_analyst")["request"]
    app.invoke({"actor_id": "analyst-1", "request": quarterly}, "shared")
    other = Principal(actor_id="cio-1", role=Role.cio, scopes=["search_policy"])
    app.pipeline.run(analyst, other, "shared")
    assert app.memory.load_session("analyst-1", "shared") == [quarterly]
    assert app.memory.load_session("cio-1", "shared") == [analyst]
    assert app.memory.load_session("analyst-1", "other-session") == []


def test_each_build_has_its_own_memory():
    first = build("local")
    second = build("local")
    request = _task("performance_pack")["request"]
    first.invoke({"actor_id": "analyst-1", "request": request}, "s1")
    assert second.memory.load_session("analyst-1", "s1") == []


def test_memory_keeps_only_allowed_facts():
    app = build("local")
    app.memory.remember("analyst-1", "committee_outcome", "paper deferred")
    app.memory.remember("analyst-1", "watchlist_status", "manager B remains on watch")
    assert app.memory.recall("analyst-1", "committee_outcome") == ["paper deferred"]
    with pytest.raises(PermissionError):
        app.memory.remember("analyst-1", "model_draft", "raw text")


def test_draft_tool_does_not_run():
    app = build("local")
    action = Action(tool_name="draft_briefing", effect=Effect.draft)
    principal = app.identity.principal("analyst-1")
    trace = app.pipeline.dispatch_tool("Draft a briefing on manager B.", principal, action, "draft")
    assert trace.policy_verdict == "review"
    assert trace.tool_name is None
    assert trace.policy_overrode_decider is True


def _task(name: str) -> dict:
    return json.loads((REPO / "evals" / "tasks" / f"{name}.json").read_text(encoding="utf-8"))


def _contract(name: str) -> dict:
    return json.loads((REPO / "evals" / "decision_contracts" / "v1" / f"{name}.json").read_text(encoding="utf-8"))
