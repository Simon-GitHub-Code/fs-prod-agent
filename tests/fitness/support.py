"""Shared paths and import walking for the fitness suite."""

from pathlib import Path

from scripts.context.lib.imports import imported_modules as _imported_modules
from scripts.context.lib.imports import python_files as _python_files
from scripts.context.lib.paths import REPO as REPO
from scripts.context.lib.paths import SRC as SRC


def python_files(root: Path = SRC) -> list[Path]:
    return _python_files(root)


def imported_modules(path: Path, root: Path = SRC) -> list[str]:
    return _imported_modules(path, root)
