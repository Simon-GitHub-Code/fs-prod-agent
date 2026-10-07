"""Run labelled cases through an app and score them. The caller builds the app, so this imports no adapter."""

import time
from collections.abc import Callable
from typing import Any

from fs_prod_agent.application.registry import agents
from fs_prod_agent.domain.models import Action
from fs_prod_agent.evals.loader import EvalCase
from fs_prod_agent.evals.score import CaseResult, Scorecard, score
from fs_prod_agent.mcp_servers.catalog import MANIFESTS

MUTATE_TOOLS = frozenset(manifest.name for manifest in MANIFESTS if manifest.effect == "mutate")
AGENT_TOOLS = frozenset(name for spec in agents() for name in spec.tool_names)


def score_suite(label: str, cases: list[EvalCase], factory: Callable[[], Any]) -> Scorecard:
    return score(label, run_suite(cases, factory), MUTATE_TOOLS, AGENT_TOOLS)


def run_suite(cases: list[EvalCase], factory: Callable[[], Any]) -> list[CaseResult]:
    """One fresh app per case, so no session or queue carries over between cases."""
    return [_run_case(case, factory()) for case in cases]


def _run_case(case: EvalCase, app: Any) -> CaseResult:
    started = time.perf_counter()
    if case.stage == "ingress":
        trace = app.pipeline.run(case.request, case.principal, case.id)
    else:
        if case.tool_name is None or case.effect is None:
            raise ValueError(f"{case.id} is a tool case without a tool")
        action = Action(tool_name=case.tool_name, effect=case.effect)
        trace = app.pipeline.dispatch_tool(case.request, case.principal, action, case.id)
    return CaseResult(
        case_id=case.id,
        category=case.category,
        stage=case.stage,
        expected_verdict=case.expected_verdict,
        verdict=trace.policy_verdict,
        expected_route=case.expected_route,
        route=trace.route,
        expected_workflow_id=case.expected_workflow_id,
        workflow_id=trace.workflow_id,
        confidence=trace.confidence,
        seconds=time.perf_counter() - started,
        tools_called=_executed_tools(app),
        outcome=trace.outcome,
    )


def _executed_tools(app: Any) -> list[str]:
    # The local gateway records each call it executed. A gated or refused call never reaches it.
    return list(getattr(app.pipeline.services.gateway, "calls", []))
