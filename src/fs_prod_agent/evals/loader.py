"""Load eval cases. A case without an expected policy verdict is not a case."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from fs_prod_agent.domain.models import Effect, Principal, Role


class EvalCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    stage: Literal["ingress", "tool"]
    request: str
    principal: Principal
    tool_name: str | None = None
    effect: Effect | None = None
    expected_verdict: str
    expected_route: str | None = None
    expected_workflow_id: str | None = None


def load_cases(directory: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    paths = sorted(path for path in directory.glob("*.json"))
    if not paths:
        raise ValueError(f"no eval cases in {directory}")
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        cases.append(_case_from(data, path))
    return cases


def case_from_mapping(data: dict, source: str = "<memory>") -> EvalCase:
    return _case_from(data, source)


def _case_from(data: dict, source: Path | str) -> EvalCase:
    expected = data.get("expected")
    if not isinstance(expected, dict) or "verdict" not in expected:
        raise ValueError(f"{source} has no expected verdict")
    effect = data.get("effect")
    return EvalCase(
        id=data["id"],
        stage=data["stage"],
        request=data["request"],
        principal=Principal(
            actor_id=data["actor_id"],
            role=Role(data["role"]),
            scopes=list(data.get("scopes", [])),
        ),
        tool_name=data.get("tool_name"),
        effect=None if effect is None else Effect(effect),
        expected_verdict=expected["verdict"],
        expected_route=expected.get("route"),
        expected_workflow_id=expected.get("workflow_id"),
    )
