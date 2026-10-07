"""Strands agent for the open manager question. Tools go through the gateway.

The scripted model needs no API key and is the default. OllamaCloud names a hosted model instead.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fs_prod_agent.application.state import AgentState, build_agent_state
from fs_prod_agent.decisions.contract import validate_decision
from fs_prod_agent.decisions.v1 import questions_for
from fs_prod_agent.domain.models import Action, Effect, Principal
from fs_prod_agent.mcp_servers.catalog import manifest_for
from fs_prod_agent.policy.authorize import Verdict, authorize
from fs_prod_agent.ports.protocols import DecisionPort, GatewayPort, HumanReviewPort

_READ_TOOLS = ("get_manager_report", "search_policy")
_PIPELINE_SESSION = "oversight"
OLLAMA_CLOUD_HOST = "https://ollama.com"
SYSTEM_PROMPT = (
    "You are the oversight analyst at a large asset owner. "
    "Answer the question from the tool results only, and name the tools you used. "
    "You draft and check. You do not place orders or send anything."
)


@dataclass(frozen=True)
class OllamaCloud:
    """A model served by Ollama Cloud. The key is read from the environment and never printed."""

    model_id: str
    api_key: str = field(repr=False)


class StrandsAgentRunner:
    """Open-question runner. Session turns live in the Strands file store."""

    def __init__(
        self,
        gateway: GatewayPort,
        decision: DecisionPort,
        review: HumanReviewPort,
        storage_dir: Path | None = None,
        model: OllamaCloud | None = None,
    ) -> None:
        self.gateway = gateway
        self.decision = decision
        self.review = review
        self.storage_dir = storage_dir or _private_dir()
        self.model = model

    def run(self, state: AgentState) -> str:
        agent = open_agent(
            _PIPELINE_SESSION,
            self.storage_dir,
            self.gateway,
            self.decision,
            self.review,
            state.principal,
            self.model,
        )
        try:
            return str(agent(state.request)).strip()
        except Exception as error:  # a model outage is an outcome, and the trace must still be written
            return f"failed: agent model error ({type(error).__name__}: {error})"


def open_agent(
    session_id: str,
    storage_dir: Path,
    gateway: GatewayPort,
    decision: DecisionPort,
    review: HumanReviewPort,
    principal: Principal,
    model: OllamaCloud | None = None,
) -> Any:
    """A Strands agent bound to one file-backed session. Import happens here, not at build()."""
    from strands import Agent
    from strands.session.file_session_manager import FileSessionManager
    from strands.tools.executors import SequentialToolExecutor

    store = FileSessionManager(session_id=session_id, storage_dir=str(storage_dir))
    return Agent(
        model=_model(model),
        tools=_gateway_tools(gateway),
        hooks=[_ToolGate(decision, review, principal, session_id)],
        session_manager=store,
        # One call at a time, so the audit lists tools in the order the agent asked for them.
        tool_executor=SequentialToolExecutor(),
        callback_handler=None,
        system_prompt=SYSTEM_PROMPT,
    )


def _private_dir() -> Path:
    import tempfile

    return Path(tempfile.mkdtemp(prefix="oversight-session-"))


def _model(choice: OllamaCloud | None) -> Any:
    if choice is None:
        return _scripted_model()
    from strands.models.ollama import OllamaModel

    return OllamaModel(
        host=OLLAMA_CLOUD_HOST,
        ollama_client_args={"headers": {"Authorization": f"Bearer {choice.api_key}"}},
        model_id=choice.model_id,
    )


def _scripted_model() -> Any:
    from strands.models.model import Model

    class Scripted(Model):
        """Calls the read tools once, then answers with the names that ran. No network."""

        def update_config(self, **model_config: Any) -> None:
            return None

        def get_config(self) -> dict[str, str]:
            return {"model_id": "scripted"}

        async def structured_output(
            self,
            output_model: type,
            prompt: Any,
            system_prompt: str | None = None,
            **kwargs: Any,
        ):
            if False:
                yield {}

        async def stream(self, messages: Any, tool_specs: Any = None, system_prompt: str | None = None, **kwargs: Any):
            names = _success_names(messages)
            events = _text_events(_answer(names, _asked(messages))) if names else _tool_events()
            for event in events:
                yield event

    return Scripted()


def _gateway_tools(gateway: GatewayPort) -> list[Any]:
    from strands import tool

    @tool
    def get_manager_report(query: str) -> str:
        """Read an external manager's latest commentary and watchlist flag."""
        return gateway.call("get_manager_report", {"query": query})

    @tool
    def search_policy(query: str) -> str:
        """Search investment policy and strategic asset allocation text."""
        return gateway.call("search_policy", {"query": query})

    return [get_manager_report, search_policy]


class _ToolGate:
    """before_tool_call: ask the decision port, then policy. A mutate call stays in the queue."""

    def __init__(
        self,
        decision: DecisionPort,
        review: HumanReviewPort,
        principal: Principal,
        session_id: str,
    ) -> None:
        self.decision = decision
        self.review = review
        self.principal = principal
        self.session_id = session_id

    def register_hooks(self, registry: Any) -> None:
        from strands.hooks import BeforeToolCallEvent

        registry.add_callback(BeforeToolCallEvent, self.gate)

    def gate(self, event: Any) -> None:
        _screen(event, self.decision, self.review, self.principal, self.session_id)


def _screen(
    event: Any,
    decision: DecisionPort,
    review: HumanReviewPort,
    principal: Principal,
    session_id: str,
) -> None:
    name = event.tool_use["name"]
    manifest = manifest_for(name)
    action = Action(tool_name=name, effect=Effect(manifest.effect), arguments=_string_args(event.tool_use.get("input")))
    raw = decision.evaluate(build_agent_state(name, [], action, principal), "tool_gate")
    verdict = authorize(principal, action, validate_decision(raw, questions_for("tool_gate")))
    if verdict is Verdict.approve:
        return
    event.cancel_tool = verdict.value
    if verdict is Verdict.review:
        review.enqueue(session_id, principal.actor_id, name)


def _string_args(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def _blocks(message: dict[str, Any]) -> list[dict[str, Any]]:
    content = message.get("content") or []
    return [block for block in content if isinstance(block, dict)]


def _tool_ids(messages: list[dict[str, Any]]) -> dict[str, str]:
    found: dict[str, str] = {}
    for message in messages:
        for block in _blocks(message):
            use = block.get("toolUse")
            if use:
                found[str(use["toolUseId"])] = str(use["name"])
    return found


def _success_names(messages: list[dict[str, Any]]) -> list[str]:
    if not messages:
        return []
    ids = _tool_ids(messages)
    names: list[str] = []
    for block in _blocks(messages[-1]):
        result = block.get("toolResult")
        if not result or result.get("status") != "success":
            continue
        name = ids.get(str(result.get("toolUseId")))
        if name:
            names.append(name)
    return names


def _asked(messages: Any) -> str:
    for message in _message_list(messages):
        if message.get("role") != "user":
            continue
        text = _user_text(message)
        if text:
            return text
    return ""


def _message_list(messages: Any) -> list[dict[str, Any]]:
    if not isinstance(messages, list | tuple):
        return []
    return [item for item in messages if isinstance(item, dict)]


def _user_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    found = ""
    for block in _blocks(message):
        text = block.get("text")
        if isinstance(text, str) and text.strip():
            found = text.strip()
    return found


def _answer(names: list[str], asked: str) -> str:
    heard = f'You asked: "{asked}". ' if asked else ""
    lead = "The scripted stand-in answered about Global Equity Manager B. Mandate text was retrieved. tools: "
    return heard + lead + ", ".join(names)


def _tool_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = [{"messageStart": {"role": "assistant"}}]
    for index, name in enumerate(_READ_TOOLS):
        events.extend(_one_tool(index, name))
    events.append({"messageStop": {"stopReason": "tool_use"}})
    return events


def _one_tool(index: int, name: str) -> list[dict[str, Any]]:
    tool_use = {"name": name, "toolUseId": f"t{index}"}
    return [
        {"contentBlockStart": {"start": {"toolUse": tool_use}}},
        {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps({"query": "Global Equity Manager B"})}}}},
        {"contentBlockStop": {}},
    ]


def _text_events(text: str) -> list[dict[str, Any]]:
    return [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"start": {}}},
        {"contentBlockDelta": {"delta": {"text": text}}},
        {"contentBlockStop": {}},
        {"messageStop": {"stopReason": "end_turn"}},
    ]
