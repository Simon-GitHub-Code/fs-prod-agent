"""A bless names every path that moved, and it says whether the failure caught something."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.context.lib.paths import REPO
from scripts.guardpin import (
    BlessError,
    UnnamedDriftError,
    Verdict,
    entries,
    init_manifest,
    is_protected,
    record,
    write_manifest,
)


def test_a_changed_byte_is_refused_until_that_path_is_named(tmp_path: Path):
    guard = _repo(tmp_path)
    init_manifest(tmp_path, tmp_path / "manifest.json")
    guard.write_text("changed\n", encoding="utf-8")
    with pytest.raises(UnnamedDriftError):
        write_manifest(["scripts/verify"], tmp_path, tmp_path / "manifest.json")
    moved = write_manifest(["tests/fitness/test_one.py"], tmp_path, tmp_path / "manifest.json")
    assert moved == ["tests/fitness/test_one.py"]


def test_two_moves_are_refused_when_only_one_is_named(tmp_path: Path):
    _repo(tmp_path)
    init_manifest(tmp_path, tmp_path / "manifest.json")
    (tmp_path / "tests" / "fitness" / "test_one.py").write_text("one\n", encoding="utf-8")
    (tmp_path / "scripts" / "verify").write_text("two\n", encoding="utf-8")
    with pytest.raises(UnnamedDriftError):
        write_manifest(["tests/fitness/test_one.py"], tmp_path, tmp_path / "manifest.json")


def test_a_bless_with_no_paths_is_refused(tmp_path: Path):
    with pytest.raises(BlessError):
        write_manifest([], tmp_path, tmp_path / "manifest.json")


def test_init_refuses_once_a_manifest_exists(tmp_path: Path):
    _repo(tmp_path)
    init_manifest(tmp_path, tmp_path / "manifest.json")
    with pytest.raises(BlessError):
        init_manifest(tmp_path, tmp_path / "manifest.json")


def test_a_ledger_line_must_carry_a_known_verdict(tmp_path: Path):
    ledger = tmp_path / "ledger.jsonl"
    record(Verdict.caught, ["tests/fitness/test_one.py"], "boundary was wrong", ledger)
    assert entries(ledger)[0]["verdict"] == "caught"
    ledger.write_text(json.dumps({"verdict": "whatever"}) + "\n", encoding="utf-8")
    with pytest.raises(BlessError):
        entries(ledger)


def test_the_manifest_itself_is_a_protected_write_and_product_code_is_not():
    assert is_protected("tests/fitness/_guard_manifest.json")
    assert is_protected("tests/fitness/_bless_ledger.jsonl")
    assert is_protected("tests/fitness/test_policy.py")
    assert is_protected("tests/unit/test_policy.py") is False
    assert is_protected("tests/integration/test_router.py") is False
    assert is_protected("src/fs_prod_agent/domain/oversight.py") is False


def test_the_cli_refuses_a_bless_that_does_not_say_what_it_was_worth():
    script = [sys.executable, str(REPO / "scripts" / "bless")]
    missing_verdict = subprocess.run([*script, "tests/fitness/test_policy.py"], capture_output=True, text=True)
    assert missing_verdict.returncode == 2
    assert "pass --caught or --routine" in missing_verdict.stderr
    missing_paths = subprocess.run([*script, "--routine"], capture_output=True, text=True)
    assert missing_paths.returncode == 2


def _repo(tmp_path: Path) -> Path:
    guard = tmp_path / "tests" / "fitness" / "test_one.py"
    guard.parent.mkdir(parents=True)
    guard.write_text("original\n", encoding="utf-8")
    verify = tmp_path / "scripts" / "verify"
    verify.parent.mkdir()
    verify.write_text("verify\n", encoding="utf-8")
    return guard
