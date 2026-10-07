"""The local desk is one build("local") sitting, served from this repo."""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fs_prod_agent.adapters.local.books import IPS, QUARTERLY_SNAPSHOT
from fs_prod_agent.adapters.local.decision_decider import CHECKPOINT_ID, SERVE_HOST, DeciderClient, serve_command
from fs_prod_agent.adapters.local.desk import run_sitting
from fs_prod_agent.adapters.local.fakes import FixtureDecision, _render_breaches, default_principal
from fs_prod_agent.application.state import AgentState
from fs_prod_agent.composition import build
from fs_prod_agent.domain.oversight import performance_briefing, range_breaches
from tests.fitness.support import REPO

_DISTINCT_CHOICE = "confirm"


def test_fresh_process_uses_the_three_adapters_and_the_domain():
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(REPO / "src"), str(REPO), env.get("PYTHONPATH", "")])
    completed = subprocess.run(
        [sys.executable, "-c", _FRESH_PROCESS],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_stub_systemone_choice_is_the_committee_row():
    posts: list[dict] = []
    server = _stub_server(posts)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        app = build("local")
        app.pipeline.services.decision = DeciderClient(base_url=f"http://{host}:{port}")
        sitting = run_sitting(app)
    finally:
        server.shutdown()
        thread.join(timeout=5)
    committee = [post for post in posts if "submit_committee_paper" in post["body"]["state"]]
    assert committee
    assert committee[0]["path"] == "/v1/systemone"
    assert sitting.committee_choice == _DISTINCT_CHOICE
    assert sitting.committee_verdict == "review"
    assert sitting.committee_outcome == "pending_review"
    assert sitting.pending_tools == ("submit_committee_paper",)
    committee_page = dict(sitting.pages)["committee_paper"]
    assert f"Decider choice: {_DISTINCT_CHOICE}." in committee_page
    assert "Policy verdict: review." in committee_page
    assert isinstance(CHECKPOINT_ID, str)
    assert "hobson" in CHECKPOINT_ID
    assert SERVE_HOST == "127.0.0.1"
    command = serve_command()
    assert command[0:3] == ("strands-decider", "serve", CHECKPOINT_ID)
    assert command.count(CHECKPOINT_ID) == 1
    assert SERVE_HOST in command
    proof = os.environ.get("DESK_SYSTEMONE")
    if proof:
        payload = {
            "posted": committee[0]["body"],
            "response": committee[0]["response"],
            "path": committee[0]["path"],
            "choice": sitting.committee_choice,
            "verdict": sitting.committee_verdict,
        }
        with open(proof, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)


def test_http_entry_serves_the_same_sitting_twice():
    expected = run_sitting(build("local"))
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(REPO / "src"), str(REPO), env.get("PYTHONPATH", "")])
    process = subprocess.Popen(
        [sys.executable, "-m", "fs_prod_agent.desk", "--host", "127.0.0.1", "--port", "0"],
        cwd=REPO,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert process.stdout is not None
    try:
        line = process.stdout.readline().strip()
        _host, port = line.split()[1:]
        first = _fetch(port, "/")
        second = _fetch(port, "/")
        pages = {case_id: _fetch(port, f"/case/{case_id}") for case_id, _html in expected.pages}
        quarterly = json.loads((REPO / "evals" / "tasks" / "performance_pack.json").read_text(encoding="utf-8"))
        asked = _post(port, quarterly["request"])
        blank = _post(port, "   ")
        open_question = _post(port, "What should I read before the committee?")
        too_long = _post(port, "x" * 2001)
        try:
            _fetch(port, "/case/not-a-case")
            missing = ""
        except HTTPError as exc:
            missing = exc.read().decode()
            assert exc.code == 404
        css = _fetch(port, "/static/desk.css")
    finally:
        process.terminate()
        process.wait(timeout=10)
    assert first == second
    assert "Ask the desk" in first
    assert "Nothing has run yet." in first
    assert expected.briefing not in first
    for case_id, html in expected.pages:
        assert pages[case_id] == html
    assert expected.briefing in asked
    assert "What each stage did" in asked
    assert "Write a question first." in blank
    assert "What should I read before the committee?" in open_question
    assert "scripted stand-in" in open_question
    assert "Write a shorter question." in too_long
    assert "Return to the desk." in missing
    assert "Source Serif 4" in css
    page_dir = os.environ.get("DESK_PAGES")
    if page_dir:
        root = Path(page_dir)
        root.mkdir(parents=True, exist_ok=True)
        (root / "page-1.html").write_text(first, encoding="utf-8")
        (root / "page-2.html").write_text(second, encoding="utf-8")


def assert_local_desk(app) -> None:
    workflow = type(app.pipeline.services.workflow).__module__
    agent = type(app.pipeline.services.agent).__module__
    decision = type(app.pipeline.services.decision).__module__
    assert workflow.endswith("workflow_langgraph")
    assert agent.endswith("agent_strands")
    assert decision.endswith("decision_decider")
    sitting = run_sitting(app)
    briefing = performance_briefing(QUARTERLY_SNAPSHOT).body
    breach = _render_breaches(range_breaches(QUARTERLY_SNAPSHOT.holdings, IPS.ranges))
    assert sitting.briefing == briefing
    assert sitting.breach == breach
    assert sitting.analyst_tools
    listed = tuple(part.strip() for part in sitting.analyst.split("tools:", 1)[1].split(",") if part.strip())
    assert listed == sitting.analyst_tools
    assert list(app.pipeline.services.gateway.calls) == list(sitting.analyst_tools)
    assert sitting.order == "refused"
    assert sitting.order_calls == ()
    assert sitting.committee_verdict == "review"
    assert sitting.committee_outcome == "pending_review"
    assert sitting.pending_tools == ("submit_committee_paper",)
    pages = dict(sitting.pages)
    assert tuple(pages) == (
        "performance_pack",
        "mandate_check",
        "oversight_analyst",
        "refuse_order",
        "committee_paper",
    )
    assert briefing in pages["performance_pack"]
    assert "materiality follow-up" not in pages["performance_pack"]
    assert breach in pages["mandate_check"]
    assert "materiality follow-up" in pages["mandate_check"]
    for name in sitting.analyst_tools:
        assert name in pages["oversight_analyst"]
    assert "scripted stand-in" in pages["oversight_analyst"]
    assert sitting.order in pages["refuse_order"]
    assert "Did not run." in pages["refuse_order"]
    assert 'class="stage-name idle"' in pages["refuse_order"]
    assert 'class="stage-name idle"' not in pages["performance_pack"]
    assert f"Decider choice: {sitting.committee_choice}." in pages["committee_paper"]
    assert "Policy verdict: review." in pages["committee_paper"]
    assert "submit_committee_paper is pending in the human queue." in pages["committee_paper"]
    assert "Ask the desk" in sitting.html
    assert "Nothing has run yet." in sitting.html
    assert briefing not in sitting.html


def _fetch(port: str, path: str) -> str:
    with urlopen(f"http://127.0.0.1:{port}{path}", timeout=60) as response:
        return response.read().decode()


def _post(port: str, question: str) -> str:
    payload = urlencode({"question": question}).encode()
    request = Request(f"http://127.0.0.1:{port}/ask", data=payload)
    with urlopen(request, timeout=60) as response:
        return response.read().decode()


def _stub_server(posts: list[dict]) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode())
            response = _systemone(body)
            posts.append({"path": self.path, "body": body, "response": response})
            payload = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)


def _systemone(body: dict) -> dict:
    questions = body["questions"]
    if "tool_gate" in questions:
        contract = "tool_gate"
    elif "route" in questions:
        contract = "ingress"
    else:
        contract = "materiality"
    request = str(body["state"]).split("\n", 1)[0]
    result = FixtureDecision().evaluate(AgentState(request=request, principal=default_principal()), contract)
    answers = {question_id: _wire(question_id, answer) for question_id, answer in result.answers.items()}
    return {"answers": answers}


def _wire(question_id: str, answer) -> dict:
    if answer.type == "choice":
        choice = _DISTINCT_CHOICE if question_id == "tool_gate" else answer.choice
        probabilities = {key: (0.97 if key == choice else 0.01) for key in answer.probabilities}
        return {"type": "choice", "choice": choice, "confidence": answer.confidence, "probabilities": probabilities}
    if answer.type == "score":
        return {
            "type": "score",
            "score": answer.score,
            "confidence": answer.confidence,
            "probabilities": dict(answer.probabilities),
        }
    return {"type": "noul", "noul": answer.noul}


_FRESH_PROCESS = """
from fs_prod_agent.composition import build
from tests.integration.test_desk import assert_local_desk

assert_local_desk(build("local"))
"""
