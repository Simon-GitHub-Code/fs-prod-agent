"""Start exactly one path. Callers pass the runners; this module does not construct them."""

from collections.abc import Callable

from fs_prod_agent.application.state import AgentState
from fs_prod_agent.decisions.contract import DecisionResult
from fs_prod_agent.ports.protocols import AgentRunner, WorkflowRunner


def dispatch_route(
    decision: DecisionResult,
    state: AgentState,
    workflow: WorkflowRunner,
    agent: AgentRunner,
    clarify: Callable[[AgentState], str],
    refuse: Callable[[AgentState], str],
) -> str:
    route = decision.answers["route"].choice
    if route == "workflow":
        workflow_id = decision.answers["workflow_id"].choice
        if workflow_id is None:
            raise ValueError("workflow route missing workflow_id")
        workflow.run(workflow_id, state)
        return "workflow"
    if route == "agent":
        agent.run(state)
        return "agent"
    if route == "clarify":
        clarify(state)
        return "clarify"
    if route == "refuse":
        refuse(state)
        return "refuse"
    raise ValueError(f"unknown route: {route}")
