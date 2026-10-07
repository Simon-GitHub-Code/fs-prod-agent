"""A Strands file session still has the prior turn after the first agent is gone."""

import json

from fs_prod_agent.adapters.local.agent_strands import open_agent
from fs_prod_agent.adapters.local.fakes import FixtureDecision, InMemoryReview, LocalGateway, default_principal
from tests.fitness.support import REPO

_KEYS = (
    "ANTHROPIC_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_BEARER_TOKEN_BEDROCK",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "OPENAI_API_KEY",
    "XAI_API_KEY",
)


def test_a_new_agent_loads_the_prior_turn(tmp_path, monkeypatch):
    for name in _KEYS:
        monkeypatch.delenv(name, raising=False)
    request = json.loads((REPO / "evals" / "tasks" / "oversight_analyst.json").read_text(encoding="utf-8"))["request"]
    principal = default_principal()
    gateway = LocalGateway()
    agent = open_agent("restart-session", tmp_path, gateway, FixtureDecision(), InMemoryReview(), principal)
    outcome = str(agent(request)).strip()
    assert gateway.calls
    assert outcome.split("tools:", 1)[1]
    del agent
    restored = open_agent(
        "restart-session",
        tmp_path,
        LocalGateway(),
        FixtureDecision(),
        InMemoryReview(),
        principal,
    )
    assert request in _text(restored.messages)


def _text(messages: list) -> str:
    chunks: list[str] = []
    for message in messages:
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            chunks.append(content)
            continue
        if not isinstance(content, list):
            chunks.append(str(message))
            continue
        for block in content:
            if isinstance(block, dict) and "text" in block:
                chunks.append(str(block["text"]))
    return "\n".join(chunks)
