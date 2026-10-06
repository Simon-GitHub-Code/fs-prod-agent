"""Import-boundary collectors. The fitness tests assert these lists are empty."""

import ast
from pathlib import Path

from scripts.context.lib.imports import imported_modules, python_files
from scripts.context.lib.paths import SRC

_OUTER = (
    "fs_prod_agent.application",
    "fs_prod_agent.adapters",
    "fs_prod_agent.agents",
    "fs_prod_agent.workflows",
    "fs_prod_agent.mcp_servers",
    "fs_prod_agent.observe",
)
_DECISION_PORT = "fs_prod_agent.ports"
_ALLOWED_STRANDS = Path("adapters/local/agent_strands.py")
_ALLOWED_DECIDER = Path("adapters/local/decision_decider.py")
_ALLOWED_LANGGRAPH = Path("adapters/local/workflow_langgraph.py")

_COLLECTORS = (
    "violations_core_packages",
    "violations_policy_ports",
    "violations_application",
    "violations_adapter_imports",
    "violations_aws_branch",
    "violations_sdk_sites",
    "violations_mcp",
    "violations_evals_observe",
    "violations_decisions_evals",
    "violations_domain_workflows",
)


def violations_core_packages(root: Path = SRC) -> list[str]:
    violations: list[str] = []
    for path in _under("domain", "decisions", "policy", root=root):
        for module in imported_modules(path, root):
            if _matches(module, _OUTER) is not None:
                violations.append(f"{_rel(path, root)} imports {module}")
    return violations


def violations_policy_ports(root: Path = SRC) -> list[str]:
    return banned_imports("policy", "decisions", banned=(_DECISION_PORT,), root=root)


def violations_application(root: Path = SRC) -> list[str]:
    violations: list[str] = []
    for path in _under("application", root=root):
        for module in imported_modules(path, root):
            adapters = ("fs_prod_agent.adapters", "fs_prod_agent.mcp_servers")
            if _matches(module, adapters) is not None or _is_framework(module):
                violations.append(f"{_rel(path, root)} imports {module}")
    return violations


def violations_adapter_imports(root: Path = SRC) -> list[str]:
    violations: list[str] = []
    for path in python_files(root):
        if path.name == "composition.py" and path.parent == root:
            continue
        if _is_under(path, "adapters", root):
            continue
        for module in imported_modules(path, root):
            if _matches(module, ("fs_prod_agent.adapters",)) is not None:
                violations.append(f"{_rel(path, root)} imports {module}")
    return violations


def violations_aws_branch(root: Path = SRC) -> list[str]:
    composition = root / "composition.py"
    tree = ast.parse(composition.read_text(encoding="utf-8"), filename=str(composition))
    parent_of = parent_map(tree)
    violations: list[str] = []
    for node in ast.walk(tree):
        for module in import_modules(node):
            if not _is_aws_adapter(module):
                continue
            if not inside_aws_check(node, parent_of):
                violations.append(f"composition.py imports {module} outside if profile == 'aws'")
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_build_local":
            for child in ast.walk(node):
                for module in import_modules(child):
                    if _is_aws_adapter(module):
                        violations.append(f"_build_local imports {module}")
    for path in python_files(root):
        if path == composition or _is_under(path, "adapters/aws", root):
            continue
        for module in imported_modules(path, root):
            if _is_aws_adapter(module):
                violations.append(f"{_rel(path, root)} imports {module}")
    return violations


def violations_sdk_sites(root: Path = SRC) -> list[str]:
    violations: list[str] = []
    for path in python_files(root):
        relative = path.relative_to(root)
        for module in imported_modules(path, root):
            if _is_strands_sdk(module) and relative != _ALLOWED_STRANDS:
                violations.append(f"{relative.as_posix()} imports {module}")
            if _is_decider(module) and relative != _ALLOWED_DECIDER:
                violations.append(f"{relative.as_posix()} imports {module}")
            if _is_langgraph(module) and relative != _ALLOWED_LANGGRAPH:
                violations.append(f"{relative.as_posix()} imports {module}")
            if _is_aws_sdk(module) and not _is_under(path, "adapters/aws", root):
                violations.append(f"{relative.as_posix()} imports {module}")
    return violations


def violations_mcp(root: Path = SRC) -> list[str]:
    return banned_imports(
        "mcp_servers",
        banned=("fs_prod_agent.application", "fs_prod_agent.agents"),
        root=root,
    )


def violations_evals_observe(root: Path = SRC) -> list[str]:
    return banned_imports("evals", "observe", banned=(_DECISION_PORT,), root=root)


def violations_decisions_evals(root: Path = SRC) -> list[str]:
    return banned_imports("decisions", banned=("fs_prod_agent.evals",), root=root)


def violations_domain_workflows(root: Path = SRC) -> list[str]:
    return banned_imports(
        "domain",
        "workflows",
        banned=(_DECISION_PORT, "fs_prod_agent.decisions"),
        root=root,
    )


def all_violations(root: Path = SRC) -> list[str]:
    found: list[str] = []
    namespace = globals()
    for name in _COLLECTORS:
        found.extend(namespace[name](root))
    return found


def violations_touching(path: Path, root: Path = SRC) -> list[str]:
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    hits: list[str] = []
    for item in all_violations(root):
        if item.startswith(relative + " "):
            hits.append(item)
        elif relative == "composition.py" and item.startswith("_build_local "):
            hits.append(item)
    return hits


def banned_imports(*packages: str, banned: tuple[str, ...], root: Path = SRC) -> list[str]:
    violations: list[str] = []
    for path in _under(*packages, root=root):
        for module in imported_modules(path, root):
            if _matches(module, banned) is not None:
                violations.append(f"{_rel(path, root)} imports {module}")
    return violations


def parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def inside_aws_check(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    current: ast.AST | None = node
    while current is not None:
        current = parents.get(current)
        if isinstance(current, ast.If) and _compares_equal_aws(current.test):
            return True
    return False


def import_modules(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
        return [node.module]
    return []


def _under(*packages: str, root: Path = SRC) -> list[Path]:
    return [path for path in python_files(root) if _top(path, root) in packages]


def _top(path: Path, root: Path) -> str:
    return path.relative_to(root).parts[0]


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_under(path: Path, prefix: str, root: Path) -> bool:
    relative = path.relative_to(root).as_posix()
    return relative.startswith(prefix.rstrip("/") + "/") or relative == prefix


def _matches(module: str, banned: tuple[str, ...]) -> str | None:
    for item in banned:
        if module == item or module.startswith(item + "."):
            return item
    return None


def _is_framework(module: str) -> bool:
    return _is_strands_sdk(module) or _is_decider(module) or _is_langgraph(module) or _is_aws_sdk(module)


def _is_strands_sdk(module: str) -> bool:
    return module.split(".")[0] == "strands"


def _is_decider(module: str) -> bool:
    return module.split(".")[0] == "strands_decider"


def _is_langgraph(module: str) -> bool:
    root = module.split(".")[0]
    return root == "langgraph" or root.startswith("langchain")


def _is_aws_sdk(module: str) -> bool:
    root = module.split(".")[0]
    return root in {"boto3", "botocore"} or "bedrock" in root


def _is_aws_adapter(module: str) -> bool:
    return module == "fs_prod_agent.adapters.aws" or module.startswith("fs_prod_agent.adapters.aws.")


def _compares_equal_aws(test: ast.AST) -> bool:
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or len(test.comparators) != 1:
        return False
    if not isinstance(test.ops[0], ast.Eq):
        return False
    comparator = test.comparators[0]
    return isinstance(comparator, ast.Constant) and comparator.value == "aws"
