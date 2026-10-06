"""The stop hook blocks a red suite and stays quiet for a session-end fire."""

import importlib.util

from tests.fitness.support import REPO


def _hook():
    path = REPO / ".grok" / "hooks" / "fitness_stop.py"
    spec = importlib.util.spec_from_file_location("fitness_stop", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_red_suite_blocks_the_turn():
    decision = _hook().gate_decision("Stop", "end_turn", 1, "failed test_policy")
    assert decision is not None
    assert decision["decision"] == "block"
    assert "scripts/verify failed" in decision["reason"]
    assert "failed test_policy" in decision["reason"]


def test_a_green_suite_allows_the_turn():
    assert _hook().gate_decision("Stop", "end_turn", 0, "") is None


def test_session_end_does_not_run_as_a_gate():
    assert _hook().gate_decision("Stop", "shutdown", 1, "failed") is None
