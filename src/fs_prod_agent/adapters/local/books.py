"""The fixture book the local workflows compute against. Not a decision."""

from fs_prod_agent.domain.models import Mandate, PortfolioSnapshot

QUARTERLY_SNAPSHOT = PortfolioSnapshot(
    as_of="2026-06-30",
    holdings={
        "bonds": 0.22,
        "cash": 0.08,
        "equities": 0.62,
        "private_markets": 0.08,
    },
    portfolio_return=0.031,
    benchmark_return=0.024,
)

IPS = Mandate(
    mandate_id="total-fund",
    name="Total fund investment policy statement",
    ranges={
        "bonds": (0.20, 0.40),
        "cash": (0.00, 0.15),
        "equities": (0.50, 0.70),
        "private_markets": (0.00, 0.05),
    },
)

MANAGER_REPORTS = {
    "Global Equity Manager B": (
        "Global Equity Manager B, quarter to 2026-06-30. Return 1.2% against a 2.6% benchmark; "
        "three years 1.1% a year behind. The lead portfolio manager left in May 2026 and the co-manager "
        "now runs the strategy. Watchlist flag: on watch since 2026-05-15 for the team change and the "
        "three-year shortfall."
    ),
}

MANAGER_POLICY = (
    "A manager goes on watch after a key-person departure, or after three years more than 1% a year "
    "behind benchmark. Watch lasts up to two quarters. The analyst then recommends retain or terminate "
    "to the investment committee. Only the committee decides."
)


def policy_text() -> str:
    ranges = "; ".join(f"{name} {low:.0%}-{high:.0%}" for name, (low, high) in sorted(IPS.ranges.items()))
    return f"{IPS.name}. Policy ranges: {ranges}. {MANAGER_POLICY}"


def holdings_text() -> str:
    weights = "; ".join(f"{name} {weight:.0%}" for name, weight in sorted(QUARTERLY_SNAPSHOT.holdings.items()))
    return f"Holdings at {QUARTERLY_SNAPSHOT.as_of}: {weights}."


def manager_report(query: str) -> str:
    for name, report in MANAGER_REPORTS.items():
        if name.lower() in query.lower():
            return report
    return "No manager report matches. Known managers: " + ", ".join(sorted(MANAGER_REPORTS)) + "."
