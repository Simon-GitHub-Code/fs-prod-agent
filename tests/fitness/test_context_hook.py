"""The file hook runs the pack scripts. It does not ask the agent to."""

import importlib.util
import io
import json
import subprocess
from unittest.mock import patch

from scripts.context.lib.paths import REPO, RULES_PACK, SRC


def _hook():
    path = REPO / ".grok" / "hooks" / "context_pack.py"
    spec = importlib.util.spec_from_file_location("context_pack", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_an_edit_regenerates_and_a_read_does_not():
    hook = _hook()
    assert hook.regenerates("search_replace")
    assert hook.regenerates("Write")
    assert hook.regenerates("write")
    assert not hook.regenerates("read_file")
    assert not hook.regenerates("Read")
    assert not hook.regenerates("grep")


def test_a_read_returns_the_query_script():
    hook = _hook()
    target = str(SRC / "domain" / "oversight.py")
    payload = {"tool_name": "read_file", "tool_input": {"target_file": target}}
    text = hook.context_for(payload)
    assert text is not None
    assert "layer: domain" in text
    assert "pack:" in text
    calls = []
    real = hook.subprocess.run

    def _record(*args, **kwargs):
        calls.append(args[0])
        return real(*args, **kwargs)

    with patch.object(hook.subprocess, "run", side_effect=_record):
        hook.context_for(payload)
    commands = [" ".join(command) for command in calls]
    assert any("query.py" in command and "layer" in command for command in commands)
    assert all("build.py" not in command for command in commands)


def test_the_hook_reads_the_generated_rules_file():
    hook = _hook()
    assert hook.RULES_PACK == RULES_PACK
    assert hook.CONTEXT_LIMIT == 10000


def test_a_long_note_is_marked_truncated():
    hook = _hook()
    text = hook.bounded("x" * (hook.CONTEXT_LIMIT + 20))
    assert len(text) == hook.CONTEXT_LIMIT
    assert text.endswith("[truncated; full file is .grok/rules/context-pack.md]\n")
    assert hook.bounded("short") == "short"


def test_an_edit_that_changes_the_pack_returns_the_rules_file():
    hook = _hook()
    state = {"n": 0}

    def _text() -> str:
        state["n"] += 1
        return "before\n" if state["n"] == 1 else "# Context pack\nafter\n"

    hook._rules_text = _text
    payload = {"tool_name": "search_replace", "tool_input": {"file_path": str(SRC / "domain" / "oversight.py")}}
    with patch.object(hook.subprocess, "run", side_effect=_scripted):
        assert hook.context_for(payload) == "# Context pack\nafter\n"


def test_an_unchanged_or_failed_rebuild_returns_the_layer():
    hook = _hook()
    payload = {"tool_name": "search_replace", "tool_input": {"file_path": str(SRC / "domain" / "oversight.py")}}
    hook._rules_text = lambda: "same\n"
    with patch.object(hook.subprocess, "run", side_effect=_scripted):
        assert hook.context_for(payload) == "layer: domain\n"

    state = {"n": 0}

    def _text() -> str:
        state["n"] += 1
        return "before\n" if state["n"] == 1 else "after\n"

    hook._rules_text = _text
    with patch.object(hook.subprocess, "run", side_effect=_failed_build):
        assert hook.context_for(payload) == "layer: domain\n"


def test_an_edit_invokes_the_pack_build():
    hook = _hook()
    calls: list[list[str]] = []
    real = hook.subprocess.run

    def _record(*args, **kwargs):
        calls.append(args[0])
        return real(*args, **kwargs)

    payload = {"tool_name": "search_replace", "tool_input": {"file_path": str(SRC / "domain" / "oversight.py")}}
    with patch.object(hook.subprocess, "run", side_effect=_record):
        text = hook.context_for(payload)
    commands = [" ".join(command) for command in calls]
    assert any("build.py" in command for command in commands)
    assert text


def test_a_tool_without_a_file_is_silent():
    hook = _hook()
    assert hook.context_for({"tool_name": "grep", "tool_input": {"pattern": "authorize"}}) is None


def test_main_prints_hook_context():
    hook = _hook()
    payload = json.dumps(
        {
            "toolName": "read_file",
            "tool_input": {"target_file": str(SRC / "policy" / "authorize.py")},
        }
    )
    stdout = io.StringIO()
    with patch("sys.stdin", io.StringIO(payload)), patch("sys.stdout", stdout):
        assert hook.main() == 0
    body = json.loads(stdout.getvalue())
    text = body["hookSpecificOutput"]["additionalContext"]
    assert "layer: policy" in text
    assert "authorize cc=16" in text


def _scripted(command, **_kwargs):
    joined = " ".join(command)
    if "build.py" in joined:
        return subprocess.CompletedProcess(command, 0)
    return subprocess.CompletedProcess(command, 0, stdout="layer: domain\n", stderr="")


def _failed_build(command, **_kwargs):
    joined = " ".join(command)
    if "build.py" in joined:
        return subprocess.CompletedProcess(command, 1)
    return subprocess.CompletedProcess(command, 0, stdout="layer: domain\n", stderr="")
