"""Import statements, resolved the same way the boundary guards resolve them."""

import ast
from pathlib import Path


def python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def imported_modules(path: Path, root: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append(resolve_from(path, node, root))
    return modules


def absolute_imports(path: Path) -> list[str]:
    """Level-zero imports. Safe for a file that sits outside the production tree."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.append(node.module)
    return modules


def resolve_from(path: Path, node: ast.ImportFrom, root: Path) -> str:
    module = node.module or ""
    if node.level == 0:
        return module
    parts = package_parts(path, root)
    climb = node.level - 1
    if climb > len(parts):
        return "<relative-out-of-tree>"
    base = parts[: len(parts) - climb] if climb else parts
    if module:
        base = [*base, *module.split(".")]
    return ".".join(base)


def package_parts(path: Path, root: Path) -> list[str]:
    relative = path.relative_to(root)
    return ["fs_prod_agent", *relative.parts[:-1]]


def module_name(path: Path, root: Path) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(["fs_prod_agent", *parts])
