#!/usr/bin/env python3
"""After a Write or Edit to production code: keep the pack current, and speak only when a function is over the cap.

Silence is the normal answer. A note on every edit gets skimmed, and a skimmed channel is a dead one, so
this says something in exactly one case: the edited file leaves a function over the cyclomatic cap, or a
named exception over its recorded score. That is scored by scripts/context/lib/complexity.py, the same
counter tests/fitness/test_complexity.py runs, so the hook cannot disagree with the gate. It answers on
stderr with exit 2, which Claude Code hands back in the same turn. The write has already landed; this is
feedback, not a block, and the ratchet still fails at verify.

The pack under docs/context/ is rebuilt quietly after the same edits, so a moved import edge or hotspot
never reaches the gate as a stale-pack failure. Any error here is silence: a diagnostic that can break the
tool call it observes is worse than none.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.context.lib.complexity import CAP, GRANDFATHERED, scores_in  # noqa: E402

FEEDBACK = 2
SILENT = 0
PACKAGE = Path("src") / "fs_prod_agent"
BUILD = Path("scripts") / "context" / "build.py"
REBUILD_TIMEOUT = 60


def project_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or _REPO).resolve()


def edited_module(payload: dict, root: Path) -> Path | None:
    tool_input = payload.get("tool_input")
    raw = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw) if Path(raw).is_absolute() else root / raw
    path = path.resolve()
    if path.suffix != ".py" or not path.is_file() or not path.is_relative_to(root / PACKAGE):
        return None
    return path


def breaches(path: Path, package: Path) -> list[str]:
    relative = path.relative_to(package).as_posix()
    found: list[str] = []
    for symbol, score in scores_in(relative, path.read_text(encoding="utf-8")).items():
        allowed = GRANDFATHERED.get(symbol, CAP)
        if score > allowed:
            limit = f"its recorded {allowed}" if symbol in GRANDFATHERED else f"the cap of {allowed}"
            found.append(f"{symbol} scores {score}, over {limit}")
    return found


def rebuild_pack(root: Path) -> None:
    if (root / BUILD).is_file():
        subprocess.run(
            ["uv", "run", "--frozen", "--quiet", "python", str(BUILD)],
            cwd=root,
            capture_output=True,
            timeout=REBUILD_TIMEOUT,
            check=False,
        )


def run(raw: str) -> int:
    payload = json.loads(raw) if raw.strip() else {}
    root = project_root()
    path = edited_module(payload, root) if isinstance(payload, dict) else None
    if path is None:
        return SILENT
    found = breaches(path, root / PACKAGE)
    rebuild_pack(root)
    if not found:
        return SILENT
    print(
        "Complexity: " + "; ".join(found) + ". tests/fitness/test_complexity.py fails on this. Split the function.",
        file=sys.stderr,
    )
    return FEEDBACK


def main() -> int:
    try:
        return run(sys.stdin.read())
    except Exception:
        return SILENT


if __name__ == "__main__":
    raise SystemExit(main())
