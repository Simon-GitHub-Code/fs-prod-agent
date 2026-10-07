#!/usr/bin/env python3
"""Rebuild the context pack after an edit, and return it when the bytes change.

A read, and an edit that leaves the pack unchanged, returns the layer query.
Exit 0 either way. Grok loads `.grok/rules/context-pack.md` at session start.

--delta (Claude Code) returns only the pack lines an edit changed, plus the layer query, instead of the
whole pack. Claude already has the pack from CLAUDE.md, so the full copy after every write only spends
context.
"""

from __future__ import annotations

import difflib
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
DELTA_LIMIT = 2000

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


def context_for(payload: dict, delta: bool = False) -> str | None:
    target = path_from(payload)
    if target is None:
        return None
    changed = _rebuilt_pack() if regenerates(tool_name_from(payload)) else None
    if changed and not delta:
        return changed[1]
    layer = _layer(target)
    if changed:
        return pack_delta(*changed) + ("\n" + layer if layer else "")
    return layer


def pack_delta(before: str, after: str) -> str:
    diff = difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
    lines = [line for line in diff if line[:1] in "+-" and not line.startswith(("+++", "---"))]
    text = f"Context pack rebuilt; {len(lines)} lines changed (full pack: .grok/rules/context-pack.md):\n"
    text += "\n".join(lines) + "\n"
    if len(text) <= DELTA_LIMIT:
        return text
    return text[:DELTA_LIMIT] + "\n[more lines changed; see .grok/rules/context-pack.md]\n"


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


def _rebuilt_pack() -> tuple[str, str] | None:
    before = _rules_text()
    result = subprocess.run([sys.executable, str(BUILD)], cwd=REPO, capture_output=True, text=True, check=False)
    after = _rules_text()
    if result.returncode != 0 or not after or after == before:
        return None
    return before, after


def _rules_text() -> str:
    if not RULES_PACK.is_file():
        return ""
    return RULES_PACK.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    delta = "--delta" in (sys.argv[1:] if argv is None else argv)
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    text = context_for(payload, delta)
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
