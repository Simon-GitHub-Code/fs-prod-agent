"""In-memory adapters for the local profile. No network and no AWS SDK."""

from dataclasses import dataclass
from pathlib import Path

from fs_prod_agent.adapters.local.books import IPS, QUARTERLY_SNAPSHOT, holdings_text, manager_report, policy_text
from fs_prod_agent.application.registry import workflow_by_id
from fs_prod_agent.application.state import AgentState
from fs_prod_agent.decisions.contract import Answer, DecisionResult
from fs_prod_agent.decisions.v1.route import INGRESS_QUESTIONS
from fs_prod_agent.decisions.v1.tool_gate import TOOL_GATE_QUESTIONS
from fs_prod_agent.domain.models import Briefing, Mandate, PortfolioSnapshot, Principal, RangeBreach, Role
from fs_prod_agent.domain.oversight import performance_briefing, range_breaches
from fs_prod_agent.mcp_servers.catalog import manifest_for
from fs_prod_agent.observe.decision_chain import TraceRecord
from fs_prod_agent.observe.review import ReviewItem
from fs_prod_agent.policy.memory_rules import may_remember

_ROUTE_KEYS = set(INGRESS_QUESTIONS[0].criteria)  # type: ignore[arg-type]
_WORKFLOW_KEYS = set(INGRESS_QUESTIONS[1].criteria)  # type: ignore[arg-type]
_GATE_KEYS = set(TOOL_GATE_QUESTIONS[0].criteria)  # type: ignore[arg-type]


def _choice(question_id: str, selected: str, confidence: float, keys: set[str]) -> Answer:
    others = [key for key in sorted(keys) if key != selected]
    share = 0.0 if not others else (1.0 - confidence) / len(others)
    probabilities = {key: confidence if key == selected else share for key in sorted(keys)}
    return Answer(
        question_id=question_id,
        type="choice",
        choice=selected,
        confidence=confidence,
        probabilities=probabilities,
    )


def _score(question_id: str, value: float, confidence: float) -> Answer:
    chosen = str(int(round(value)))
    share = (1.0 - confidence) / 3
    probabilities = {str(index): confidence if str(index) == chosen else share for index in range(4)}
    return Answer(
        question_id=question_id,
        type="score",
        score=value,
        confidence=confidence,
        probabilities=probabilities,
    )


def _noul(question_id: str, value: float) -> Answer:
    return Answer(
        question_id=question_id,
        type="noul",
        noul=value,
        confidence=value,
        probabilities={"yes": value, "no": 1.0 - value},
    )


def _ingress(route: str, workflow_id: str, materiality: float, needs_human: float, confidence: float) -> DecisionResult:
    return DecisionResult(
        contract_version="v1",
        available=True,
        answers={
            "route": _choice("route", route, confidence, _ROUTE_KEYS),
            "workflow_id": _choice("workflow_id", workflow_id, confidence, _WORKFLOW_KEYS),
            "materiality": _score("materiality", materiality, confidence),
            "needs_human": _noul("needs_human", needs_human),
        },
    )


class FixtureDecision:
    """Scripted decisions for the three skeleton requests. Not a model."""

    def evaluate(self, state: AgentState, contract: str) -> DecisionResult:
        if contract == "materiality":
            return DecisionResult(
                contract_version="v1",
                available=True,
                answers={"materiality": _score("materiality", 2.0, 0.9)},
            )
        if contract == "tool_gate":
            return DecisionResult(
                contract_version="v1",
                available=True,
                answers={
                    "tool_gate": _choice("tool_gate", "proceed", 0.99, _GATE_KEYS),
                    "arguments_grounded": _noul("arguments_grounded", 0.9),
                    "required_info_missing": _noul("required_info_missing", 0.05),
                    "call_premature": _noul("call_premature", 0.05),
                },
            )
        if contract != "ingress":
            return DecisionResult(contract_version="v1", available=False, error=f"unknown contract {contract}")
        text = state.request.lower()
        if "buy" in text and "share" in text:
            return _ingress("refuse", "none", 0.0, 0.1, 0.97)
        if "quarterly" in text:
            return _ingress("workflow", "performance_pack", 1.0, 0.1, 0.95)
        if "mandate check" in text:
            return _ingress("workflow", "mandate_check", 1.0, 0.1, 0.95)
        return _ingress("agent", "none", 1.0, 0.1, 0.9)


class InMemoryMemory:
    def __init__(self) -> None:
        self.sessions: dict[tuple[str, str], list[str]] = {}
        self.facts: dict[tuple[str, str], list[str]] = {}

    def append_turn(self, actor_id: str, session_id: str, text: str) -> None:
        self.sessions.setdefault((actor_id, session_id), []).append(text)

    def load_session(self, actor_id: str, session_id: str) -> list[str]:
        return list(self.sessions.get((actor_id, session_id), []))

    def remember(self, actor_id: str, kind: str, text: str) -> None:
        if not may_remember(kind):
            raise PermissionError(f"{kind} is not a long-term memory")
        self.facts.setdefault((actor_id, kind), []).append(text)

    def recall(self, actor_id: str, kind: str) -> list[str]:
        return list(self.facts.get((actor_id, kind), []))


class LocalGateway:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def call(self, tool_name: str, arguments: dict[str, str]) -> str:
        manifest_for(tool_name)
        self.calls.append(tool_name)
        if tool_name == "get_manager_report":
            return manager_report(arguments.get("query", ""))
        if tool_name == "search_policy":
            return policy_text()
        if tool_name == "get_holdings":
            return holdings_text()
        return f"{tool_name}:ok"


class StaticRetriever:
    def retrieve(self, request: str) -> list[str]:
        return ["ips-excerpt", "saa-policy"]


class InMemoryIdentity:
    def __init__(self, principals: dict[str, Principal]) -> None:
        self._principals = principals

    def principal(self, actor_id: str) -> Principal:
        try:
            return self._principals[actor_id]
        except KeyError as exc:
            raise KeyError(f"unknown actor {actor_id}") from exc


class InMemoryReview:
    def __init__(self) -> None:
        self.items: list[ReviewItem] = []

    def enqueue(self, session_id: str, actor_id: str, tool_name: str) -> ReviewItem:
        item = ReviewItem(session_id=session_id, actor_id=actor_id, tool_name=tool_name)
        self.items.append(item)
        return item

    def pending(self, session_id: str) -> list[ReviewItem]:
        return [item for item in self.items if item.session_id == session_id and item.status == "pending"]


class JsonlTrace:
    def __init__(self, path: Path | None = None) -> None:
        self._records: list[TraceRecord] = []
        self.path = path

    def record(self, trace: TraceRecord) -> None:
        self._records.append(trace)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(trace.model_dump_json() + "\n")

    def records(self) -> list[TraceRecord]:
        return list(self._records)


@dataclass
class _Step:
    snapshot: PortfolioSnapshot | None = None
    mandate: Mandate | None = None
    briefing: Briefing | None = None
    text: str = ""


def _load_holdings(step: _Step) -> None:
    step.snapshot = QUARTERLY_SNAPSHOT


def _load_mandate(step: _Step) -> None:
    step.mandate = IPS


def _compute_return_versus_benchmark(step: _Step) -> None:
    if step.snapshot is None:
        raise ValueError("holdings are not loaded")
    step.briefing = performance_briefing(step.snapshot)


def _render_briefing(step: _Step) -> None:
    if step.briefing is None:
        raise ValueError("the briefing is not computed")
    step.text = step.briefing.body


def _compute_range_breaches(step: _Step) -> None:
    if step.snapshot is None or step.mandate is None:
        raise ValueError("holdings and the mandate are not loaded")
    step.text = _render_breaches(range_breaches(step.snapshot.holdings, step.mandate.ranges))


STEP_TABLE = {
    "load_holdings": _load_holdings,
    "load_mandate": _load_mandate,
    "compute_return_versus_benchmark": _compute_return_versus_benchmark,
    "render_briefing": _render_briefing,
    "compute_range_breaches": _compute_range_breaches,
}


class FixtureWorkflowRunner:
    def run(self, workflow_id: str, state: AgentState) -> str:
        spec = workflow_by_id(workflow_id)
        step = _Step()
        for name in spec.steps:
            STEP_TABLE[name](step)
        return step.text


class FixtureAgentRunner:
    def run(self, state: AgentState) -> str:
        return "oversight_analyst:scripted"


def _render_breaches(breaches: tuple[RangeBreach, ...]) -> str:
    if not breaches:
        return "none"
    return ", ".join(
        f"{item.asset_class} {item.weight:.0%} outside {item.lower:.0%}-{item.upper:.0%}" for item in breaches
    )


def default_principal() -> Principal:
    return Principal(
        actor_id="analyst-1",
        role=Role.analyst,
        scopes=[
            "search_policy",
            "get_holdings",
            "get_manager_report",
            "draft_briefing",
            "submit_committee_paper",
        ],
    )
