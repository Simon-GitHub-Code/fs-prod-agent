"""An unavailable decision stays an outage. A contract miss is invalid."""

import pytest

from fs_prod_agent.decisions.contract import Answer, DecisionResult, Question, unavailable, validate_decision


def test_unavailable_is_an_outage_and_not_an_invalid_contract():
    result = unavailable("v1", "decider down")
    assert result.available is False
    assert result.invalid is False
    assert result.contract_version == "v1"
    assert result.error == "decider down"
    assert result.answers == {}
    assert result.model_fields_set == {"contract_version", "available", "invalid", "error"}


def test_an_unavailable_decision_is_not_rewritten():
    raw = DecisionResult(contract_version="v1", available=False, error="down")
    assert validate_decision(raw, _questions()) is raw


@pytest.mark.parametrize(("score", "noul"), [(0.0, 0.0), (3.0, 1.0)])
def test_a_complete_contract_stays_valid(score: float, noul: float):
    raw = _decision(score=score, noul=noul)
    assert validate_decision(raw, _questions()) is raw


def test_question_ids_must_match_the_contract():
    raw = _decision()
    answers = dict(raw.answers)
    del answers["needs_human"]
    result = validate_decision(raw.model_copy(update={"answers": answers}), _questions())
    assert result.invalid is True
    assert result.error == "question ids do not match the contract"


def test_an_answer_type_must_match_its_question():
    raw = _decision(noul_type="choice")
    result = validate_decision(raw, _questions())
    assert result.invalid is True
    assert result.error == "needs_human type mismatch"


def test_an_unknown_choice_names_the_question():
    result = validate_decision(_decision(choice="invent"), _questions())
    assert result.invalid is True
    assert result.error == "unknown choice for route"


def test_choice_criteria_that_are_not_a_map_reject_the_answer():
    result = validate_decision(_decision(choice="workflow"), _questions(choice_criteria=["workflow"]))
    assert result.invalid is True
    assert result.error == "unknown choice for route"


def test_a_missing_score_or_an_empty_scale_is_invalid():
    raw = _decision()
    answers = dict(raw.answers)
    answers["materiality"] = Answer(question_id="materiality", type="score", score=None, confidence=0.9)
    missing = validate_decision(raw.model_copy(update={"answers": answers}), _questions())
    assert missing.invalid is True
    assert missing.error == "score missing for materiality"

    empty = validate_decision(_decision(score=0), _questions(score_criteria=[]))
    assert empty.invalid is True
    assert empty.error == "score missing for materiality"


def test_a_score_scale_must_be_a_list():
    result = validate_decision(
        _decision(score=0),
        _questions(score_criteria={"low": "file", "high": "board"}),
    )
    assert result.invalid is True
    assert result.error == "score missing for materiality"


@pytest.mark.parametrize("score", [-1, 4])
def test_a_score_outside_the_scale_is_invalid(score: float):
    result = validate_decision(_decision(score=score), _questions())
    assert result.invalid is True
    assert result.error == "score out of range for materiality"


@pytest.mark.parametrize("noul", [None, -0.01, 1.5])
def test_a_noul_outside_zero_to_one_is_invalid(noul: float | None):
    raw = _decision()
    answers = dict(raw.answers)
    answers["needs_human"] = Answer(question_id="needs_human", type="noul", noul=noul, confidence=0.9)
    result = validate_decision(raw.model_copy(update={"answers": answers}), _questions())
    assert result.invalid is True
    assert result.error == "noul out of range for needs_human"


def _questions(
    *,
    choice_criteria: dict[str, str] | list[str] | None = None,
    score_criteria: dict[str, str] | list[str] | None = None,
) -> list[Question]:
    if choice_criteria is None:
        choice_criteria = {"workflow": "a known procedure", "agent": "open reasoning"}
    if score_criteria is None:
        score_criteria = ["low", "mid", "high", "top"]
    return [
        Question(id="route", version="v1", type="choice", instructions="Which path?", criteria=choice_criteria),
        Question(id="materiality", version="v1", type="score", instructions="How material?", criteria=score_criteria),
        Question(id="needs_human", version="v1", type="noul", instructions="Does a person have to approve?"),
    ]


def _decision(
    *,
    choice: str = "workflow",
    score: float | None = 0.0,
    noul: float | None = 0.0,
    noul_type: str = "noul",
) -> DecisionResult:
    return DecisionResult(
        contract_version="v1",
        available=True,
        answers={
            "route": Answer(question_id="route", type="choice", choice=choice, confidence=0.9),
            "materiality": Answer(question_id="materiality", type="score", score=score, confidence=0.9),
            "needs_human": Answer(question_id="needs_human", type=noul_type, noul=noul, confidence=0.9),
        },
    )
