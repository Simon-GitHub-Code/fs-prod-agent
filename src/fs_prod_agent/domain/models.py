"""Asset-owner types. No I/O and no framework imports."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Role(str, Enum):
    analyst = "analyst"
    cio = "cio"
    committee = "committee"


class Effect(str, Enum):
    read = "read"
    draft = "draft"
    mutate = "mutate"


class Principal(BaseModel):
    model_config = ConfigDict(frozen=True)

    actor_id: str
    role: Role
    scopes: list[str] = Field(default_factory=list)

    def allows(self, tool_name: str) -> bool:
        return tool_name in self.scopes


class Mandate(BaseModel):
    model_config = ConfigDict(frozen=True)

    mandate_id: str
    name: str
    ranges: dict[str, tuple[float, float]] = Field(default_factory=dict)


class PortfolioSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    as_of: str
    holdings: dict[str, float] = Field(default_factory=dict)
    portfolio_return: float | None = None
    benchmark_return: float | None = None


class Briefing(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    body: str
    evidence_ids: list[str] = Field(default_factory=list)


class RangeBreach(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset_class: str
    weight: float
    lower: float
    upper: float


class Action(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_name: str
    effect: Effect
    arguments: dict[str, str] = Field(default_factory=dict)
