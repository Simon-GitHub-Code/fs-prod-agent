"""The mutation run stays pointed at the decision modules and the unit tests that exercise them."""

import json
import tomllib
from pathlib import Path

from scripts.context.lib.paths import REPO
from scripts.mutate_status import failures, outcomes

_PATHS = [
    "src/fs_prod_agent/domain/oversight.py",
    "src/fs_prod_agent/policy/authorize.py",
    "src/fs_prod_agent/decisions/contract.py",
]
_TESTS = [
    "tests/unit/test_oversight.py",
    "tests/unit/test_policy.py",
    "tests/unit/test_decision_contracts.py",
]


def test_mutmut_paths_are_the_decision_modules():
    config = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    mutmut = config["tool"]["mutmut"]
    assert mutmut["source_paths"] == ["src/fs_prod_agent"]
    assert mutmut["only_mutate"] == _PATHS
    assert mutmut["pytest_add_cli_args_test_selection"] == _TESTS
    assert mutmut["also_copy"] == ["scripts", "evals"]


def test_ci_runs_the_mutation_gate():
    workflow = (REPO / ".github" / "workflows" / "fitness.yml").read_text(encoding="utf-8")
    script = (REPO / "scripts" / "mutate").read_text(encoding="utf-8")
    assert "scripts/mutate\n" in workflow
    assert "mutmut run" not in workflow
    assert "rm -rf mutants" in script
    assert "mutmut run" in script
    assert "scripts/mutate_status.py" in script


def test_mutation_gate_rejects_a_survivor_and_a_line_no_test_runs(tmp_path: Path):
    meta = tmp_path / "mod.py.meta"
    meta.write_text(
        json.dumps({"exit_code_by_key": {"alive": 0, "missed": 33, "dead": 1}}),
        encoding="utf-8",
    )
    assert failures(outcomes(tmp_path)) == {"alive": "survived", "missed": "no tests"}


def test_mutation_gate_rejects_an_empty_run(tmp_path: Path):
    assert failures(outcomes(tmp_path)) == {"<none>": "no mutants"}


def test_a_type_checker_catch_counts_as_killed():
    assert failures({"typed": "caught by type check", "dead": "killed"}) == {}
