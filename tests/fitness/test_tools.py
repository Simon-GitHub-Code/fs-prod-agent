"""Tools are manifest names. Agents and workflows do not carry tool functions."""

import ast
import re

from fs_prod_agent.application.registry import agents, workflows
from fs_prod_agent.mcp_servers.catalog import MANIFESTS
from tests.fitness.support import SRC

_BANNED = re.compile(r"\b(orders?|trades?|payments?|wires?|emails?|send[-_ ]?email)\b", re.IGNORECASE)


def test_spec_tool_names_are_a_subset_of_manifests():
    names = {manifest.name for manifest in MANIFESTS}
    assert names
    for spec in [*workflows(), *agents()]:
        assert spec.tool_names
        assert set(spec.tool_names) <= names


def test_agents_and_workflows_have_no_tool_decorators():
    violations: list[str] = []
    for package in ("agents", "workflows"):
        for path in (SRC / package).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for decorator in node.decorator_list:
                    if _decorator_name(decorator) == "tool":
                        violations.append(f"{path.relative_to(SRC)}:{node.lineno} @{node.name}")
    assert not violations, "\n".join(violations)


def test_manifests_have_no_trading_or_payment_words():
    assert _BANNED.search("strategy") is None
    assert _BANNED.search("strategic asset allocation") is None
    assert trading_violations([(manifest.name, manifest.description) for manifest in MANIFESTS]) == []


def test_an_order_tool_is_rejected():
    violations = trading_violations([("place_order", "Place an order and wire the payment.")])
    assert any("place_order" in item for item in violations)
    assert trading_violations([("search_policy", "Search investment policy text.")]) == []


def trading_violations(texts: list[tuple[str, str]]) -> list[str]:
    violations: list[str] = []
    for name, description in texts:
        for label, text in (("name", name), ("description", description)):
            if _BANNED.search(text):
                violations.append(f"{name} {label}: {text}")
    return violations


def _decorator_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return None
