"""Versioned question contracts. Instructions are API text."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

QuestionType = Literal["choice", "score", "noul"]


class Question(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: str
    type: QuestionType
    instructions: str
    criteria: dict[str, str] | list[str] | None = None


class Answer(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str
    type: QuestionType
    choice: str | None = None
    score: float | None = None
    noul: float | None = None
    confidence: float | None = None
    probabilities: dict[str, float] = Field(default_factory=dict)


class DecisionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract_version: str
    available: bool
    invalid: bool = False
    answers: dict[str, Answer] = Field(default_factory=dict)
    error: str | None = None


def unavailable(contract_version: str, error: str) -> DecisionResult:
    return DecisionResult(
        contract_version=contract_version,
        available=False,
        invalid=False,
        error=error,
    )


def validate_decision(decision: DecisionResult, questions: list[Question]) -> DecisionResult:
    """Mark a response invalid when a choice or score falls outside the contract."""
    if not decision.available:
        return decision
    by_id = {question.id: question for question in questions}
    if set(decision.answers) != set(by_id):
        return decision.model_copy(update={"invalid": True, "error": "question ids do not match the contract"})
    for answer in decision.answers.values():
        question = by_id[answer.question_id]
        if answer.type != question.type:
            return decision.model_copy(update={"invalid": True, "error": f"{answer.question_id} type mismatch"})
        if question.type == "choice":
            criteria = question.criteria if isinstance(question.criteria, dict) else {}
            if answer.choice not in criteria:
                return decision.model_copy(update={"invalid": True, "error": f"unknown choice for {question.id}"})
        if question.type == "score":
            levels = question.criteria if isinstance(question.criteria, list) else []
            if answer.score is None or not levels:
                return decision.model_copy(update={"invalid": True, "error": f"score missing for {question.id}"})
            if answer.score < 0 or answer.score > len(levels) - 1:
                return decision.model_copy(update={"invalid": True, "error": f"score out of range for {question.id}"})
        if question.type == "noul" and (answer.noul is None or not 0.0 <= answer.noul <= 1.0):
            return decision.model_copy(update={"invalid": True, "error": f"noul out of range for {question.id}"})
    return decision
