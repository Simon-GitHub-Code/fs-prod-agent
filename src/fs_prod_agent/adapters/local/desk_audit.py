"""Stage audit for one pipeline trace. The text reports the trace. It does not recompute the book."""

from dataclasses import dataclass

from fs_prod_agent.decisions.contract import Answer
from fs_prod_agent.observe.decision_chain import TraceRecord

_STOPPED = frozenset({"refused", "pending_review", "rejected", "failed", "uncertain"})


@dataclass(frozen=True)
class Stage:
    name: str
    did: str
    ran: bool


def audit_stages(
    trace: TraceRecord,
    calls: tuple[str, ...],
    pending: tuple[str, ...],
    effect: str | None = None,
) -> tuple[Stage, ...]:
    return (
        _context(trace),
        _decide(trace),
        _authorize(trace, effect),
        _execute(trace, calls, pending),
        _observe(trace, pending),
    )


def primer_stages() -> tuple[Stage, ...]:
    """What each stage will do, before a question has run."""
    return (
        Stage("Context", "Reads the question, the actor, and the evidence the retriever returns.", True),
        Stage("Decide", "Asks the decider the contract questions for this request.", True),
        Stage(
            "Authorize",
            "Policy returns approve, review, reject, failed, or uncertain. A model signal does not grant permission.",
            True,
        ),
        Stage("Execute", "An approved workflow or agent runs. A refused request and a queued paper do not.", True),
        Stage("Observe", "Writes the trace: who asked, what was decided, what policy did, and what ran.", True),
    )


def _context(trace: TraceRecord) -> Stage:
    evidence = ", ".join(trace.evidence_ids) if trace.evidence_ids else "none"
    did = f"Actor {trace.actor_id} asked: {trace.user_request} Evidence retrieved: {evidence}."
    return Stage("Context", did, True)


def _decide(trace: TraceRecord) -> Stage:
    lines: list[str] = []
    follow = False
    for answer in trace.answers:
        lines.append(_answer_line(answer, follow))
        follow = _saw_materiality(follow, answer.question_id)
    text = "\n".join(lines)
    if not text:
        text = "No answers were recorded."
    return Stage("Decide", text, True)


def _saw_materiality(follow: bool, question_id: str) -> bool:
    if question_id == "materiality":
        return True
    return follow


def _answer_line(answer: Answer, follow: bool) -> str:
    label = _label(answer.question_id, follow)
    return f"{label}: {_value(answer)}. Confidence {_fmt(answer.confidence)}."


def _label(question_id: str, follow: bool) -> str:
    if follow and question_id == "materiality":
        return "materiality follow-up"
    return question_id


def _value(answer: Answer) -> str:
    if answer.type == "choice":
        return answer.choice or "none"
    if answer.type == "score":
        return _num(answer.score)
    return _num(answer.noul)


def _fmt(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"{value:.2f}"


def _num(value: float | None) -> str:
    if value is None:
        return "none"
    return f"{value:g}"


def _authorize(trace: TraceRecord, effect: str | None) -> Stage:
    lead = f"Policy verdict: {trace.policy_verdict}."
    choice = _primary_choice(trace)
    if choice:
        lead = f"Decider choice: {choice}. {lead}"
    if effect:
        lead = f"{lead} Effect: {effect}."
    over = "yes" if trace.policy_overrode_decider else "no"
    return Stage("Authorize", f"{lead} Policy overrode the decider: {over}.", True)


def _primary_choice(trace: TraceRecord) -> str:
    for question_id in ("tool_gate", "route"):
        found = _choice_for(trace, question_id)
        if found:
            return found
    return ""


def _choice_for(trace: TraceRecord, question_id: str) -> str:
    for answer in trace.answers:
        if answer.question_id == question_id and answer.choice:
            return answer.choice
    return ""


def _execute(trace: TraceRecord, calls: tuple[str, ...], pending: tuple[str, ...]) -> Stage:
    if trace.outcome in _STOPPED:
        return Stage("Execute", _stopped_did(trace, pending), False)
    return Stage("Execute", _ran_did(trace, calls), True)


def _stopped_did(trace: TraceRecord, pending: tuple[str, ...]) -> str:
    if trace.outcome == "refused":
        return "Did not run. The request was refused at ingress. No tool was called."
    if trace.outcome == "pending_review":
        return f"Did not run. {_queued(trace, pending)} is pending in the human queue."
    return f"Did not run. Outcome: {trace.outcome}."


def _queued(trace: TraceRecord, pending: tuple[str, ...]) -> str:
    if pending:
        return pending[0]
    if trace.tool_name:
        return trace.tool_name
    return "the request"


def _ran_did(trace: TraceRecord, calls: tuple[str, ...]) -> str:
    if trace.route == "workflow":
        return f"The workflow {trace.workflow_id} ran. Outcome: {trace.outcome}"
    if trace.route == "agent":
        return _agent_did(trace, calls)
    if trace.tool_name:
        return f"The tool {trace.tool_name} ran. Outcome: {trace.outcome}"
    return f"Ran. Outcome: {trace.outcome}"


def _agent_did(trace: TraceRecord, calls: tuple[str, ...]) -> str:
    called = ", ".join(calls) if calls else "none"
    return f"The agent ran. Tools called: {called}. Outcome: {trace.outcome}"


def _period(text: str) -> str:
    if text.endswith((".", "!", "?")):
        return text
    return f"{text}."


def _observe(trace: TraceRecord, pending: tuple[str, ...]) -> Stage:
    queue = ", ".join(pending) if pending else "empty"
    over = "yes" if trace.policy_overrode_decider else "no"
    did = (
        f"The trace records outcome {_period(trace.outcome)} "
        f"Policy overrode the decider: {over}. "
        f"Human queue: {queue}. "
        "If nothing is listening on 127.0.0.1:8000, the decider's answers are the fixture stand-in."
    )
    return Stage("Observe", did, True)
