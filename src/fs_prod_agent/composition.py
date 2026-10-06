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


def _build_local() -> App:
    from fs_prod_agent.adapters.local.fakes import (
        FixtureAgentRunner,
        FixtureDecision,
        FixtureWorkflowRunner,
        InMemoryIdentity,
        InMemoryMemory,
        InMemoryReview,
        JsonlTrace,
        LocalGateway,
        StaticRetriever,
        default_principal,
    )

    principal = default_principal()
    memory = InMemoryMemory()
    review = InMemoryReview()
    trace = JsonlTrace()
    identity = InMemoryIdentity({principal.actor_id: principal})
    pipeline = Pipeline(
        Services(
            decision=FixtureDecision(),
            memory=memory,
            gateway=LocalGateway(),
            retriever=StaticRetriever(),
            trace=trace,
            human_review=review,
            workflow=FixtureWorkflowRunner(),
            agent=FixtureAgentRunner(),
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
