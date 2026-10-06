"""Fitness modules and the invariant each module docstring states."""

import ast

from scripts.context.lib.paths import FITNESS


def guard_rows() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for path in sorted(FITNESS.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        summary = _first_line(ast.get_docstring(tree) or "")
        names = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
        ]
        relative = path.relative_to(FITNESS.parents[1]).as_posix()
        rows.append((relative, summary, ",".join(names)))
    return rows


def _first_line(text: str) -> str:
    line = text.strip().splitlines()[0] if text.strip() else ""
    return line.strip()
