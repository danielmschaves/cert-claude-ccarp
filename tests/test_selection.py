"""Tier assignment and cooldown boundaries.

selection is pure and takes `now`, which is the only reason a 24h boundary can be tested
without waiting a day.
"""

from datetime import UTC, datetime, timedelta

import pytest

from ccarp import bank as bank_mod
from ccarp import selection
from ccarp.models import Attempt, Bank

NOW = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)


def item(qid="d1-001", obj="1.1", rev=1):
    from tests.helpers import make_item
    return bank_mod._item_from_json(make_item(qid, obj, rev=rev))


def attempt(qid="d1-001", *, ago_h=0.0, correct=True, confidence="sure", rev=1):
    return Attempt(
        ts=NOW - timedelta(hours=ago_h),
        session="s",
        mode="drill",
        qid=qid,
        obj="1.1",
        rev=rev,
        correct=correct,
        confidence=confidence,
        secs=10,
    )


# --- classification ---------------------------------------------------------

def test_no_attempts_is_unseen():
    assert selection.classify(item(), []) == "unseen"


@pytest.mark.parametrize(
    "correct,confidence,expected",
    [
        (False, "sure", "wrong"),
        (False, "guess", "wrong"),
        (True, "unsure", "shaky"),
        (True, "guess", "shaky"),
        (True, "sure", "solid"),
    ],
)
def test_latest_attempt_decides_tier(correct, confidence, expected):
    history = [attempt(correct=correct, confidence=confidence)]
    assert selection.classify(item(), history) == expected


def test_two_consecutive_confident_corrects_retire():
    history = [attempt(ago_h=100), attempt(ago_h=50)]
    assert selection.classify(item(), history) == "retired"


def test_a_slip_before_the_last_confident_correct_does_not_retire():
    history = [attempt(ago_h=100, correct=False), attempt(ago_h=50)]
    assert selection.classify(item(), history) == "solid"


def test_attempts_at_an_older_rev_do_not_count_for_tiering():
    """A revised item re-enters as unseen: the history is about a question that changed."""
    history = [attempt(rev=1), attempt(rev=1)]
    assert selection.classify(item(rev=2), history) == "unseen"


# --- cooldown boundaries ----------------------------------------------------

@pytest.mark.parametrize("ago_h,served", [(23.9, 0), (24.1, 1)])
def test_wrong_tier_24h_boundary(ago_h, served):
    bank = Bank((item(),))
    picked, _ = selection.select(bank, [attempt(ago_h=ago_h, correct=False)], NOW, 5)
    assert len(picked) == served


@pytest.mark.parametrize("ago_h,served", [(71.9, 0), (72.1, 1)])
def test_shaky_tier_72h_boundary(ago_h, served):
    bank = Bank((item(),))
    history = [attempt(ago_h=ago_h, confidence="guess")]
    picked, _ = selection.select(bank, history, NOW, 5)
    assert len(picked) == served


@pytest.mark.parametrize("ago_h,served", [(24 * 14 - 1, 0), (24 * 14 + 1, 1)])
def test_solid_tier_14d_boundary(ago_h, served):
    bank = Bank((item(),))
    picked, _ = selection.select(bank, [attempt(ago_h=ago_h)], NOW, 5)
    assert len(picked) == served


@pytest.mark.parametrize("ago_h,served", [(24 * 30 - 1, 0), (24 * 30 + 1, 1)])
def test_retired_tier_30d_boundary(ago_h, served):
    bank = Bank((item(),))
    history = [attempt(ago_h=ago_h + 24), attempt(ago_h=ago_h)]
    picked, _ = selection.select(bank, history, NOW, 5)
    assert len(picked) == served


# --- ordering and fall-through ----------------------------------------------

def test_unseen_is_drained_before_wrong():
    bank = Bank((item("d1-001"), item("d1-002")))
    history = [attempt("d1-001", ago_h=48, correct=False)]
    picked, _ = selection.select(bank, history, NOW, 1)
    assert [i.qid for i in picked] == ["d1-002"]


def test_falls_through_only_when_a_tier_is_dry():
    bank = Bank((item("d1-001"), item("d1-002")))
    history = [attempt("d1-001", ago_h=48, correct=False)]
    picked, _ = selection.select(bank, history, NOW, 2)
    # unseen first, then the wrong one -- never blended to pad the count
    assert [i.qid for i in picked] == ["d1-002", "d1-001"]


def test_wrong_tier_serves_oldest_first():
    bank = Bank((item("d1-001"), item("d1-002")))
    history = [
        attempt("d1-001", ago_h=30, correct=False),
        attempt("d1-002", ago_h=100, correct=False),
    ]
    picked, _ = selection.select(bank, history, NOW, 2)
    assert [i.qid for i in picked] == ["d1-002", "d1-001"]


def test_no_item_is_served_twice_in_one_run():
    bank = Bank(tuple(item(f"d1-{n:03d}") for n in range(1, 4)))
    picked, _ = selection.select(bank, [], NOW, 10)
    assert len(picked) == len({i.qid for i in picked}) == 3


def test_unseen_order_is_stable_across_runs():
    bank = Bank(tuple(item(f"d1-{n:03d}") for n in range(1, 6)))
    first, _ = selection.select(bank, [], NOW, 5)
    second, _ = selection.select(bank, [], NOW, 5)
    assert [i.qid for i in first] == [i.qid for i in second]


# --- shortfall reporting ----------------------------------------------------

def test_shortfall_reports_how_short_and_when_the_next_frees_up():
    bank = Bank((item("d1-001"), item("d1-002")))
    history = [
        attempt("d1-001", ago_h=1, correct=False),   # 23h to go
        attempt("d1-002", ago_h=10, correct=False),  # 14h to go
    ]
    picked, sf = selection.select(bank, history, NOW, 5)
    assert picked == []
    assert sf.short == 5
    assert sf.in_cooldown == 2
    assert sf.next_free_tier == "wrong"
    assert sf.next_free_in == pytest.approx(14.0)


def test_no_shortfall_when_the_run_is_filled():
    bank = Bank(tuple(item(f"d1-{n:03d}") for n in range(1, 6)))
    _, sf = selection.select(bank, [], NOW, 3)
    assert sf.short == 0
    assert sf.next_free_in is None


def test_exhausted_bank_serves_nothing_rather_than_repeating():
    bank = Bank((item("d1-001"),))
    picked, sf = selection.select(bank, [attempt(ago_h=0)], NOW, 5)
    assert picked == []
    assert sf.in_cooldown == 1
