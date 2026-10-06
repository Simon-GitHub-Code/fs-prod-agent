"""Collectors for the one route branch, used ports, and steps the runner calls."""

import ast
from pathlib import Path

from scripts.context.lib.imports import python_files
from scripts.context.lib.paths import SRC

ALLOWED_RUNNERS = (
    "application/pipeline.py::run calls agent.run",
    "application/pipeline.py::_run_workflow calls workflow.run",
)
_RUNNER_NAMES = frozenset({"agent", "workflow"})
_SKIP_PORTS = frozenset({"ports/protocols.py", "ports/__init__.py"})
_SKIP_DOMAIN = frozenset({"domain/models.py", "domain/__init__.py"})


def runner_sites(root: Path) -> list[str]:
    sites: list[str] = []
    for path in python_files(root):
        relative = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            sites.extend(_run_sites(relative, node))
    return sites


def runner_drift(root: Path = SRC) -> list[str]:
    found = set(runner_sites(root))
    violations = [_extra_runner(site) for site in sorted(found) if site not in ALLOWED_RUNNERS]
    if root.resolve() == SRC.resolve():
        violations.extend(_missing_runner(site) for site in ALLOWED_RUNNERS if site not in found)
    return violations


def workflow_id_mentions(root: Path = SRC) -> list[str]:
    application = root / "application"
    if not application.is_dir():
        return []
    ids = _registered_ids()
    violations: list[str] = []
    for path in python_files(application):
        if path.name == "registry.py":
            continue
        violations.extend(_id_literals(path, root, ids))
    return violations


def unused_ports(root: Path = SRC) -> list[str]:
    path = root / "ports" / "protocols.py"
    if not path.is_file():
        return []
    mentioned = _mentioned_names(root, _SKIP_PORTS)
    return [
        f"ports/protocols.py: Protocol {name} has no caller"
        for name in _class_names(path, {"Protocol"})
        if name not in mentioned
    ]


def unread_services(root: Path = SRC) -> list[str]:
    path = root / "application" / "pipeline.py"
    if not path.is_file():
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    services = _class_def(tree, "Services")
    if services is None:
        return []
    used = _service_loads(tree)
    return [
        f"application/pipeline.py: Services field {name} is never read"
        for name, _annotation in _fields(services)
        if name not in used
    ]


def object_collaborators(root: Path = SRC) -> list[str]:
    composition = root / "composition.py"
    if not composition.is_file():
        return []
    tree = ast.parse(composition.read_text(encoding="utf-8"), filename=str(composition))
    app = _class_def(tree, "App")
    if app is None:
        return []
    protocols = set(_class_names(root / "ports" / "protocols.py", {"Protocol"}))
    violations: list[str] = []
    for field, annotation in _fields(app):
        if field in {"pipeline", "profile"}:
            continue
        if isinstance(annotation, ast.Name) and annotation.id in protocols:
            continue
        violations.append(f"composition.py: App field {field} is {_annotation_label(annotation)}")
    return violations


def unused_domain_types(root: Path = SRC) -> list[str]:
    path = root / "domain" / "models.py"
    if not path.is_file():
        return []
    mentioned = _mentioned_names(root, _SKIP_DOMAIN)
    return [
        f"domain/models.py: {name} has no caller"
        for name in _class_names(path, {"BaseModel", "Enum"})
        if name not in mentioned
    ]


def unread_fields(root: Path = SRC) -> list[str]:
    path = root / "domain" / "models.py"
    if not path.is_file():
        return []
    used = _mentioned_attrs(root, {"domain/models.py"})
    violations: list[str] = []
    for class_name, fields in _model_fields(path):
        for field in fields:
            if field not in used:
                violations.append(f"domain/models.py: {class_name} field {field} is unread")
    return violations


def step_gaps(declared: set[str], table: set[str], runner_source: str) -> list[str]:
    gaps = [f"adapters/local/fakes.py: step {name} missing from STEP_TABLE" for name in sorted(declared - table)]
    gaps.extend(
        f"adapters/local/fakes.py: STEP_TABLE has unregistered step {name}" for name in sorted(table - declared)
    )
    gaps.extend(_runner_gaps(runner_source))
    return gaps


def step_violations(root: Path = SRC) -> list[str]:
    if root.resolve() != SRC.resolve():
        return []
    from fs_prod_agent.adapters.local.fakes import STEP_TABLE
    from fs_prod_agent.application.registry import workflows

    declared = {step for spec in workflows() for step in spec.steps}
    source = (SRC / "adapters" / "local" / "fakes.py").read_text(encoding="utf-8")
    return step_gaps(declared, set(STEP_TABLE), source)


def all_spine(root: Path = SRC) -> list[str]:
    return [
        *runner_drift(root),
        *workflow_id_mentions(root),
        *unused_ports(root),
        *unread_services(root),
        *object_collaborators(root),
        *unused_domain_types(root),
        *unread_fields(root),
        *step_violations(root),
    ]


def spine_touching(path: Path) -> list[str]:
    try:
        relative = path.resolve().relative_to(SRC.resolve()).as_posix()
    except ValueError:
        return []
    details: list[str] = []
    for item in all_spine():
        prefix, separator, detail = item.partition(": ")
        if separator and prefix == relative:
            details.append(detail)
    return details


def _run_sites(relative: str, function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    sites: list[str] = []
    for call in _owned_calls(function):
        receiver = _run_receiver(call)
        if receiver is not None:
            sites.append(f"{relative}::{function.name} calls {receiver}.run")
    return sites


def _owned_calls(function: ast.AST) -> list[ast.Call]:
    found: list[ast.Call] = []
    stack = list(ast.iter_child_nodes(function))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        if isinstance(node, ast.Call):
            found.append(node)
        stack.extend(ast.iter_child_nodes(node))
    return found


def _run_receiver(call: ast.Call) -> str | None:
    func = call.func
    if not isinstance(func, ast.Attribute) or func.attr != "run":
        return None
    receiver = func.value
    if isinstance(receiver, ast.Name) and receiver.id in _RUNNER_NAMES:
        return receiver.id
    if isinstance(receiver, ast.Attribute) and receiver.attr in _RUNNER_NAMES:
        return receiver.attr
    return None


def _extra_runner(site: str) -> str:
    path, _, rest = site.partition("::")
    return f"{path}: {rest}"


def _missing_runner(site: str) -> str:
    path, _, _rest = site.partition("::")
    return f"{path}: missing {site}"


def _registered_ids() -> set[str]:
    from fs_prod_agent.application.registry import agents, workflows

    return {spec.id for spec in (*workflows(), *agents())}


def _id_literals(path: Path, root: Path, ids: set[str]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docs = _docstring_nodes(tree)
    relative = path.relative_to(root).as_posix()
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node not in docs and node.value in ids:
            hits.append(f"{relative}: names workflow {node.value}")
    return hits


def _docstring_nodes(tree: ast.AST) -> set[ast.AST]:
    found: set[ast.AST] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        found.update(_docstring_of(node))
    return found


def _docstring_of(node: ast.AST) -> set[ast.AST]:
    body = getattr(node, "body", [])
    if not body or not isinstance(body[0], ast.Expr):
        return set()
    value = body[0].value
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return {value}
    return set()


def _mentioned_names(root: Path, skip: frozenset[str]) -> set[str]:
    found: set[str] = set()
    for path in python_files(root):
        if path.relative_to(root).as_posix() in skip:
            continue
        found.update(_names_in(path))
    return found


def _names_in(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.alias) and isinstance(node.name, str):
            found.add(node.name)
            if node.asname:
                found.add(node.asname)
    return found


def _mentioned_attrs(root: Path, skip: set[str]) -> set[str]:
    found: set[str] = set()
    for path in python_files(root):
        if path.relative_to(root).as_posix() in skip:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                found.add(node.attr)
            elif isinstance(node, ast.keyword) and node.arg:
                found.add(node.arg)
    return found


def _class_names(path: Path, bases: set[str]) -> list[str]:
    if not path.is_file():
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef) and _base_names(node) & bases]


def _base_names(node: ast.ClassDef) -> set[str]:
    found: set[str] = set()
    for base in node.bases:
        if isinstance(base, ast.Name):
            found.add(base.id)
        elif isinstance(base, ast.Attribute):
            found.add(base.attr)
    return found


def _class_def(tree: ast.AST, name: str) -> ast.ClassDef | None:
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def _fields(node: ast.ClassDef) -> list[tuple[str, ast.expr]]:
    fields: list[tuple[str, ast.expr]] = []
    for child in node.body:
        if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            fields.append((child.target.id, child.annotation))
    return fields


def _model_fields(path: Path) -> list[tuple[str, list[str]]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    models: list[tuple[str, list[str]]] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and "BaseModel" in _base_names(node):
            models.append((node.name, [field for field, _annotation in _fields(node)]))
    return models


def _service_loads(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        value = node.value
        if isinstance(value, ast.Attribute) and value.attr == "services":
            found.add(node.attr)
    return found


def _annotation_label(annotation: ast.expr) -> str:
    if isinstance(annotation, ast.Name):
        return annotation.id
    return ast.unparse(annotation)


def _runner_function(tree: ast.AST) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "FixtureWorkflowRunner":
            continue
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == "run":
                return child
    return None


def _walks(function: ast.AST) -> bool:
    return any(isinstance(node, ast.For) for node in ast.walk(function))


def _calls_step_table(function: ast.AST) -> bool:
    for node in ast.walk(function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Subscript):
            continue
        value = node.func.value
        if isinstance(value, ast.Name) and value.id == "STEP_TABLE":
            return True
    return False


def _calls_join(function: ast.AST) -> bool:
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "join":
            return True
    return False


def _runner_gaps(source: str) -> list[str]:
    run = _runner_function(ast.parse(source))
    if run is None or not _walks(run) or not _calls_step_table(run):
        return ["adapters/local/fakes.py: FixtureWorkflowRunner.run does not walk STEP_TABLE"]
    if _calls_join(run):
        return ["adapters/local/fakes.py: FixtureWorkflowRunner.run pastes step names"]
    return []
