"""Quarterly total-fund pack. The steps are data. The arithmetic is domain.oversight."""

WORKFLOW_ID = "performance_pack"
EVAL_SUITE = "performance_pack"
TOOL_NAMES = ("get_holdings", "search_policy")
STEPS = (
    "load_holdings",
    "compute_return_versus_benchmark",
    "render_briefing",
)
