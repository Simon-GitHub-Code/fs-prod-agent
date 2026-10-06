"""Every registered path has an eval suite. A case without a verdict does not load."""

import json
from pathlib import Path

import pytest

from fs_prod_agent.application.registry import agents, workflows
from fs_prod_agent.evals.loader import load_cases
from tests.fitness.support import REPO

_TASKS = REPO / "evals" / "tasks"


def test_every_registered_path_resolves_to_a_task_file():
    loaded = {case.id: case for case in load_cases(_TASKS)}
    for spec in [*workflows(), *agents()]:
        path = _TASKS / f"{spec.eval_suite}.json"
        assert path.is_file(), spec.eval_suite
        assert spec.eval_suite in loaded
        assert loaded[spec.eval_suite].expected_verdict


def test_a_case_without_a_verdict_fails_to_load(tmp_path: Path):
    (tmp_path / "missing.json").write_text(
        json.dumps(
            {
                "id": "missing",
                "stage": "ingress",
                "request": "Prepare the quarterly pack",
                "actor_id": "analyst-1",
                "role": "analyst",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="expected verdict"):
        load_cases(tmp_path)


def test_drift_windows_are_not_eval_cases():
    with pytest.raises(ValueError, match="expected verdict"):
        load_cases(REPO / "evals" / "drift")
