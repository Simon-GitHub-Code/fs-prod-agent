"""The committed pack matches a fresh build."""

import subprocess
import sys

from scripts.context.lib.paths import REPO


def test_committed_pack_matches_a_fresh_build():
    completed = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "context" / "build.py"), "--check"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
