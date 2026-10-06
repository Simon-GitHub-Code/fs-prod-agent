"""Desk arithmetic. Pure: no I/O and no decision port."""

from fs_prod_agent.domain.models import Briefing, PortfolioSnapshot, RangeBreach


def excess_return(portfolio_return: float, benchmark_return: float) -> float:
    return portfolio_return - benchmark_return


def range_breaches(
    holdings: dict[str, float],
    ranges: dict[str, tuple[float, float]],
) -> tuple[RangeBreach, ...]:
    """Weights outside the inclusive IPS band. An asset with no band is left out."""
    breaches: list[RangeBreach] = []
    for asset_class in sorted(holdings):
        if asset_class not in ranges:
            continue
        lower, upper = ranges[asset_class]
        weight = holdings[asset_class]
        if weight < lower or weight > upper:
            breaches.append(RangeBreach(asset_class=asset_class, weight=weight, lower=lower, upper=upper))
    return tuple(breaches)


def performance_briefing(snapshot: PortfolioSnapshot) -> Briefing:
    if snapshot.portfolio_return is None or snapshot.benchmark_return is None:
        raise ValueError("a performance snapshot needs a fund return and a benchmark return")
    excess = excess_return(snapshot.portfolio_return, snapshot.benchmark_return)
    body = (
        f"Quarter to {snapshot.as_of}: total fund {snapshot.portfolio_return:.2%} "
        f"versus SAA {snapshot.benchmark_return:.2%}, excess {excess:.2%}."
    )
    return Briefing(
        title=f"Total fund pack {snapshot.as_of}",
        body=body,
        evidence_ids=["saa-policy"],
    )
