#!/usr/bin/env python3
"""Rebuild the context pack after an edit, and return it when the bytes change.

A read, and an edit that leaves the pack unchanged, returns the layer query.
Exit 0 either way. Grok loads `.grok/rules/context-pack.md` at session start.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
QUERY = REPO / "scripts" / "context" / "query.py"
BUILD = REPO / "scripts" / "context" / "build.py"
RULES_PACK = REPO / ".grok" / "rules" / "context-pack.md"
# additionalContext is clipped at 10000 characters by the harness.
CONTEXT_LIMIT = 10000

_EDIT_TOOLS = {"write", "edit", "search_replace", "strreplace", "multiedit"}
_PATH_KEYS = ("target_file", "file_path", "path")


def regenerates(tool_name: str) -> bool:
    return tool_name.lower() in _EDIT_TOOLS


def path_from(payload: dict) -> str | None:
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        return None
    for key in _PATH_KEYS:
        raw = tool_input.get(key)
        if isinstance(raw, str) and raw:
            return raw
    return None


def tool_name_from(payload: dict) -> str:
    raw = payload.get("tool_name") or payload.get("toolName") or ""
    return raw if isinstance(raw, str) else ""


def context_for(payload: dict) -> str | None:
    target = path_from(payload)
    if target is None:
        return None
    changed = _rebuilt_pack() if regenerates(tool_name_from(payload)) else None
    if changed:
        return note_for(changed, None)
    return note_for(None, _layer(target))


def note_for(changed_pack: str | None, layer: str | None) -> str | None:
    if changed_pack:
        return changed_pack
    return layer


def bounded(text: str) -> str:
    if len(text) <= CONTEXT_LIMIT:
        return text
    note = "\n[truncated; full file is .grok/rules/context-pack.md]\n"
    return text[: CONTEXT_LIMIT - len(note)] + note


def _layer(target: str) -> str | None:
    result = subprocess.run(
        [sys.executable, str(QUERY), "layer", target],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout


def _rebuilt_pack() -> str | None:
    before = _rules_text()
    result = subprocess.run([sys.executable, str(BUILD)], cwd=REPO, capture_output=True, text=True, check=False)
    after = _rules_text()
    if result.returncode != 0 or not after or after == before:
        return None
    return after


def _rules_text() -> str:
    if not RULES_PACK.is_file():
        return ""
    return RULES_PACK.read_text(encoding="utf-8")


def main() -> int:
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    text = context_for(payload)
    if text is None:
        return 0
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": bounded(text),
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
