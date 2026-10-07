"""The local oversight page. One request is one fresh build("local"). The page renders that run."""

from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from fs_prod_agent.adapters.local.desk_audit import audit_stages
from fs_prod_agent.adapters.local.desk_page import render_home, render_missing, render_run
from fs_prod_agent.evals.loader import EvalCase, load_cases
from fs_prod_agent.observe.decision_chain import TraceRecord

_HTML = "text/html; charset=utf-8"
_BODY_CAP = 8192
_QUESTION_CAP = 2000
_STATIC = {
    "desk.css": "text/css; charset=utf-8",
    "source-serif-4-400.woff2": "font/woff2",
    "source-serif-4-600.woff2": "font/woff2",
    "source-serif-4-400-italic.woff2": "font/woff2",
}


@dataclass(frozen=True)
class _Case:
    case_id: str
    folder: str


_CASES = (
    _Case("performance_pack", "tasks"),
    _Case("mandate_check", "tasks"),
    _Case("oversight_analyst", "tasks"),
    _Case("refuse_order", "decision_contracts/v1"),
    _Case("committee_paper", "decision_contracts/v1"),
)
_CASE_INDEX = {case.case_id: case for case in _CASES}


@dataclass(frozen=True)
class Sitting:
    briefing: str
    breach: str
    analyst: str
    analyst_tools: tuple[str, ...]
    order: str
    order_calls: tuple[str, ...]
    committee_verdict: str
    committee_choice: str
    committee_outcome: str
    pending_tools: tuple[str, ...]
    html: str
    pages: tuple[tuple[str, str], ...]


def run_sitting(app: object) -> Sitting:
    session = "desk"
    pack, pack_page = _take(app, "performance_pack", session)
    mandate, mandate_page = _take(app, "mandate_check", session)
    analyst_at = len(_calls(app))
    analyst, analyst_page = _take(app, "oversight_analyst", session)
    analyst_tools = tuple(_calls(app)[analyst_at:])
    order_at = len(_calls(app))
    order, order_page = _take(app, "refuse_order", session)
    order_calls = tuple(_calls(app)[order_at:])
    committee, committee_page = _take(app, "committee_paper", session)
    pending = tuple(item.tool_name for item in app.human_review.pending(session))
    pages = (
        ("performance_pack", pack_page),
        ("mandate_check", mandate_page),
        ("oversight_analyst", analyst_page),
        ("refuse_order", order_page),
        ("committee_paper", committee_page),
    )
    return Sitting(
        briefing=pack.outcome,
        breach=mandate.outcome,
        analyst=analyst.outcome,
        analyst_tools=analyst_tools,
        order=order.outcome,
        order_calls=order_calls,
        committee_verdict=committee.policy_verdict,
        committee_choice=_choice(committee, "tool_gate"),
        committee_outcome=committee.outcome,
        pending_tools=pending,
        html=render_home(_case_links()),
        pages=pages,
    )


def render_sitting(app: object) -> str:
    return run_sitting(app).html


def serve(factory: Callable[[], Any], host: str, port: int) -> None:
    """Serve one fresh local app per request. factory is build."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self._respond(_get(self.path, factory))

        def do_POST(self) -> None:  # noqa: N802
            length = _content_length(self.headers.get("Content-Length"))
            raw = self.rfile.read(min(length, _BODY_CAP + 1))
            if length > _BODY_CAP or len(raw) > _BODY_CAP:
                self._respond(_page(400, render_home(_case_links(), "That question is too long.")))
                return
            self._respond(_post(self.path, raw, factory))

        def _respond(self, result: tuple[int, str, bytes]) -> None:
            status, content_type, body = result
            self.send_response(status)
            if status == 204:
                self.end_headers()
                return
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    server = HTTPServer((host, port), Handler)
    print(f"listening {host} {server.server_port}", flush=True)
    server.serve_forever()


def _get(path: str, factory: Callable[[], Any]) -> tuple[int, str, bytes]:
    clean = path.split("?", 1)[0]
    if clean == "/favicon.ico":
        return 204, "text/plain", b""
    if clean == "/":
        return _page(200, render_home(_case_links()))
    if clean.startswith("/case/"):
        return _case_response(clean.removeprefix("/case/"), factory)
    if clean.startswith("/static/"):
        return _static(clean.removeprefix("/static/"))
    return _page(404, render_missing())


def _post(path: str, raw: bytes, factory: Callable[[], Any]) -> tuple[int, str, bytes]:
    if path.split("?", 1)[0] != "/ask":
        return _page(404, render_missing())
    question = _question(raw)
    if question is None:
        return _page(200, render_home(_case_links(), "Write a question first."))
    if len(question) > _QUESTION_CAP:
        return _page(200, render_home(_case_links(), "Write a shorter question."))
    return _page(200, _ask_page(question, factory))


def _case_response(case_id: str, factory: Callable[[], Any]) -> tuple[int, str, bytes]:
    if case_id not in _CASE_INDEX:
        return _page(404, render_missing())
    return _page(200, _one_page(factory(), case_id, "desk"))


def _ask_page(question: str, factory: Callable[[], Any]) -> str:
    app = factory()
    trace = app.invoke({"actor_id": "analyst-1", "request": question}, "ask")
    calls = tuple(_calls(app))
    pending = tuple(item.tool_name for item in app.human_review.pending("ask"))
    stages = audit_stages(trace, calls, pending, None)
    return render_run(trace.user_request, _plate(trace, pending), stages, _case_links())


def _one_page(app: object, case_id: str, session: str) -> str:
    _trace, page = _take(app, case_id, session)
    return page


def _take(app: object, case_id: str, session: str) -> tuple[TraceRecord, str]:
    spec = _CASE_INDEX[case_id]
    case = _case(spec.folder, spec.case_id)
    before = len(_calls(app))
    trace = _invoke_case(app, case, session)
    calls = tuple(_calls(app)[before:])
    pending = tuple(item.tool_name for item in app.human_review.pending(session))
    stages = audit_stages(trace, calls, pending, _effect_name(case))
    page = render_run(trace.user_request, _plate(trace, pending), stages, _case_links())
    return trace, page


def _plate(trace: TraceRecord, pending: tuple[str, ...]) -> str:
    if trace.outcome == "pending_review" and pending:
        return _committee_line(pending, _choice(trace, "tool_gate"), trace.policy_verdict)
    if trace.outcome == "refused":
        return "The request was refused at ingress. No tool was called."
    return trace.outcome


def _page(status: int, text: str) -> tuple[int, str, bytes]:
    return status, _HTML, text.encode()


def _question(raw: bytes) -> str | None:
    parsed = parse_qs(raw.decode("utf-8", "replace"), keep_blank_values=True)
    values = parsed.get("question", [])
    text = values[0].strip() if values else ""
    if not text:
        return None
    return text


def _content_length(value: str | None) -> int:
    if not value:
        return 0
    try:
        parsed = int(value)
    except ValueError:
        return 0
    if parsed < 0:
        return 0
    return parsed


def _static(name: str) -> tuple[int, str, bytes]:
    mime = _STATIC.get(name)
    if mime is None:
        return _page(404, render_missing())
    path = Path(__file__).resolve().parent / "desk_static" / name
    return 200, mime, path.read_bytes()


def _case_links() -> tuple[tuple[str, str], ...]:
    return tuple((case.case_id, _case(case.folder, case.case_id).request) for case in _CASES)


def _invoke_case(app: object, case: EvalCase, session: str) -> TraceRecord:
    payload = {"actor_id": case.principal.actor_id, "request": case.request}
    if case.tool_name is not None and case.effect is not None:
        payload["tool_name"] = case.tool_name
        payload["effect"] = case.effect.value
    return app.invoke(payload, session)


def _effect_name(case: EvalCase) -> str | None:
    if case.effect is None:
        return None
    return case.effect.value


def _case(folder: str, name: str) -> EvalCase:
    cases = load_cases(_repo() / "evals" / folder)
    for case in cases:
        if case.id == name:
            return case
    raise KeyError(name)


def _repo() -> Path:
    return Path(__file__).resolve().parents[4]


def _calls(app: object) -> list[str]:
    return list(app.pipeline.services.gateway.calls)


def _choice(trace: TraceRecord, question_id: str) -> str:
    for answer in trace.answers:
        if answer.question_id == question_id and answer.choice:
            return answer.choice
    return ""


def _committee_line(pending: tuple[str, ...], choice: str, verdict: str) -> str:
    tool = pending[0] if pending else "submit_committee_paper"
    return f"{tool} is pending in the human queue. Decider choice: {choice}. Policy verdict: {verdict}."
