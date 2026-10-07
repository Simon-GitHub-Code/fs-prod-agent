"""Cyclomatic ratchet. New functions stay at or under the cap. Named functions may not grow."""

from scripts.context.lib.complexity import CAP, GRANDFATHERED, function_scores, scores_in
from tests.fitness.support import SRC


def test_production_complexity_matches_the_ratchet():
    scores = function_scores(SRC)
    over = {key: value for key, value in scores.items() if value > CAP}
    assert over == GRANDFATHERED


def test_a_function_over_the_cap_is_rejected():
    body = "".join(f"    if n == {index}:\n        return {index}\n" for index in range(CAP + 1))
    scores = scores_in("new.py", f"def wider(n):\n{body}")
    assert scores["new.py::wider"] > CAP
    assert {key: value for key, value in scores.items() if value > CAP} != {}
