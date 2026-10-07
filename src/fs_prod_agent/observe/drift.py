"""Compare two windows of decision-chain traces. Pure: no model and no I/O.

Production traffic has no labels, so these are label-free signals read straight off the traces. Each
one leads a user-visible failure:

- human override rate: policy is refusing confident proceeds more often than it did
- route mix: requests are landing on different paths (total variation distance between the windows)
- mean confidence: the decider is less sure than it was, before it is wrong often enough to notice
- failure rate: failed or uncertain verdicts, from an outage, invalid answers, or low confidence
"""

from pydantic import BaseModel, ConfigDict, Field

from fs_prod_agent.observe.decision_chain import TraceRecord

_FAILED = {"failed", "uncertain"}


class DriftThresholds(BaseModel):
    model_config = ConfigDict(frozen=True)

    override_rate_delta: float = 0.2
    route_shift: float = 0.2
    confidence_drop: float = 0.05
    failure_rate_delta: float = 0.1


class DriftReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    override_rate_baseline: float
    override_rate_current: float
    route_mix_baseline: dict[str, float] = Field(default_factory=dict)
    route_mix_current: dict[str, float] = Field(default_factory=dict)
    route_shift: float = 0.0
    mean_confidence_baseline: float = 0.0
    mean_confidence_current: float
    failure_rate_baseline: float = 0.0
    failure_rate_current: float = 0.0
    shifted: bool
    reasons: list[str] = Field(default_factory=list)


def _override_rate(traces: list[TraceRecord]) -> float:
    if not traces:
        return 0.0
    return sum(1 for trace in traces if trace.policy_overrode_decider) / len(traces)


def _failure_rate(traces: list[TraceRecord]) -> float:
    if not traces:
        return 0.0
    return sum(1 for trace in traces if trace.policy_verdict in _FAILED) / len(traces)


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


def _total_variation(left: dict[str, float], right: dict[str, float]) -> float:
    keys = set(left) | set(right)
    return sum(abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in keys) / 2


def detect_shift(
    baseline: list[TraceRecord],
    current: list[TraceRecord],
    override_rate_delta: float = 0.2,
    thresholds: DriftThresholds | None = None,
) -> DriftReport:
    limits = thresholds or DriftThresholds(override_rate_delta=override_rate_delta)
    report = DriftReport(
        override_rate_baseline=_override_rate(baseline),
        override_rate_current=_override_rate(current),
        route_mix_baseline=_route_mix(baseline),
        route_mix_current=_route_mix(current),
        route_shift=_total_variation(_route_mix(baseline), _route_mix(current)),
        mean_confidence_baseline=_mean_confidence(baseline),
        mean_confidence_current=_mean_confidence(current),
        failure_rate_baseline=_failure_rate(baseline),
        failure_rate_current=_failure_rate(current),
        shifted=False,
    )
    reasons = _reasons(report, limits)
    return report.model_copy(update={"shifted": bool(reasons), "reasons": reasons})


def _reasons(report: DriftReport, limits: DriftThresholds) -> list[str]:
    reasons: list[str] = []
    if report.override_rate_current - report.override_rate_baseline >= limits.override_rate_delta:
        reasons.append("human override rate increased")
    if report.route_shift >= limits.route_shift:
        reasons.append(f"route mix shifted (total variation {report.route_shift:.2f})")
    if report.mean_confidence_baseline - report.mean_confidence_current >= limits.confidence_drop:
        reasons.append(
            f"mean confidence fell {report.mean_confidence_baseline:.2f} -> {report.mean_confidence_current:.2f}"
        )
    if report.failure_rate_current - report.failure_rate_baseline >= limits.failure_rate_delta:
        reasons.append(
            f"failed or uncertain verdicts rose {report.failure_rate_baseline:.0%} -> {report.failure_rate_current:.0%}"
        )
    return reasons


def rolling(records: list[TraceRecord], window: int, thresholds: DriftThresholds | None = None) -> list[DriftReport]:
    """The first window is the baseline. Each later full window is compared with it, in order."""
    if window <= 0 or len(records) < 2 * window:
        return []
    baseline = records[:window]
    starts = range(window, len(records) - window + 1, window)
    return [detect_shift(baseline, records[start : start + window], thresholds=thresholds) for start in starts]
