"""Pinned tests and quality controls match their recorded hashes."""

from scripts.context.lib.paths import REPO
from scripts.guardpin import (
    PINNED_FILES,
    PINNED_TREES,
    compute_hashes,
    drifted,
    entries,
    load_manifest,
    protected_files,
)


def test_pinned_surfaces_match_the_manifest():
    moved = drifted(load_manifest(), compute_hashes())
    assert moved == [], (
        "A pinned test or quality control changed. "
        "scripts/bless records it only when every moved path is named and the verdict is "
        f"--caught or --routine. Moved: {moved}"
    )


def test_the_manifest_and_ledger_are_not_part_of_the_hash():
    names = {path.rsplit("/", 1)[-1] for path in protected_files()}
    assert "_guard_manifest.json" not in names
    assert "_bless_ledger.jsonl" not in names
    assert "tests/fitness/test_guard_integrity.py" in protected_files()


def test_the_ledger_records_a_verdict():
    found = entries()
    assert found
    assert {entry["verdict"] for entry in found} <= {"caught", "routine"}
    assert {entry["artefact"] for entry in found} == {"guard_manifest"}


def test_codeowners_routes_every_pinned_surface():
    text = (REPO / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert "@Simon-GitHub-Code" in text
    for tree in PINNED_TREES:
        assert f"/{tree}/" in text
    for rel in PINNED_FILES:
        assert f"/{rel}" in text
