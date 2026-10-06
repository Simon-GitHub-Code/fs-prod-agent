"""Spec for the oversight analyst. Tool names are strings. The gateway is the caller."""

AGENT_ID = "oversight_analyst"
PROMPT_ID = "oversight_analyst"
EVAL_SUITE = "oversight_analyst"
TOOL_NAMES = (
    "search_policy",
    "get_holdings",
    "get_manager_report",
    "draft_briefing",
    "submit_committee_paper",
)
