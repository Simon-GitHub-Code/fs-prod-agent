"""Answer layer, import, hotspot, and guard questions from the live tree.

python scripts/context/query.py layer <path>
python scripts/context/query.py who-imports <module> [--transitive]
python scripts/context/query.py hotspots [--path P] [--all]
python scripts/context/query.py guards [--keyword K]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.context.lib.complexity import CAP, function_scores  # noqa: E402
from scripts.context.lib.guards import guard_rows  # noqa: E402
from scripts.context.lib.pack import MARGIN, hotspot_rows, report_for, who_imports  # noqa: E402
from scripts.context.lib.paths import REPO, SRC  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query the context pack measurements.")
    commands = parser.add_subparsers(dest="command", required=True)

    layer = commands.add_parser("layer")
    layer.add_argument("path")

    imports = commands.add_parser("who-imports")
    imports.add_argument("module")
    imports.add_argument("--transitive", action="store_true")

    spots = commands.add_parser("hotspots")
    spots.add_argument("--path")
    spots.add_argument("--all", action="store_true")

    guards = commands.add_parser("guards")
    guards.add_argument("--keyword", default="")

    args = parser.parse_args(argv)
    if args.command == "layer":
        text = report_for(_resolve(args.path))
        if text is None:
            print(f"{args.path} is outside {REPO}", file=sys.stderr)
            return 2
        sys.stdout.write(text)
        return 0
    if args.command == "who-imports":
        sys.stdout.write(who_imports(args.module, transitive=args.transitive))
        return 0
    if args.command == "hotspots":
        sys.stdout.write(_hotspots(args.path, args.all))
        return 0
    sys.stdout.write(_guards(args.keyword))
    return 0


def _resolve(text: str) -> Path:
    candidate = Path(text)
    if candidate.is_absolute():
        return candidate
    if (REPO / candidate).exists():
        return REPO / candidate
    if (SRC / candidate).exists():
        return SRC / candidate
    return REPO / candidate


def _hotspots(prefix: str | None, include_all: bool) -> str:
    rows = hotspot_rows() if not include_all else _every_score()
    if prefix:
        relative = _source_prefix(prefix)
        rows = [row for row in rows if row[0] == relative or row[0].startswith(relative.rstrip("/") + "/")]
    lines = ["path  symbol  cc  cap  headroom"]
    for path, symbol, cc, cap, headroom in rows:
        lines.append(f"{path}  {symbol}  {cc}  {cap}  {headroom}")
    if len(lines) == 1:
        lines.append(f"none within {MARGIN} of the cap")
    return "\n".join(lines) + "\n"


def _every_score() -> list[tuple[str, str, int, int, int]]:
    rows: list[tuple[str, str, int, int, int]] = []
    for key, score in sorted(function_scores(SRC).items()):
        path, _, symbol = key.partition("::")
        rows.append((path, symbol, score, CAP, CAP - score))
    return rows


def _source_prefix(text: str) -> str:
    candidate = _resolve(text)
    try:
        return candidate.resolve().relative_to(SRC.resolve()).as_posix()
    except ValueError:
        return text.removeprefix("src/fs_prod_agent/")


def _guards(keyword: str) -> str:
    needle = keyword.casefold()
    lines = ["path  summary"]
    for path, summary, tests in guard_rows():
        haystack = f"{path} {summary} {tests}".casefold()
        if needle and needle not in haystack:
            continue
        lines.append(f"{path}  {summary}")
    if len(lines) == 1:
        lines.append("none")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
