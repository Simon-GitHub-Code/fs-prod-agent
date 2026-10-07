"""The routing suite runs on every change. The fixture tier may not regress past its baseline."""

from fs_prod_agent.composition import build
from fs_prod_agent.evals.loader import load_suite
from fs_prod_agent.evals.run import score_suite
from fs_prod_agent.evals.score import Baseline, regressions
from tests.fitness.support import REPO

_SUITE = REPO / "evals" / "routing" / "v1" / "cases.jsonl"
_BASELINE = REPO / "evals" / "baselines" / "fixture.json"


def test_the_fixture_tier_holds_its_baseline():
    card = score_suite("fixture", load_suite(_SUITE), lambda: build("local"))
    baseline = Baseline.model_validate_json(_BASELINE.read_text(encoding="utf-8"))
    assert regressions(card, baseline) == []
