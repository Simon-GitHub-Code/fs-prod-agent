"""Hash pin for fitness tests and the quality controls around them.

The manifest cannot hash itself: writing it would change the bytes just recorded.
The ledger is written during a bless, so it has the same problem. Both still count
as protected writes. A new file under a pinned tree is covered as soon as it exists.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from scripts.context.lib.paths import REPO

MANIFEST_PATH = REPO / "tests" / "fitness" / "_guard_manifest.json"
LEDGER_PATH = REPO / "tests" / "fitness" / "_bless_ledger.jsonl"

_EXCLUDED_NAMES = {MANIFEST_PATH.name, LEDGER_PATH.name}
_EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
_UNHASHED = (
    "tests/fitness/_guard_manifest.json",
    "tests/fitness/_bless_ledger.jsonl",
)

PINNED_TREES = (
    "tests/fitness",
    "scripts/context",
    ".grok/hooks",
)

PINNED_FILES = (
    ".claude/settings.json",
    ".github/CODEOWNERS",
    ".github/workflows/fitness.yml",
    ".pre-commit-config.yaml",
    "AGENTS.md",
    "CLAUDE.md",
    "pyproject.toml",
    "scripts/bless",
    "scripts/guardpin.py",
    "scripts/mutate",
    "scripts/mutate_status.py",
    "scripts/secrets",
    "scripts/verify",
)

_LEDGER_FIELDS = {"at", "artefact", "note", "paths", "verdict"}


class Verdict(str, Enum):
    caught = "caught"
    routine = "routine"


class UnnamedDriftError(RuntimeError):
    """A bless found a pinned path that moved and was not named."""


class BlessError(RuntimeError):
    """A bless or a ledger line that does not say what it is."""


def _skip(path: Path) -> bool:
    if path.name in _EXCLUDED_NAMES:
        return True
    return any(part in _EXCLUDED_PARTS for part in path.parts)


def protected_files(repo: Path = REPO) -> list[str]:
    found: set[str] = set()
    for tree in PINNED_TREES:
        root = repo / tree
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and not _skip(path):
                found.add(path.relative_to(repo).as_posix())
    for rel in PINNED_FILES:
        if (repo / rel).is_file():
            found.add(rel)
    return sorted(found)


def manifest_key(path: str | Path, repo: Path = REPO) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = repo / candidate
    try:
        return candidate.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError as exc:
        raise BlessError(f"{path} is outside the repository") from exc


def is_protected(path: str | Path, repo: Path = REPO) -> bool:
    try:
        key = manifest_key(path, repo)
    except BlessError:
        return False
    if key in _UNHASHED:
        return True
    if _skip(Path(key)):
        return False
    if key in PINNED_FILES:
        return True
    return any(key == tree or key.startswith(f"{tree}/") for tree in PINNED_TREES)


def compute_hashes(repo: Path = REPO) -> dict[str, str]:
    return {rel: hashlib.sha256((repo / rel).read_bytes()).hexdigest() for rel in protected_files(repo)}


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8"))


def drifted(recorded: dict[str, str], fresh: dict[str, str]) -> list[str]:
    keys = set(recorded) | set(fresh)
    return sorted(key for key in keys if recorded.get(key) != fresh.get(key))


def write_manifest(
    only: Sequence[str],
    repo: Path = REPO,
    manifest: Path = MANIFEST_PATH,
) -> list[str]:
    if not only:
        raise BlessError("name each path this bless is allowed to move")
    fresh = compute_hashes(repo)
    moved = drifted(load_manifest(manifest), fresh) if manifest.is_file() else sorted(fresh)
    named = {manifest_key(path, repo) for path in only}
    unnamed = [key for key in moved if key not in named]
    if unnamed:
        raise UnnamedDriftError(
            f"{len(unnamed)} pinned path(s) moved and were not named: {unnamed}. Name them too, or set them aside."
        )
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(fresh, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return moved


def init_manifest(repo: Path = REPO, manifest: Path = MANIFEST_PATH) -> list[str]:
    if manifest.is_file():
        raise BlessError("the manifest already exists; name the paths")
    fresh = compute_hashes(repo)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(fresh, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sorted(fresh)


def record(
    verdict: Verdict,
    paths: Sequence[str],
    note: str = "",
    ledger: Path = LEDGER_PATH,
) -> None:
    if not isinstance(verdict, Verdict):
        raise BlessError("verdict must be caught or routine")
    entry = {
        "artefact": "guard_manifest",
        "at": datetime.now(UTC).isoformat(),
        "note": note,
        "paths": sorted(paths),
        "verdict": verdict.value,
    }
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def entries(ledger: Path = LEDGER_PATH) -> list[dict[str, object]]:
    if not ledger.is_file():
        return []
    parsed: list[dict[str, object]] = []
    for number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            parsed.append(_entry(line, number))
    return parsed


def _entry(line: str, number: int) -> dict[str, object]:
    try:
        entry = json.loads(line)
    except ValueError as broken:
        raise BlessError(f"line {number} is not JSON") from broken
    if not isinstance(entry, dict) or not _LEDGER_FIELDS <= set(entry):
        raise BlessError(f"line {number} is missing a field")
    if entry["verdict"] not in {member.value for member in Verdict}:
        raise BlessError(f"line {number} has verdict {entry['verdict']!r}")
    return entry


def render_tally(ledger: Path = LEDGER_PATH) -> str:
    counts = {member.value: 0 for member in Verdict}
    for entry in entries(ledger):
        if not entry:
            continue
        counts[str(entry["verdict"])] += 1
    return f"caught {counts['caught']}\nroutine {counts['routine']}"
