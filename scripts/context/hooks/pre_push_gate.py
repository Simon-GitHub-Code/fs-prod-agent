#!/usr/bin/env python3
"""Refuse the Bash call that would git push while scripts/verify is red.

The gate runs where it matters: before anything leaves the machine, not at the end of every turn. Git
cannot force a local hook to exist and --no-verify skips the ones that do, so an agent's push is the last
place local checking can be made deterministic. CI remains the floor.

Detection is tokenised, never a substring match: a commit message or an echo that mentions a push is not
one, and blocking those would teach an agent to route around the channel. The checkout gated is the one
the call runs in, read from the hook's cwd, a `cd`, or `git -C`.

The polarity is the opposite of the advisory edit hook. That one is silent when it breaks. This one
refuses with a reason when it cannot reach a verdict, because silence from a gate reads as a pass.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

VERIFY = Path("scripts") / "verify"
VERIFY_TIMEOUT = 280
REPORTED_CHARS = 3000
_SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", "\n"}
_TAKES_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def segments(command: str) -> list[list[str]]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    found: list[list[str]] = [[]]
    for token in lexer:
        if token in _SEPARATORS:
            found.append([])
        else:
            found[-1].append(token)
    return [segment for segment in found if segment]


def push_target(command: str, cwd: Path) -> Path | None:
    """The directory a push in this command would run in, or None when nothing here pushes."""
    here = cwd
    for segment in segments(command):
        words = _without_prefix(segment)
        if words[:1] == ["cd"] and len(words) > 1:
            here = (here / words[1]).resolve()
            continue
        if words and Path(words[0]).name == "git":
            directory, subcommand = _git_call(words[1:], here)
            if subcommand == "push":
                return directory
    return None


def _without_prefix(segment: list[str]) -> list[str]:
    index = 0
    while index < len(segment) and ("=" in segment[index] and not segment[index].startswith("-")):
        index += 1
    if index < len(segment) and segment[index] == "env":
        return _without_prefix(segment[index + 1 :])
    return segment[index:]


def _git_call(arguments: list[str], here: Path) -> tuple[Path, str | None]:
    index = 0
    while index < len(arguments):
        word = arguments[index]
        if word in _TAKES_VALUE and index + 1 < len(arguments):
            if word == "-C":
                here = (here / arguments[index + 1]).resolve()
            index += 2
        elif word.startswith("-"):
            index += 1
        else:
            return here, word
    return here, None


def checkout(directory: Path) -> Path | None:
    done = subprocess.run(
        ["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return Path(done.stdout.strip()) if done.returncode == 0 and done.stdout.strip() else None


def deny(reason: str) -> int:
    decision = {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}
    print(json.dumps({"hookSpecificOutput": decision}))
    return 0


def gate(payload: dict) -> int:
    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str) or "push" not in command:
        return 0
    cwd = Path(payload.get("cwd") or ".").resolve()
    try:
        directory = push_target(command, cwd)
    except ValueError:
        return deny("The command does not tokenise, so whether it pushes cannot be read. Rewrite it plainly.")
    if directory is None:
        return 0
    root = checkout(directory)
    if root is None or not (root / VERIFY).is_file():
        return 0
    try:
        done = subprocess.run([str(root / VERIFY)], cwd=root, capture_output=True, text=True, timeout=VERIFY_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as error:
        return deny(f"scripts/verify could not reach a verdict ({type(error).__name__}); push refused.")
    if done.returncode == 0:
        return 0
    tail = (done.stdout + done.stderr)[-REPORTED_CHARS:]
    return deny(f"scripts/verify is red in {root}, so this push is refused. Fix the suite first.\n{tail}")


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        return gate(payload)
    except Exception as error:
        return deny(f"the push gate itself failed ({type(error).__name__}); push refused.")


if __name__ == "__main__":
    raise SystemExit(main())
