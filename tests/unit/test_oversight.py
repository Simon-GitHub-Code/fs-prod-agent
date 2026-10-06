"""Desk arithmetic stays inside the inclusive IPS bands."""

import pytest

from fs_prod_agent.adapters.local.books import QUARTERLY_SNAPSHOT
from fs_prod_agent.domain.oversight import excess_return, performance_briefing, range_breaches


def test_excess_return_is_the_fund_minus_the_benchmark():
    assert excess_return(0.031, 0.024) == pytest.approx(0.007)


def test_ips_bands_are_inclusive_and_an_unbanded_asset_is_skipped():
    breaches = range_breaches(
        {"aaa_unbanded": 0.9, "bonds": 0.20, "cash": 0.15, "equities": 0.80},
        {"bonds": (0.20, 0.40), "cash": (0.00, 0.15), "equities": (0.50, 0.70)},
    )
    assert [item.asset_class for item in breaches] == ["equities"]
    assert breaches[0].weight == pytest.approx(0.80)


def test_a_weight_outside_either_end_is_a_breach():
    breaches = range_breaches(
        {"bonds": 0.19, "cash": 0.16},
        {"bonds": (0.20, 0.40), "cash": (0.00, 0.15)},
    )
    assert [(item.asset_class, item.weight) for item in breaches] == [("bonds", 0.19), ("cash", 0.16)]


def test_a_performance_briefing_names_the_fund_the_benchmark_and_the_policy():
    briefing = performance_briefing(QUARTERLY_SNAPSHOT)
    assert briefing.title == "Total fund pack 2026-06-30"
    assert briefing.evidence_ids == ["saa-policy"]
    assert "excess 0.70%" in briefing.body


def test_a_performance_snapshot_needs_both_returns():
    message = "a performance snapshot needs a fund return and a benchmark return"
    for update in (
        {"portfolio_return": None},
        {"benchmark_return": None},
        {"portfolio_return": None, "benchmark_return": None},
    ):
        with pytest.raises(ValueError) as caught:
            performance_briefing(QUARTERLY_SNAPSHOT.model_copy(update=update))
        assert str(caught.value) == message
