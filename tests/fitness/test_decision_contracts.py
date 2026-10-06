"""Question text is an API. Editing v1 instructions fails until the version directory changes."""

import ast
import json

from fs_prod_agent.decisions.v1 import iter_questions
from fs_prod_agent.decisions.v1.materiality import MATERIALITY_QUESTIONS
from fs_prod_agent.decisions.v1.route import INGRESS_QUESTIONS
from tests.fitness.support import REPO, SRC

_ALLOWED_TYPES = {"choice", "score", "noul"}


def test_question_types_are_choice_score_or_noul():
    tree = ast.parse((SRC / "decisions" / "contract.py").read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "QuestionType" for target in node.targets):
            continue
        found = _literal_strings(node.value)
    assert found == ["choice", "score", "noul"]
    for question in iter_questions():
        assert question.type in _ALLOWED_TYPES
        assert question.id
        assert question.version == "v1"
        assert question.instructions
        if question.type == "choice":
            assert isinstance(question.criteria, dict) and question.criteria
        elif question.type == "score":
            assert isinstance(question.criteria, list) and question.criteria
        else:
            assert question.criteria is None


def test_v1_instructions_match_the_snapshot():
    version_dirs = sorted(
        path.name for path in (SRC / "decisions").iterdir() if path.is_dir() and path.name.startswith("v")
    )
    assert version_dirs == ["v1"]
    for version in version_dirs:
        snapshot = REPO / "tests" / "fitness" / "snapshots" / f"decisions_{version}.json"
        assert snapshot.is_file(), f"missing snapshot for {version}"
    recorded = json.loads((REPO / "tests" / "fitness" / "snapshots" / "decisions_v1.json").read_text(encoding="utf-8"))
    assert recorded == [question.model_dump() for question in iter_questions()]


def test_materiality_question_is_the_ingress_question():
    assert MATERIALITY_QUESTIONS == [question for question in INGRESS_QUESTIONS if question.id == "materiality"]
    assert [question.id for question in iter_questions()].count("materiality") == 1


def _literal_strings(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.Tuple):
        values: list[str] = []
        for element in node.elts:
            values.extend(_literal_strings(element))
        return values
    if isinstance(node, ast.Subscript):
        return _literal_strings(node.slice)
    return []
