"""Load a decision-chain trace log and print a drift timeline. Shared by scripts/drift and scripts/simulate-traffic."""

from __future__ import annotations

from pathlib import Path

from fs_prod_agent.observe.decision_chain import TraceRecord
from fs_prod_agent.observe.drift import DriftReport


def load(path: Path) -> list[TraceRecord]:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    return [TraceRecord.model_validate_json(line) for line in lines if line.strip()]


def print_timeline(reports: list[DriftReport], window: int, marks: dict[int, str] | None = None) -> None:
    first = reports[0]
    print(
        f"baseline (records 1-{window}): routes {_mix(first.route_mix_baseline)} | "
        f"confidence {first.mean_confidence_baseline:.3f} | failed {first.failure_rate_baseline:.0%} | "
        f"override {first.override_rate_baseline:.0%}\n"
    )
    print(f"{'window':>7} {'records':>9}  {'confidence':>10} {'failed':>6} {'override':>8} {'route TVD':>9}  status")
    for index, report in enumerate(reports, start=1):
        start = index * window + 1
        status = "DRIFT: " + "; ".join(report.reasons) if report.shifted else "ok"
        mark = (marks or {}).get(index, "")
        print(
            f"{index:>7} {start:>4}-{start + window - 1:<4}  {report.mean_confidence_current:>10.3f} "
            f"{report.failure_rate_current:>6.0%} {report.override_rate_current:>8.0%} {report.route_shift:>9.2f}  "
            f"{status}{mark}"
        )


def _mix(mix: dict[str, float]) -> str:
    return ", ".join(f"{route} {share:.0%}" for route, share in mix.items())
