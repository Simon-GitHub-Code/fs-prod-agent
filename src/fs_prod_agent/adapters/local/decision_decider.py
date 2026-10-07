"""Strands Decider client. One hobson checkpoint, served on localhost.

By default the fixture answers when nothing is listening. A live run turns that off: an offline
decider or a malformed answer becomes an unavailable decision, and policy fails closed.
"""

import json
import urllib.error
import urllib.request
from typing import Any

import strands_decider

from fs_prod_agent.adapters.local.fakes import FixtureDecision
from fs_prod_agent.application.state import AgentState
from fs_prod_agent.decisions.contract import Answer, DecisionResult, unavailable
from fs_prod_agent.decisions.v1 import questions_for

# The reference checkpoint published with strands-decider. Serve binds to localhost.
CHECKPOINT_ID = "StrandsAgents/strands-decider-2B-hobson-v19"
SERVE_HOST = "127.0.0.1"
SERVE_PORT = 8000
_TIMEOUT_SECONDS = 0.4
# A CPU-served 2B checkpoint answers in seconds, not milliseconds.
LIVE_TIMEOUT_SECONDS = 60.0


class DeciderOffline(Exception):
    """Nothing accepted POST /v1/systemone."""


class DeciderClient:
    """Posts v1 questions to the decider. A live answer replaces the fixture choice."""

    def __init__(
        self,
        base_url: str | None = None,
        fallback: FixtureDecision | None = None,
        timeout: float = _TIMEOUT_SECONDS,
        fixture_when_offline: bool = True,
    ) -> None:
        self.base_url = base_url or f"http://{SERVE_HOST}:{SERVE_PORT}"
        self.fallback = fallback or FixtureDecision()
        self.timeout = timeout
        self.fixture_when_offline = fixture_when_offline

    def evaluate(self, state: AgentState, contract: str) -> DecisionResult:
        try:
            payload = _read_json(_request(self.base_url, _body(state, contract)), self.timeout)
        except DeciderOffline as offline:
            if self.fixture_when_offline:
                return self.fallback.evaluate(state, contract)
            return unavailable("v1", f"decider offline: {offline}")
        try:
            return _result_from(payload)
        except (KeyError, TypeError, ValueError) as malformed:
            return unavailable("v1", f"decider answer malformed: {malformed!r}")


def serve_command() -> tuple[str, ...]:
    """The one local serve invocation. The host is 127.0.0.1 and the checkpoint is hobson."""
    return (
        "strands-decider",
        "serve",
        CHECKPOINT_ID,
        "--host",
        SERVE_HOST,
        "--port",
        str(SERVE_PORT),
    )


def _request(base_url: str, body: dict[str, Any]) -> urllib.request.Request:
    return urllib.request.Request(
        base_url.rstrip("/") + "/v1/systemone",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )


def _read_json(request: urllib.request.Request, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise DeciderOffline(str(exc)) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise DeciderOffline(str(exc)) from exc


def _body(state: AgentState, contract: str) -> dict[str, Any]:
    return {
        "state": _state_text(state),
        "model": CHECKPOINT_ID,
        "questions": {question.id: _question_body(question) for question in questions_for(contract)},
    }


def _question_body(question: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"type": question.type, "instructions": question.instructions}
    if question.criteria is not None:
        body["criteria"] = question.criteria
    return body


def _state_text(state: AgentState) -> str:
    lines = [state.request, *state.evidence_ids]
    if state.workflow_result:
        lines.append(state.workflow_result)
    action = state.proposed_action
    if action is not None:
        lines.append(action.tool_name)
        lines.append(action.effect.value)
    return "\n".join(lines)


def _result_from(payload: dict[str, Any]) -> DecisionResult:
    answers = {question_id: _answer_from(question_id, raw) for question_id, raw in payload["answers"].items()}
    return DecisionResult(contract_version="v1", available=True, answers=answers)


def _answer_from(question_id: str, raw: dict[str, Any]) -> Answer:
    kind = raw["type"]
    if kind == "choice":
        return _choice_answer(question_id, raw)
    if kind == "score":
        return _score_answer(question_id, raw)
    return _noul_answer(question_id, raw)


def _choice_answer(question_id: str, raw: dict[str, Any]) -> Answer:
    return Answer(
        question_id=question_id,
        type="choice",
        choice=raw["choice"],
        confidence=raw.get("confidence"),
        probabilities=dict(raw.get("probabilities") or {}),
    )


def _score_answer(question_id: str, raw: dict[str, Any]) -> Answer:
    return Answer(
        question_id=question_id,
        type="score",
        score=raw["score"],
        confidence=raw.get("confidence"),
        probabilities={str(key): value for key, value in (raw.get("probabilities") or {}).items()},
    )


def _noul_answer(question_id: str, raw: dict[str, Any]) -> Answer:
    noul = float(raw["noul"])
    return Answer(
        question_id=question_id,
        type="noul",
        noul=noul,
        confidence=noul,
        probabilities={"yes": noul, "no": 1.0 - noul},
    )


# Keep the package import live so this file is the only strands_decider site.
_DECIDER_VERSION = strands_decider.__version__
