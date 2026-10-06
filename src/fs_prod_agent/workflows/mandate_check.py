"""Holdings versus IPS ranges. Breach math is domain.oversight. Materiality is asked afterwards."""

WORKFLOW_ID = "mandate_check"
EVAL_SUITE = "mandate_check"
FOLLOW_UP = "materiality"
TOOL_NAMES = ("get_holdings", "search_policy")
STEPS = (
    "load_holdings",
    "load_mandate",
    "compute_range_breaches",
)
