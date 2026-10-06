from fs_prod_agent.decisions.contract import Question
from fs_prod_agent.decisions.v1.materiality import MATERIALITY_QUESTIONS
from fs_prod_agent.decisions.v1.route import INGRESS_QUESTIONS
from fs_prod_agent.decisions.v1.tool_gate import TOOL_GATE_QUESTIONS

CONTRACT_VERSION = "v1"


def iter_questions() -> list[Question]:
    return [*INGRESS_QUESTIONS, *TOOL_GATE_QUESTIONS]


__all__ = [
    "CONTRACT_VERSION",
    "INGRESS_QUESTIONS",
    "MATERIALITY_QUESTIONS",
    "TOOL_GATE_QUESTIONS",
    "iter_questions",
]
