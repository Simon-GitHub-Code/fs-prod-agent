#!/usr/bin/env python3
"""Ask before a write to a hash-pinned test or quality control. Exit 0 either way."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.guardpin import PINNED_FILES, PINNED_TREES, is_protected  # noqa: E402

_WRITE_TOOLS = {"write", "edit", "search_replace", "strreplace", "multiedit"}
_SHELL_TOOLS = {"bash", "shell", "run_terminal_command"}
_PATH_KEYS = ("target_file", "file_path", "path")
_MUTATING = {"rm", "mv", "cp", "tee", "truncate"}
_BLESS_FLAGS = ("--caught", "--routine", "--init")


def tool_name_from(payload: dict) -> str:
    raw = payload.get("tool_name") or payload.get("toolName") or ""
    return raw if isinstance(raw, str) else ""


def _tool_input(payload: dict) -> dict:
    raw = payload.get("tool_input") or payload.get("toolInput") or {}
    return raw if isinstance(raw, dict) else {}


def path_from(payload: dict) -> str | None:
    for key in _PATH_KEYS:
        raw = _tool_input(payload).get(key)
        if isinstance(raw, str) and raw:
            return raw
    return None


def command_from(payload: dict) -> str | None:
    for key in ("command", "cmd"):
        raw = _tool_input(payload).get(key)
        if isinstance(raw, str) and raw:
            return raw
    return None


def command_needs_approval(command: str) -> bool:
    if _invokes_bless(command):
        return True
    if _redirects_onto_pinned(command):
        return True
    return _mutates_pinned(command)


def decision_for(payload: dict) -> dict | None:
    tool = tool_name_from(payload).lower()
    if tool in _WRITE_TOOLS:
        target = path_from(payload)
        if target and is_protected(target):
            return _ask(target)
        return None
    if tool in _SHELL_TOOLS:
        command = command_from(payload)
        if command and command_needs_approval(command):
            return _ask(command)
    return None


def main() -> int:
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    try:
        decision = decision_for(payload)
    except Exception:
        return 0
    if decision is not None:
        json.dump(decision, sys.stdout)
    return 0


def _ask(subject: str) -> dict:
    reason = (
        f"{subject} is a pinned test or quality control. "
        "Approve this only if the change is deliberate. "
        "The suite stays red until scripts/bless names every moved path with --caught or --routine."
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }


def _mentions_pinned(text: str) -> bool:
    if any(tree in text for tree in PINNED_TREES):
        return True
    return any(rel in text for rel in PINNED_FILES)


def _invokes_bless(command: str) -> bool:
    if "scripts/bless" not in command:
        return False
    return any(flag in command for flag in _BLESS_FLAGS)


def _redirects_onto_pinned(command: str) -> bool:
    for match in re.finditer(r">\s*([^\s;&|]+)", command):
        if _mentions_pinned(match.group(1)):
            return True
    return False


def _mutates_pinned(command: str) -> bool:
    for segment in re.split(r"[;&|]", command):
        if _segment_mutates(segment):
            return True
    return False


def _segment_mutates(segment: str) -> bool:
    parts = segment.split()
    if not parts:
        return False
    head = Path(parts[0]).name
    if head in _MUTATING and any(_mentions_pinned(part) for part in parts[1:]):
        return True
    return head == "sed" and "-i" in parts and any(_mentions_pinned(part) for part in parts)
