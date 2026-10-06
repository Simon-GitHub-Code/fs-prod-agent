"""context → decide → authorize → execute → observe. Evaluate stays outside this loop."""

from dataclasses import dataclass

from fs_prod_agent.application.registry import workflow_by_id
from fs_prod_agent.application.state import AgentState, build_agent_state
from fs_prod_agent.decisions.contract import DecisionResult, validate_decision
from fs_prod_agent.decisions.v1 import CONTRACT_VERSION, questions_for
from fs_prod_agent.domain.models import Action, Principal
from fs_prod_agent.observe.decision_chain import TraceRecord
from fs_prod_agent.policy.authorize import Verdict, admit, authorize, overrode
from fs_prod_agent.ports.protocols import (
    AgentRunner,
    DecisionPort,
    GatewayPort,
    HumanReviewPort,
    MemoryPort,
    RetrieverPort,
    TracePort,
    WorkflowRunner,
)


@dataclass
class Services:
    decision: DecisionPort
    memory: MemoryPort
    gateway: GatewayPort
    retriever: RetrieverPort
    trace: TracePort
    human_review: HumanReviewPort
    workflow: WorkflowRunner
    agent: AgentRunner


class Pipeline:
    def __init__(self, services: Services) -> None:
        self.services = services

    def run(self, request: str, principal: Principal, session_id: str) -> TraceRecord:
        self.services.memory.append_turn(principal.actor_id, session_id, request)
        evidence = self.services.retriever.retrieve(request)
        state = build_agent_state(request, evidence, None, principal)
        decision = self._decide(state, "ingress", questions_for("ingress"))
        verdict = admit(decision)
        route, workflow_id = _route_fields(decision)
        answers = list(decision.answers.values())
        outcome = _stopped_outcome(verdict, route)
        if verdict is Verdict.approve and route == "workflow":
            outcome = self._run_workflow(workflow_id, request, evidence, principal, answers)
        elif verdict is Verdict.approve and route == "agent":
            outcome = self.services.agent.run(state)
        elif verdict is Verdict.review:
            self.services.human_review.enqueue(session_id, principal.actor_id, "ingress")
            outcome = "pending_review"
        return self._emit(
            request=request,
            route=route,
            workflow_id=workflow_id if verdict is Verdict.approve else None,
            evidence_ids=evidence,
            decision=decision,
            answers=answers,
            verdict=verdict,
            tool_name=None,
            outcome=outcome,
            session_id=session_id,
            actor_id=principal.actor_id,
            confidence_key="route",
        )

    def dispatch_tool(
        self,
        request: str,
        principal: Principal,
        action: Action,
        session_id: str,
    ) -> TraceRecord:
        evidence = self.services.retriever.retrieve(request)
        state = build_agent_state(request, evidence, action, principal)
        decision = self._decide(state, "tool_gate", questions_for("tool_gate"))
        verdict = authorize(principal, action, decision)
        tool_name: str | None = None
        if verdict is Verdict.approve:
            tool_name = action.tool_name
            outcome = self.services.gateway.call(action.tool_name, dict(action.arguments))
        elif verdict is Verdict.review:
            self.services.human_review.enqueue(session_id, principal.actor_id, action.tool_name)
            outcome = "pending_review"
        elif verdict is Verdict.reject:
            outcome = "rejected"
        elif verdict is Verdict.failed:
            outcome = "failed"
        else:
            outcome = "uncertain"
        return self._emit(
            request=request,
            route=None,
            workflow_id=None,
            evidence_ids=evidence,
            decision=decision,
            answers=list(decision.answers.values()),
            verdict=verdict,
            tool_name=tool_name,
            outcome=outcome,
            session_id=session_id,
            actor_id=principal.actor_id,
            confidence_key="tool_gate",
        )

    def _decide(self, state: AgentState, contract: str, questions: list) -> DecisionResult:
        raw = self.services.decision.evaluate(state, contract)
        return validate_decision(raw, questions)

    def _emit(
        self,
        request: str,
        route: str | None,
        workflow_id: str | None,
        evidence_ids: list[str],
        decision: DecisionResult,
        answers: list,
        verdict: Verdict,
        tool_name: str | None,
        outcome: str,
        session_id: str,
        actor_id: str,
        confidence_key: str,
    ) -> TraceRecord:
        confidence_answer = decision.answers.get(confidence_key)
        trace = TraceRecord(
            user_request=request,
            route=route,
            workflow_id=workflow_id,
            evidence_ids=evidence_ids,
            decision_contract_version=decision.contract_version or CONTRACT_VERSION,
            answers=answers,
            policy_verdict=verdict.value,
            tool_name=tool_name,
            outcome=outcome,
            session_id=session_id,
            actor_id=actor_id,
            policy_overrode_decider=overrode(decision, verdict),
            confidence=None if confidence_answer is None else confidence_answer.confidence,
        )
        self.services.trace.record(trace)
        return trace

    def _run_workflow(
        self,
        workflow_id: str | None,
        request: str,
        evidence: list[str],
        principal: Principal,
        answers: list,
    ) -> str:
        if workflow_id is None:
            raise ValueError("workflow route missing workflow_id")
        spec = workflow_by_id(workflow_id)
        state = build_agent_state(request, evidence, None, principal)
        outcome = self.services.workflow.run(workflow_id, state)
        if spec.follow_up is None:
            return outcome
        follow_state = build_agent_state(request, evidence, None, principal, outcome)
        follow = self._decide(follow_state, spec.follow_up, questions_for(spec.follow_up))
        answers.extend(follow.answers.values())
        return outcome


def _route_fields(decision: DecisionResult) -> tuple[str | None, str | None]:
    route_answer = decision.answers.get("route")
    workflow_answer = decision.answers.get("workflow_id")
    route = None if route_answer is None else route_answer.choice
    workflow_id = None if workflow_answer is None else workflow_answer.choice
    if route != "workflow":
        workflow_id = None
    return route, workflow_id


def _stopped_outcome(verdict: Verdict, route: str | None) -> str:
    if verdict is Verdict.failed:
        return "failed"
    if verdict is Verdict.uncertain:
        return "uncertain"
    if verdict is Verdict.reject and route == "refuse":
        return "refused"
    if verdict is Verdict.reject:
        return "rejected"
    if verdict is Verdict.review:
        return "pending_review"
    return "pending"
