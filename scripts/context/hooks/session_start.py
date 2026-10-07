#!/usr/bin/env python3
"""SessionStart and SubagentStart: hand the agent the pack index, and say whether the local channels are live.

A subagent starts with an empty context, so it gets the same index a session does. The index is small; the
tables behind it are fetched on demand with scripts/context/query.py.

Two health lines follow it. A script that exists is not a script that answers, so the edit hook is run
against an over-cap fixture in a scratch tree and must name it back. And a clone that never installed its
git hooks has no pre-commit or pre-push gate at all, which is indistinguishable from a green one until CI
goes red. Each check that fails says DEAD and names why. A check that breaks still lets the index through.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
EDIT_HOOK = Path(__file__).resolve().parent / "post_edit_complexity.py"
INDEX = Path("docs") / "context" / "index.md"
PROBE_TIMEOUT = 10.0
CANARY = "canary_symbol"
FIXTURE = "def canary_symbol(n):\n" + "".join(f"    if n == {index}:\n        return {index}\n" for index in range(11))
QUERY = (
    "Tables behind this index: `uv run python scripts/context/query.py layer <path>`, "
    "`who-imports <module>`, `hotspots`, `guards`. Ask the pack before you grep."
)


def probe_edit_hook() -> str:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as scratch:
        module = Path(scratch, "src", "fs_prod_agent", "canary.py")
        module.parent.mkdir(parents=True)
        module.write_text(FIXTURE, encoding="utf-8")
        request = json.dumps({"hook_event_name": "PostToolUse", "tool_input": {"file_path": str(module)}})
        try:
            done = subprocess.run(
                [sys.executable, str(EDIT_HOOK)],
                input=request,
                capture_output=True,
                text=True,
                timeout=PROBE_TIMEOUT,
                check=False,
                env={**os.environ, "CLAUDE_PROJECT_DIR": scratch},
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return f"complexity hook DEAD: {type(error).__name__}. tests/fitness/test_complexity.py still gates."
    if done.returncode != 2 or CANARY not in done.stderr:
        return f"complexity hook DEAD: an over-cap fixture drew exit {done.returncode}. The ratchet still gates."
    return f"complexity hook live: an over-cap fixture was named back in {time.perf_counter() - started:.2f}s."


def git_hooks(root: Path) -> str:
    done = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-path", "hooks"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    directory = (root / done.stdout.strip()).resolve() if done.returncode == 0 else None
    missing = [name for name in ("pre-commit", "pre-push") if directory is None or not _drives(directory / name)]
    if missing:
        return (
            f"git hooks DEAD: {', '.join(missing)} not installed. "
            "Run `uv run pre-commit install && uv run pre-commit install --hook-type pre-push`. CI still gates."
        )
    return "git hooks live: pre-commit runs scripts/verify, pre-push runs scripts/secrets."


def _drives(hook: Path) -> bool:
    return hook.is_file() and os.access(hook, os.X_OK) and "pre-commit" in hook.read_text(errors="replace")


def _guarded(check, *arguments) -> str:
    try:
        return check(*arguments)
    except Exception as error:
        return f"{check.__name__} could not run ({type(error).__name__})."


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        payload = {}
    event = payload.get("hook_event_name") if isinstance(payload, dict) else None
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or _REPO).resolve()
    index = root / INDEX
    if not index.is_file():
        return 0
    health = [_guarded(probe_edit_hook), _guarded(git_hooks, root)]
    context = "\n".join([index.read_text(encoding="utf-8"), QUERY, "", *health, ""])
    hook_output = {"hookEventName": event or "SessionStart", "additionalContext": context}
    print(json.dumps({"hookSpecificOutput": hook_output}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
