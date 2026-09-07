"""Exam draw, grading, and the scaled-score estimate.

The estimate is a fabrication we are honest about. Several tests here exist purely to stop
that honesty being refactored away.
"""


from datetime import UTC, datetime

import pytest

from ccarp import bank as bank_mod
from ccarp import blueprint as bp_mod
from ccarp import render, scoring
from ccarp.models import Attempt, Bank
from tests.helpers import make_item

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


def _full_bank(blueprint_path):
    """A bank meeting the blueprint quota exactly, built from fixtures."""
    bp = bp_mod.load(blueprint_path)
    items = []
    for d in bp.domains:
        objs = [o.id for o in d.objectives]
        for n in range(d.items):
            items.append(bank_mod._item_from_json(
                make_item(f"{d.id}-{n + 1:03d}", objs[n % len(objs)])
            ))
    return Bank(tuple(items))


def _attempt(qid, obj, correct, secs=10, session="s"):
    return Attempt(ts=NOW, session=session, mode="exam", qid=qid, obj=obj, rev=1,
                   correct=correct, confidence="sure", secs=secs)


# --- the estimate, and the honesty around it --------------------------------

def test_implied_threshold_is_44_of_63(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    assert scoring.implied_raw_threshold(bp.exam["scale"], 63) == 44


def test_the_threshold_is_the_first_raw_score_that_clears_the_cut(blueprint_path):
    scale = bp_mod.load(blueprint_path).exam["scale"]
    assert scoring.scaled_score_est(43 / 63, scale) < scale["cut"]
    assert scoring.scaled_score_est(44 / 63, scale) >= scale["cut"]


@pytest.mark.parametrize("pct,expected", [(0.0, 100), (1.0, 1000), (0.5, 550)])
def test_estimator_endpoints(blueprint_path, pct, expected):
    scale = bp_mod.load(blueprint_path).exam["scale"]
    assert scoring.scaled_score_est(pct, scale) == expected


def test_the_caveat_names_the_mapping_as_unpublished(blueprint_path):
    """Guard: this sentence is the only thing stopping the estimate reading as a real score."""
    scale = bp_mod.load(blueprint_path).exam["scale"]
    line = scoring.caveat_line(scale, 63)
    assert "does not publish" in line
    assert "estimate" in line
    assert "44/63" in line


def test_no_pass_or_fail_verdict_is_ever_rendered(blueprint_path, capsys):
    """We do not know the raw cut, so we do not render a verdict."""
    bp = bp_mod.load(blueprint_path)
    bank = _full_bank(blueprint_path)
    served, _ = scoring.draw(bp, bank, "seed")
    attempts = [_attempt(i.qid, i.obj, True) for i in served]
    render.exam_report(scoring.grade(bp, served, attempts, 3600))
    printed = capsys.readouterr().out.lower()
    assert "pass" not in printed
    assert "fail" not in printed
    assert "scaled_score_est" in printed


# --- the draw ---------------------------------------------------------------

def test_draw_fills_the_blueprint_quota(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    served, short = scoring.draw(bp, _full_bank(blueprint_path), "seed")
    assert short == {}
    assert len(served) == 63
    for d in bp.domains:
        assert sum(1 for i in served if i.domain_id == d.id) == d.items


def test_draw_reports_shortfall_instead_of_serving_a_partial_exam(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    thin = Bank(tuple(bank_mod._item_from_json(make_item(f"d1-{n:03d}")) for n in range(1, 4)))
    served, short = scoring.draw(bp, thin, "seed")
    assert served == []
    assert short["d1"] == 8
    assert short["d3"] == 12


def test_the_same_seed_reproduces_the_same_sitting(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    bank = _full_bank(blueprint_path)
    a, _ = scoring.draw(bp, bank, "seed-one")
    b, _ = scoring.draw(bp, bank, "seed-one")
    c, _ = scoring.draw(bp, bank, "seed-two")
    assert [i.qid for i in a] == [i.qid for i in b]
    assert [i.qid for i in a] != [i.qid for i in c]


def test_draw_never_repeats_an_item(blueprint_path):
    served, _ = scoring.draw(bp_mod.load(blueprint_path), _full_bank(blueprint_path), "s")
    assert len({i.qid for i in served}) == len(served)


def test_draw_does_not_consult_history(blueprint_path):
    """Signature proof: an unseen-preferring draw would make the mock easier than the real thing."""
    import inspect
    params = inspect.signature(scoring.draw).parameters
    assert "attempts" not in params and "progress" not in params


# --- grading ----------------------------------------------------------------

def test_grade_counts_per_domain(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    served, _ = scoring.draw(bp, _full_bank(blueprint_path), "seed")
    # everything right except d3
    attempts = [_attempt(i.qid, i.obj, i.domain_id != "d3") for i in served]
    result = scoring.grade(bp, served, attempts, 100)
    d3 = next(s for s in result.by_domain if s.domain_id == "d3")
    assert d3.correct == 0
    assert result.raw_correct == 63 - 12


def test_unanswered_items_are_counted_and_scored_incorrect(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    served, _ = scoring.draw(bp, _full_bank(blueprint_path), "seed")
    answered = [_attempt(i.qid, i.obj, True) for i in served[:60]]
    ran_out = [_attempt(i.qid, i.obj, False, secs=0) for i in served[60:]]
    unanswered = frozenset(i.qid for i in served[60:])
    result = scoring.grade(bp, served, answered + ran_out, 7200, unanswered)
    assert result.unanswered == 3
    assert result.raw_correct == 60
    assert result.raw_total == 63


def test_a_fast_sitting_is_not_reported_as_unanswered(blueprint_path):
    """Regression: unanswered was inferred from secs == 0, so quick answers vanished."""
    bp = bp_mod.load(blueprint_path)
    served, _ = scoring.draw(bp, _full_bank(blueprint_path), "seed")
    instant = [_attempt(i.qid, i.obj, True, secs=0) for i in served]
    result = scoring.grade(bp, served, instant, 30)
    assert result.unanswered == 0
    assert result.raw_correct == 63


def test_a_perfect_sitting_reaches_the_top_of_the_scale(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    served, _ = scoring.draw(bp, _full_bank(blueprint_path), "seed")
    result = scoring.grade(bp, served, [_attempt(i.qid, i.obj, True) for i in served], 60)
    assert result.raw_correct == 63
    assert result.scaled_score_est == 1000
