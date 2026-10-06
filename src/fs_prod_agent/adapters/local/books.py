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
