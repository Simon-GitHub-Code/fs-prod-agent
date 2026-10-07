"""Pinned tests and quality controls match their recorded hashes."""

from scripts.guardpin import compute_hashes, drifted, load_manifest


def test_pinned_surfaces_match_the_manifest():
    moved = drifted(load_manifest(), compute_hashes())
    assert moved == [], (
        "A pinned test or quality control changed. "
        "scripts/bless records it only when every moved path is named and the verdict is "
        f"--caught or --routine. Moved: {moved}"
    )
