"""Exit 1 unless every mutant was killed. mutmut run itself exits 0 with survivors."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from mutmut.stats import status_by_exit_code

_ACCEPT = {"killed", "caught by type check"}


def outcomes(mutants_dir: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for meta in sorted(mutants_dir.rglob("*.meta")):
        data = json.loads(meta.read_text(encoding="utf-8"))
        for name, code in data["exit_code_by_key"].items():
            found[name] = status_by_exit_code[code]
    return found


def failures(found: dict[str, str]) -> dict[str, str]:
    if not found:
        return {"<none>": "no mutants"}
    return {name: status for name, status in found.items() if status not in _ACCEPT}


def main() -> int:
    found = outcomes(Path("mutants"))
    bad = failures(found)
    if bad:
        for name, status in sorted(bad.items()):
            print(f"{status}: {name}", file=sys.stderr)
        print(f"{len(bad)} mutant(s) were not killed", file=sys.stderr)
        return 1
    print(f"killed {len(found)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
