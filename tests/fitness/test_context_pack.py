"""The committed pack matches a fresh build, and a changed byte does not."""

import subprocess
import sys
from pathlib import Path

from scripts.context.lib.pack import (
    build_files,
    freshness_diff,
    hotspot_rows,
    rules_diff,
    rules_document,
    who_imports,
    write_pack,
)
from scripts.context.lib.paths import REPO, SRC


def test_committed_pack_matches_a_fresh_build():
    completed = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "context" / "build.py"), "--check"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_a_changed_byte_is_stale(tmp_path: Path):
    files = build_files()
    write_pack(tmp_path, files)
    assert freshness_diff(tmp_path, files) == []
    (tmp_path / "index.md").write_text(files["index.md"] + "\n", encoding="utf-8")
    assert "index.md" in freshness_diff(tmp_path, files)


def test_a_changed_rules_file_is_stale(tmp_path: Path):
    files = build_files()
    path = tmp_path / "context-pack.md"
    path.write_text(rules_document(files), encoding="utf-8")
    assert rules_diff(path, files) == []
    path.write_text("hand edit\n", encoding="utf-8")
    assert rules_diff(path, files) == [".grok/rules/context-pack.md"]
    assert rules_diff(tmp_path / "missing.md", files) == ["missing .grok/rules/context-pack.md"]


def test_an_extra_file_is_stale(tmp_path: Path):
    files = build_files()
    write_pack(tmp_path, files)
    (tmp_path / "note.txt").write_text("hand edit\n", encoding="utf-8")
    assert "extra note.txt" in freshness_diff(tmp_path, files)


def test_hotspots_use_the_ratchet_counter():
    scores = {f"{path}::{symbol}": cc for path, symbol, cc, _cap, _headroom in hotspot_rows()}
    assert scores["policy/authorize.py::authorize"] == 16
    assert scores["decisions/contract.py::validate_decision"] == 18


def test_who_imports_names_the_local_runner():
    text = who_imports("fs_prod_agent.domain.oversight", transitive=False)
    assert "src/fs_prod_agent/adapters/local/fakes.py" in text


def test_query_layer_names_the_domain_layer():
    completed = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "context" / "query.py"), "layer", str(SRC / "domain" / "oversight.py")],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "layer: domain" in completed.stdout
    assert "boundary:" in completed.stdout
    assert "clean" in completed.stdout


def test_query_layer_names_the_rules_file_as_the_generated_pack():
    completed = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "context" / "query.py"), "layer", ".grok/rules/context-pack.md"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "layer: generated-pack" in completed.stdout
    assert "owner: scripts/context/build.py" in completed.stdout


def test_query_guards_finds_the_import_boundary():
    completed = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "context" / "query.py"), "guards", "--keyword", "import boundaries"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "tests/fitness/test_import_boundaries.py" in completed.stdout
