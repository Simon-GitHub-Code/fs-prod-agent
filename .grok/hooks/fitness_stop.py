#!/usr/bin/env python3
"""Block the end of a turn when scripts/verify is red. CI remains the floor.

Grok sends a Stop `reason`; only `end_turn` is a gate. Claude Code sends no
reason, so every Claude Stop is the end of a turn. Claude sets `stop_hook_active`
when the turn is already continuing from a block; that stop is let through, so a
red suite blocks once instead of looping.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VERIFY = REPO / "scripts" / "verify"


def gate_decision(event_name: str | None, reason: str | None, returncode: int, output: str) -> dict[str, str] | None:
    if session_end(event_name, reason):
        return None
    if returncode == 0:
        return None
    tail = output[-4000:]
    return {
        "decision": "block",
        "reason": "scripts/verify failed. Fix the fitness suite before finishing.\n" + tail,
    }


def session_end(event_name: str | None, reason: str | None) -> bool:
    return event_name in {"Stop", "stop"} and reason is not None and reason != "end_turn"


def main() -> int:
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    event_name = payload.get("hook_event_name") or payload.get("hookEventName")
    reason = payload.get("reason")
    if session_end(event_name, reason) or payload.get("stop_hook_active"):
        return 0
    result = subprocess.run([str(VERIFY)], cwd=REPO, capture_output=True, text=True, check=False)
    decision = gate_decision(event_name, reason, result.returncode, result.stdout + result.stderr)
    if decision is None:
        return 0
    json.dump(decision, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
