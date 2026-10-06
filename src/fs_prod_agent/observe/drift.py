"""Compare two windows of decision-chain traces. Pure: no model and no I/O."""

from pydantic import BaseModel, ConfigDict, Field

from fs_prod_agent.observe.decision_chain import TraceRecord


class DriftReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    override_rate_baseline: float
    override_rate_current: float
    route_mix_current: dict[str, float] = Field(default_factory=dict)
    mean_confidence_current: float
    shifted: bool
    reasons: list[str] = Field(default_factory=list)


def _override_rate(traces: list[TraceRecord]) -> float:
    if not traces:
        return 0.0
    return sum(1 for trace in traces if trace.policy_overrode_decider) / len(traces)


def _mean_confidence(traces: list[TraceRecord]) -> float:
    values = [trace.confidence for trace in traces if trace.confidence is not None]
    if not values:
        return 0.0
    return sum(values) / len(values)


def _route_mix(traces: list[TraceRecord]) -> dict[str, float]:
    if not traces:
        return {}
    counts: dict[str, int] = {}
    for trace in traces:
        key = trace.route or "none"
        counts[key] = counts.get(key, 0) + 1
    return {key: count / len(traces) for key, count in sorted(counts.items())}


def detect_shift(
    baseline: list[TraceRecord],
    current: list[TraceRecord],
    override_rate_delta: float = 0.2,
) -> DriftReport:
    baseline_rate = _override_rate(baseline)
    current_rate = _override_rate(current)
    reasons: list[str] = []
    if current_rate - baseline_rate >= override_rate_delta:
        reasons.append("human override rate increased")
    return DriftReport(
        override_rate_baseline=baseline_rate,
        override_rate_current=current_rate,
        route_mix_current=_route_mix(current),
        mean_confidence_current=_mean_confidence(current),
        shifted=bool(reasons),
        reasons=reasons,
    )
