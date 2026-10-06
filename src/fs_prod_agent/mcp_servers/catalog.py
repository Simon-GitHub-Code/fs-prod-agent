"""Tool manifests. Effect is a property of the tool, not of the agent that names it."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

EffectName = Literal["read", "draft", "mutate"]


class ToolManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    effect: EffectName
    description: str
    server: str


MANIFESTS: tuple[ToolManifest, ...] = (
    ToolManifest(
        name="search_policy",
        effect="read",
        description="Search investment policy and strategic asset allocation text.",
        server="policy_docs",
    ),
    ToolManifest(
        name="get_holdings",
        effect="read",
        description="Read a point-in-time holdings snapshot for the total fund.",
        server="holdings",
    ),
    ToolManifest(
        name="get_manager_report",
        effect="read",
        description="Read an external manager's latest commentary and watchlist flag.",
        server="manager_reports",
    ),
    ToolManifest(
        name="draft_briefing",
        effect="draft",
        description="Draft an internal briefing. It is not sent anywhere.",
        server="committee",
    ),
    ToolManifest(
        name="submit_committee_paper",
        effect="mutate",
        description="Queue a paper for the investment committee. A person must release it.",
        server="committee",
    ),
)


def manifest_for(name: str) -> ToolManifest:
    for manifest in MANIFESTS:
        if manifest.name == name:
            return manifest
    raise KeyError(name)
