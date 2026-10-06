"""The fixture decider matches the verdict recorded on every eval case."""

import pytest

from fs_prod_agent.composition import build
from fs_prod_agent.domain.models import Action
from fs_prod_agent.evals.loader import EvalCase, load_cases
from tests.fitness.support import REPO

_TASKS = REPO / "evals" / "tasks"
_CONTRACTS = REPO / "evals" / "decision_contracts" / "v1"


@pytest.mark.parametrize("case", [*load_cases(_TASKS), *load_cases(_CONTRACTS)], ids=lambda case: case.id)
def test_fixture_decider_matches_the_expected_verdict(case: EvalCase):
    app = build("local")
    if case.stage == "ingress":
        trace = app.pipeline.run(case.request, case.principal, case.id)
    else:
        assert case.tool_name is not None and case.effect is not None
        action = Action(tool_name=case.tool_name, effect=case.effect)
        trace = app.pipeline.dispatch_tool(case.request, case.principal, action, case.id)
    assert trace.policy_verdict == case.expected_verdict
    if case.expected_route is not None:
        assert trace.route == case.expected_route
    if case.expected_workflow_id is not None:
        assert trace.workflow_id == case.expected_workflow_id
    if case.stage == "tool" and case.expected_verdict == "review":
        assert trace.tool_name is None
        assert trace.outcome == "pending_review"
        assert trace.policy_overrode_decider is True
