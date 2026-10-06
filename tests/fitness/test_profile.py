"""The local profile is the one that runs. The AWS profile is the unused switch."""

import os
import subprocess
import sys
import tomllib

import pytest

from fs_prod_agent.adapters.aws.profile import AwsProfileUnavailable
from fs_prod_agent.composition import build
from tests.fitness.support import REPO


def test_declared_dependencies_exclude_the_aws_sdk():
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    declared = list(project["dependencies"])
    for extra in project.get("optional-dependencies", {}).values():
        declared.extend(extra)
    text = " ".join(declared).lower()
    for name in ("boto3", "botocore", "bedrock"):
        assert name not in text


def test_local_profile_does_not_import_the_aws_sdk():
    _run(
        """
import sys
from fs_prod_agent.composition import build

def banned(name):
    root = name.split(".")[0]
    return root in {"boto3", "botocore", "bedrock"} or "bedrock" in root

app = build("local")
assert app.profile == "local"
found = [name for name in sys.modules if banned(name) or "adapters.aws" in name]
if found:
    raise SystemExit("unexpected imports: " + ", ".join(sorted(found)))
"""
    )


def test_aws_profile_raises_without_importing_the_aws_sdk():
    with pytest.raises(AwsProfileUnavailable, match="not configured"):
        build("aws")
    _run(
        """
import sys
from fs_prod_agent.composition import build

try:
    build("aws")
except Exception as exc:
    if type(exc).__name__ != "AwsProfileUnavailable" or "not configured" not in str(exc):
        raise
else:
    raise SystemExit("build('aws') returned a profile")

banned = []
for name in sys.modules:
    root = name.split(".")[0]
    if root in {"boto3", "botocore", "bedrock"} or "bedrock" in root:
        banned.append(name)
if banned:
    raise SystemExit("unexpected imports: " + ", ".join(sorted(banned)))
"""
    )


def test_unknown_profile_is_rejected_and_local_is_the_default():
    with pytest.raises(ValueError, match="unknown profile"):
        build("other")
    assert build().profile == "local"


def _run(script: str) -> None:
    env = os.environ.copy()
    src = str(REPO / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
