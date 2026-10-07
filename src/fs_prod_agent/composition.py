"""The only module that wires adapters. local is the default. aws is the unused switch."""

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


def build(profile: str = "local") -> App:
    if profile == "aws":
        from fs_prod_agent.adapters.aws.profile import build_aws

        return build_aws()
    if profile != "local":
        raise ValueError(f"unknown profile: {profile}")
    return _build_local()


def serve_desk(host: str = "127.0.0.1", port: int = 8766) -> None:
    from fs_prod_agent.adapters.local.desk import serve

    serve(build, host, port)


def _build_local() -> App:
    from fs_prod_agent.adapters.local.agent_strands import StrandsAgentRunner
    from fs_prod_agent.adapters.local.decision_decider import DeciderClient
    from fs_prod_agent.adapters.local.fakes import (
        InMemoryIdentity,
        InMemoryMemory,
        InMemoryReview,
        JsonlTrace,
        LocalGateway,
        StaticRetriever,
        default_principal,
    )
    from fs_prod_agent.adapters.local.workflow_langgraph import LangGraphWorkflow

    principal = default_principal()
    memory = InMemoryMemory()
    review = InMemoryReview()
    trace = JsonlTrace()
    identity = InMemoryIdentity({principal.actor_id: principal})
    gateway = LocalGateway()
    decision = DeciderClient()
    pipeline = Pipeline(
        Services(
            decision=decision,
            memory=memory,
            gateway=gateway,
            retriever=StaticRetriever(),
            trace=trace,
            human_review=review,
            workflow=LangGraphWorkflow(),
            agent=StrandsAgentRunner(gateway, decision, review),
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
