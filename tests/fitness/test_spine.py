"""One dispatcher starts a runner. Ports, domain fields, and workflow steps stay in use."""

from pathlib import Path

from scripts.context.lib.pack import build_files, report_for
from scripts.context.lib.spine import (
    ALLOWED_RUNNERS,
    all_spine,
    object_collaborators,
    runner_drift,
    runner_sites,
    step_gaps,
    unread_fields,
    unread_services,
    unused_domain_types,
    unused_ports,
    workflow_id_mentions,
)
from tests.fitness.support import SRC

_WALKS = (
    "class FixtureWorkflowRunner:\n"
    "    def run(self, workflow_id, state):\n"
    "        step = None\n"
    "        for name in ('load_holdings',):\n"
    "            STEP_TABLE[name](step)\n"
    "        return ''\n"
)

_PASTES = (
    "class FixtureWorkflowRunner:\n"
    "    def run(self, workflow_id, state):\n"
    "        steps = ','.join(['load_holdings'])\n"
    "        for name in ('load_holdings',):\n"
    "            STEP_TABLE[name](None)\n"
    "        return steps\n"
)


def test_the_live_spine_is_one_route_branch():
    files = build_files()
    assert sorted(runner_sites(SRC)) == sorted(ALLOWED_RUNNERS)
    assert all_spine() == []
    assert "Spine collectors report clean." in files["index.md"]
    assert "Boundary collectors report clean." in files["index.md"]


def test_a_second_dispatcher_is_rejected(tmp_path: Path):
    application = tmp_path / "application"
    application.mkdir()
    (application / "router.py").write_text(
        "def dispatch_route(workflow):\n    workflow.run()\n",
        encoding="utf-8",
    )
    assert runner_drift(tmp_path) == ["application/router.py: dispatch_route calls workflow.run"]


def test_a_workflow_id_literal_in_application_code_is_rejected(tmp_path: Path):
    application = tmp_path / "application"
    application.mkdir()
    (application / "hardcoded.py").write_text('LABEL = "mandate_check"\n', encoding="utf-8")
    (application / "registry.py").write_text('LABEL = "performance_pack"\n', encoding="utf-8")
    (application / "note.py").write_text('"""mandate_check stays in the registry."""\n', encoding="utf-8")
    assert workflow_id_mentions(tmp_path) == ["application/hardcoded.py: names workflow mandate_check"]


def test_an_unused_protocol_is_rejected(tmp_path: Path):
    ports = tmp_path / "ports"
    ports.mkdir()
    (ports / "protocols.py").write_text(
        "from typing import Protocol\n\n"
        "class MemoryPort(Protocol):\n"
        "    def append_turn(self) -> None: ...\n\n"
        "class Idle(Protocol):\n"
        "    def ping(self) -> None: ...\n",
        encoding="utf-8",
    )
    (ports / "__init__.py").write_text("from ports.protocols import Idle, MemoryPort\n", encoding="utf-8")
    (tmp_path / "composition.py").write_text("class App:\n    memory: MemoryPort\n", encoding="utf-8")
    assert unused_ports(tmp_path) == ["ports/protocols.py: Protocol Idle has no caller"]


def test_an_unread_services_field_is_rejected(tmp_path: Path):
    application = tmp_path / "application"
    application.mkdir()
    (application / "pipeline.py").write_text(
        "class Services:\n"
        "    decision: object\n"
        "    model: object\n\n"
        "class Pipeline:\n"
        "    def run(self):\n"
        "        return self.services.decision\n",
        encoding="utf-8",
    )
    assert unread_services(tmp_path) == ["application/pipeline.py: Services field model is never read"]


def test_an_object_collaborator_is_rejected(tmp_path: Path):
    ports = tmp_path / "ports"
    ports.mkdir()
    (ports / "protocols.py").write_text(
        "from typing import Protocol\n\nclass MemoryPort(Protocol):\n    def append_turn(self) -> None: ...\n",
        encoding="utf-8",
    )
    (tmp_path / "composition.py").write_text(
        "class App:\n    profile: str\n    pipeline: Pipeline\n    memory: object\n    trace: MemoryPort\n",
        encoding="utf-8",
    )
    assert object_collaborators(tmp_path) == ["composition.py: App field memory is object"]


def test_an_unused_domain_type_is_rejected(tmp_path: Path):
    domain = tmp_path / "domain"
    domain.mkdir()
    (domain / "models.py").write_text(
        "from pydantic import BaseModel\n\n"
        "class Mandate(BaseModel):\n"
        "    name: str\n\n"
        "class Proposal(BaseModel):\n"
        "    title: str\n",
        encoding="utf-8",
    )
    (domain / "__init__.py").write_text("from domain.models import Mandate, Proposal\n", encoding="utf-8")
    (tmp_path / "books.py").write_text("Mandate(name='fund')\n", encoding="utf-8")
    assert unused_domain_types(tmp_path) == ["domain/models.py: Proposal has no caller"]


def test_an_unread_domain_field_is_rejected(tmp_path: Path):
    domain = tmp_path / "domain"
    domain.mkdir()
    (domain / "models.py").write_text(
        "from pydantic import BaseModel\n\nclass Mandate(BaseModel):\n    name: str\n    exclusions: tuple\n",
        encoding="utf-8",
    )
    (tmp_path / "books.py").write_text("Mandate(name='fund')\n", encoding="utf-8")
    assert unread_fields(tmp_path) == ["domain/models.py: Mandate field exclusions is unread"]


def test_a_step_missing_from_the_table_is_rejected():
    gaps = step_gaps({"render_briefing"}, {"unused_step"}, _WALKS)
    assert gaps == [
        "adapters/local/fakes.py: step render_briefing missing from STEP_TABLE",
        "adapters/local/fakes.py: STEP_TABLE has unregistered step unused_step",
    ]


def test_a_runner_that_pastes_step_names_is_rejected():
    gaps = step_gaps({"load_holdings"}, {"load_holdings"}, _PASTES)
    assert gaps == ["adapters/local/fakes.py: FixtureWorkflowRunner.run pastes step names"]


def test_the_layer_report_names_a_clean_spine():
    report = report_for(SRC / "application" / "pipeline.py")
    assert report is not None
    assert "spine:\n  clean\n" in report
