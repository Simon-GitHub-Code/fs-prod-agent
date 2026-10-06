"""A write to a pinned control asks. A read, and a write to product code, do not."""

import importlib.util
import io
import json
from unittest.mock import patch

from tests.fitness.support import REPO


def test_an_edit_of_a_fitness_test_asks():
    decision = _hook().decision_for(_edit("tests/fitness/test_policy.py"))
    assert decision is not None
    assert decision["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_an_edit_of_the_manifest_asks():
    decision = _hook().decision_for(_edit("tests/fitness/_guard_manifest.json"))
    assert decision["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_an_edit_of_product_code_does_not_ask():
    assert _hook().decision_for(_edit("src/fs_prod_agent/domain/oversight.py")) is None


def test_an_edit_of_a_unit_or_integration_test_does_not_ask():
    hook = _hook()
    assert hook.decision_for(_edit("tests/unit/test_policy.py")) is None
    assert hook.decision_for(_edit("tests/integration/test_router.py")) is None


def test_a_read_does_not_ask():
    payload = {"tool_name": "read_file", "tool_input": {"target_file": "tests/fitness/test_policy.py"}}
    assert _hook().decision_for(payload) is None


def test_running_the_suite_does_not_ask():
    payload = {"tool_name": "run_terminal_command", "tool_input": {"command": "scripts/verify"}}
    assert _hook().decision_for(payload) is None


def test_blessing_or_deleting_a_pinned_path_asks():
    hook = _hook()
    bless = {
        "tool_name": "bash",
        "tool_input": {"command": "python scripts/bless --routine tests/fitness/test_policy.py"},
    }
    remove = {"tool_name": "bash", "tool_input": {"command": "rm tests/fitness/test_policy.py"}}
    assert hook.decision_for(bless)["hookSpecificOutput"]["permissionDecision"] == "ask"
    assert hook.decision_for(remove)["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_main_prints_the_ask():
    hook = _hook()
    payload = json.dumps(_edit("scripts/verify"))
    stdout = io.StringIO()
    with patch("sys.stdin", io.StringIO(payload)), patch("sys.stdout", stdout):
        assert hook.main() == 0
    body = json.loads(stdout.getvalue())
    assert body["hookSpecificOutput"]["permissionDecision"] == "ask"
    assert "scripts/verify" in body["hookSpecificOutput"]["permissionDecisionReason"]


def _edit(path: str) -> dict:
    return {"tool_name": "search_replace", "tool_input": {"file_path": path}}


def _hook():
    path = REPO / ".grok" / "hooks" / "approval.py"
    spec = importlib.util.spec_from_file_location("approval_hook", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
