"""The only module that wires adapters. local is the default. aws is the unused switch.

build("local") is offline: a scripted agent model and the fixture decider. build("local", live_model=...)
names an Ollama Cloud model for the agent, reads OLLAMA_API_KEY, and requires the served decider.
live_decider=False keeps the fixture decisions under a live agent model, for a machine that cannot
serve the decider. Tools are served over MCP: in-process by default, or by the Streamable HTTP server
at tool_server, which is where an AgentCore Gateway URL would go.
"""

import os
from dataclasses import dataclass

from fs_prod_agent.application.pipeline import Pipeline, Services
from fs_prod_agent.domain.models import Action, Effect
from fs_prod_agent.observe.decision_chain import TraceRecord
from fs_prod_agent.ports.protocols import HumanReviewPort, IdentityPort, MemoryPort, TracePort


@dataclass
class App:
    profile: str
    pipeline: Pipeline
    memory: MemoryPort
    human_review: HumanReviewPort
    trace: TracePort
    identity: IdentityPort

    def invoke(self, payload: dict[str, str], session_id: str) -> TraceRecord:
        actor_id = payload["actor_id"]
        principal = self.identity.principal(actor_id)
        request = payload["request"]
        if "tool_name" in payload:
            action = Action(tool_name=payload["tool_name"], effect=Effect(payload["effect"]))
            return self.pipeline.dispatch_tool(request, principal, action, session_id)
        return self.pipeline.run(request, principal, session_id)


class LiveModelUnavailable(RuntimeError):
    """A live model was named and OLLAMA_API_KEY is not set."""


def build(
    profile: str = "local",
    live_model: str | None = None,
    live_decider: bool = True,
    tool_server: str | None = None,
) -> App:
    if profile == "aws":
        from fs_prod_agent.adapters.aws.profile import build_aws

        return build_aws()
    if profile != "local":
        raise ValueError(f"unknown profile: {profile}")
    return _build_local(live_model, live_decider, tool_server)


def serve_desk(host: str = "127.0.0.1", port: int = 8766, live_model: str | None = None) -> None:
    from fs_prod_agent.adapters.local.desk import serve

    serve(lambda: build("local", live_model), host, port)


def _build_local(live_model: str | None, live_decider: bool, tool_server: str | None) -> App:
    from fs_prod_agent.adapters.local.agent_strands import OllamaCloud, StrandsAgentRunner
    from fs_prod_agent.adapters.local.decision_decider import LIVE_TIMEOUT_SECONDS, DeciderClient
    from fs_prod_agent.adapters.local.fakes import (
        InMemoryIdentity,
        InMemoryMemory,
        InMemoryReview,
        JsonlTrace,
        StaticRetriever,
        default_principal,
    )
    from fs_prod_agent.adapters.local.gateway_mcp import McpGateway
    from fs_prod_agent.adapters.local.mcp_tools import build_server
    from fs_prod_agent.adapters.local.workflow_langgraph import LangGraphWorkflow

    principal = default_principal()
    memory = InMemoryMemory()
    review = InMemoryReview()
    trace = JsonlTrace()
    identity = InMemoryIdentity({principal.actor_id: principal})
    gateway = McpGateway(tool_server or build_server())
    model = None
    decision = DeciderClient()
    if live_model is not None:
        model = OllamaCloud(model_id=live_model, api_key=_ollama_key())
    if live_model is not None and live_decider:
        decision = DeciderClient(timeout=LIVE_TIMEOUT_SECONDS, fixture_when_offline=False)
    pipeline = Pipeline(
        Services(
            decision=decision,
            memory=memory,
            gateway=gateway,
            retriever=StaticRetriever(),
            trace=trace,
            human_review=review,
            workflow=LangGraphWorkflow(),
            agent=StrandsAgentRunner(gateway, decision, review, model=model),
        )
    )
    return App(
        profile="local",
        pipeline=pipeline,
        memory=memory,
        human_review=review,
        trace=trace,
        identity=identity,
    )


def _ollama_key() -> str:
    key = os.environ.get("OLLAMA_API_KEY", "")
    if not key:
        raise LiveModelUnavailable("a live model was named and OLLAMA_API_KEY is not set")
    return key
