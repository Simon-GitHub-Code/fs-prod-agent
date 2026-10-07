"""LangGraph runner for the two desk workflows. Nodes call the domain arithmetic."""

from collections.abc import Callable
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from fs_prod_agent.adapters.local.books import IPS, QUARTERLY_SNAPSHOT
from fs_prod_agent.adapters.local.fakes import _render_breaches
from fs_prod_agent.application.registry import workflow_by_id
from fs_prod_agent.application.state import AgentState
from fs_prod_agent.domain.models import Briefing, Mandate, PortfolioSnapshot
from fs_prod_agent.domain.oversight import performance_briefing, range_breaches


class _GraphState(TypedDict, total=False):
    snapshot: PortfolioSnapshot
    mandate: Mandate
    briefing: Briefing
    text: str


def _load_holdings(state: _GraphState) -> _GraphState:
    return {"snapshot": QUARTERLY_SNAPSHOT}


def _load_mandate(state: _GraphState) -> _GraphState:
    return {"mandate": IPS}


def _compute_return_versus_benchmark(state: _GraphState) -> _GraphState:
    snapshot = state["snapshot"]
    return {"briefing": performance_briefing(snapshot)}


def _render_briefing(state: _GraphState) -> _GraphState:
    return {"text": state["briefing"].body}


def _compute_range_breaches(state: _GraphState) -> _GraphState:
    found = range_breaches(state["snapshot"].holdings, state["mandate"].ranges)
    return {"text": _render_breaches(found)}


_NODES: dict[str, Callable[[_GraphState], _GraphState]] = {
    "load_holdings": _load_holdings,
    "load_mandate": _load_mandate,
    "compute_return_versus_benchmark": _compute_return_versus_benchmark,
    "render_briefing": _render_briefing,
    "compute_range_breaches": _compute_range_breaches,
}


def _compile(steps: tuple[str, ...]):
    graph = StateGraph(_GraphState)
    for name in steps:
        graph.add_node(name, _NODES[name])
    graph.add_edge(START, steps[0])
    for left, right in zip(steps, steps[1:], strict=False):
        graph.add_edge(left, right)
    graph.add_edge(steps[-1], END)
    return graph.compile()


class LangGraphWorkflow:
    """Runs a registered workflow as a LangGraph. The book stays in the domain functions."""

    def run(self, workflow_id: str, state: AgentState) -> str:
        del state
        spec = workflow_by_id(workflow_id)
        result = _compile(spec.steps).invoke({})
        return result["text"]
