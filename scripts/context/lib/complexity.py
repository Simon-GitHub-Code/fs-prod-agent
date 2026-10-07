"""Cyclomatic counter. The ratchet and the hotspot table both call this."""

import ast
from pathlib import Path

CAP = 10

# Decision tables. Their branches are the policy. Growing one is a visible edit here.
GRANDFATHERED = {
    "decisions/contract.py::validate_decision": 18,
    "policy/authorize.py::authorize": 16,
}


def function_scores(root: Path) -> dict[str, int]:
    scores: dict[str, int] = {}
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        scores.update(scores_in(relative, path.read_text(encoding="utf-8")))
    return scores


def scores_in(relative: str, source: str) -> dict[str, int]:
    tree = ast.parse(source)
    scores: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scores[f"{relative}::{node.name}"] = cyclomatic(node)
    return scores


def cyclomatic(function: ast.AST) -> int:
    score = 1
    for node in _body(function):
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.With)):
            score += 1
        elif isinstance(node, ast.BoolOp):
            score += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            score += 1 + len(node.ifs)
        elif isinstance(node, ast.Match):
            score += max(len(node.cases) - 1, 0)
    return score


def _body(function: ast.AST):
    stack = list(ast.iter_child_nodes(function))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))
