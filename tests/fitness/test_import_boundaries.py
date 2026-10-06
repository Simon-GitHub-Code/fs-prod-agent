"""Import boundaries, read from import statements. Comments and strings do not count."""

import ast
from pathlib import Path

from scripts.context.lib.boundaries import (
    banned_imports,
    import_modules,
    inside_aws_check,
    parent_map,
    violations_adapter_imports,
    violations_application,
    violations_aws_branch,
    violations_core_packages,
    violations_decisions_evals,
    violations_domain_workflows,
    violations_evals_observe,
    violations_mcp,
    violations_policy_ports,
    violations_sdk_sites,
)


def test_core_packages_stay_inside_the_decision_layer():
    violations = violations_core_packages()
    assert not violations, "\n".join(violations)


def test_policy_and_decisions_do_not_import_io_ports():
    violations = violations_policy_ports()
    assert not violations, "\n".join(violations)


def test_application_does_not_import_adapters_or_frameworks():
    violations = violations_application()
    assert not violations, "\n".join(violations)


def test_only_composition_imports_adapters():
    violations = violations_adapter_imports()
    assert not violations, "\n".join(violations)


def test_aws_adapter_import_is_only_the_aws_branch():
    violations = violations_aws_branch()
    assert not violations, "\n".join(violations)


def test_third_party_sdks_have_one_import_site():
    violations = violations_sdk_sites()
    assert not violations, "\n".join(violations)


def test_mcp_servers_do_not_import_application_or_agents():
    violations = violations_mcp()
    assert not violations, "\n".join(violations)


def test_evals_and_observe_do_not_import_the_decision_port():
    violations = violations_evals_observe()
    assert not violations, "\n".join(violations)


def test_decisions_do_not_import_eval_metrics():
    violations = violations_decisions_evals()
    assert not violations, "\n".join(violations)


def test_domain_and_workflows_do_not_call_the_decider():
    violations = violations_domain_workflows()
    assert not violations, "\n".join(violations)


def test_a_domain_file_that_imports_an_adapter_is_rejected(tmp_path: Path):
    package = tmp_path / "domain"
    package.mkdir()
    (package / "leak.py").write_text("import fs_prod_agent.adapters.local.fakes\n", encoding="utf-8")
    violations = banned_imports("domain", banned=("fs_prod_agent.adapters",), root=tmp_path)
    assert violations == ["domain/leak.py imports fs_prod_agent.adapters.local.fakes"]


def test_a_clean_domain_file_is_not_rejected(tmp_path: Path):
    package = tmp_path / "domain"
    package.mkdir()
    (package / "quiet.py").write_text("from fs_prod_agent.domain.models import Mandate\n", encoding="utf-8")
    assert banned_imports("domain", banned=("fs_prod_agent.adapters",), root=tmp_path) == []


def test_a_module_level_aws_import_sits_outside_the_aws_branch():
    tree = ast.parse("from fs_prod_agent.adapters.aws.profile import build_aws\n")
    node = next(item for item in ast.walk(tree) if isinstance(item, ast.ImportFrom))
    assert import_modules(node) == ["fs_prod_agent.adapters.aws.profile"]
    assert inside_aws_check(node, parent_map(tree)) is False
