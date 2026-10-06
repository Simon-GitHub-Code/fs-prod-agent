"""Write the context pack, or fail when the committed bytes differ."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.context.lib.pack import build_files, pack_diff, write_pack, write_rules  # noqa: E402
from scripts.context.lib.paths import PACK_DIR, RULES_PACK  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the context pack from the tree, or compare it.")
    parser.add_argument("--check", action="store_true", help="exit 1 when the context pack differs")
    args = parser.parse_args(argv)
    files = build_files()
    if args.check:
        diff = pack_diff(files)
        if diff:
            print("context pack is stale: " + ", ".join(diff), file=sys.stderr)
            print("rebuild: uv run python scripts/context/build.py", file=sys.stderr)
            return 1
        return 0
    write_pack(PACK_DIR, files)
    write_rules(RULES_PACK, files)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
