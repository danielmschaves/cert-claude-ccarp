"""Coverage, mastery and correctness. Pure over (bank, attempts, now)."""

from datetime import UTC, datetime, timedelta

from ccarp import bank as bank_mod
from ccarp import blueprint as bp_mod
from ccarp import stats
from ccarp.models import Attempt, Bank
from tests.helpers import make_item

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


def _item(qid="d1-001", obj="1.1", rev=1):
    return bank_mod._item_from_json(make_item(qid, obj, rev=rev))


def _a(qid="d1-001", *, ago_h=0.0, correct=True, confidence="sure", rev=1, obj="1.1"):
    return Attempt(
        ts=NOW - timedelta(hours=ago_h), session="s", mode="drill", qid=qid, obj=obj,
        rev=rev, correct=correct, confidence=confidence, secs=10,
    )


def _report(bank, attempts, blueprint_path):
    return stats.build(bp_mod.load(blueprint_path), bank, attempts, NOW)


def test_empty_bank_reports_none_not_zero(blueprint_path):
    r = _report(Bank(), [], blueprint_path)
    assert r.overall.coverage is None
    assert r.overall.mastery is None
    assert r.overall.accuracy is None


def test_no_attempts_is_zero_coverage_not_none(blueprint_path):
    r = _report(Bank((_item(),)), [], blueprint_path)
    assert r.overall.coverage == 0.0
    assert r.overall.mastery == 0.0


def test_coverage_and_mastery_diverge(blueprint_path):
    """The reason they are always reported together."""
    bank = Bank(tuple(_item(f"d1-{n:03d}") for n in range(1, 5)))
    attempts = [
        _a("d1-001", ago_h=3),                        # correct + sure -> mastered
        _a("d1-002", ago_h=2, confidence="unsure"),   # correct, not sure
        _a("d1-003", ago_h=1, correct=False),         # wrong
    ]
    r = _report(bank, attempts, blueprint_path)
    assert r.overall.coverage == 0.75
    assert r.overall.mastery == 0.25


def test_mastery_uses_only_the_latest_attempt(blueprint_path):
    bank = Bank((_item(),))
    attempts = [_a(ago_h=5), _a(ago_h=1, correct=False)]
    r = _report(bank, attempts, blueprint_path)
    assert r.overall.mastery == 0.0
    assert r.overall.coverage == 1.0


def test_a_revised_item_keeps_coverage_but_loses_mastery(blueprint_path):
    """Editing an answer key must not leave mastery overstated."""
    bank = Bank((_item(rev=2),))
    r = _report(bank, [_a(rev=1)], blueprint_path)
    assert r.overall.coverage == 1.0
    assert r.overall.mastery == 0.0
    assert r.overall.stale == 1


def test_lifetime_and_last_n_can_disagree(blueprint_path):
    """Needs more than a full window of attempts, or last-50 is just lifetime."""
    bank = Bank(tuple(_item(f"d1-{n:03d}") for n in range(1, 4)))
    # 50 old failures, then 50 recent successes: lifetime 50%, last-50 100%.
    old_wrong = [
        _a(f"d1-{(n % 3) + 1:03d}", ago_h=200 - n, correct=False) for n in range(50)
    ]
    recent_right = [_a(f"d1-{(n % 3) + 1:03d}", ago_h=50 - n * 0.5) for n in range(50)]
    r = stats.build(bp_mod.load(blueprint_path), bank, old_wrong + recent_right, NOW)
    assert r.overall.accuracy == 0.5
    assert r.last_n.accuracy == 1.0
    assert r.last_n.attempts == 50


def test_attempts_on_items_not_in_the_bank_are_ignored(blueprint_path):
    r = _report(Bank((_item("d1-001"),)), [_a("d1-999")], blueprint_path)
    assert r.overall.attempts == 0
    assert r.overall.coverage == 0.0


def test_per_domain_and_per_objective_slices(blueprint_path):
    bank = Bank((_item("d1-001", "1.1"), _item("d1-002", "1.2")))
    r = _report(bank, [_a("d1-001", obj="1.1")], blueprint_path)
    d1 = next(s for s in r.by_domain if s.label == "d1")
    assert (d1.seen, d1.bank_size) == (1, 2)
    o11 = next(s for s in r.by_objective if s.label == "1.1")
    o12 = next(s for s in r.by_objective if s.label == "1.2")
    assert o11.coverage == 1.0
    assert o12.coverage == 0.0
    assert len(r.by_objective) == 38


# --- review --wrong ---------------------------------------------------------

def test_wrong_qids_are_oldest_first():
    bank = Bank((_item("d1-001"), _item("d1-002"), _item("d1-003")))
    attempts = [
        _a("d1-001", ago_h=10, correct=False),
        _a("d1-002", ago_h=50, correct=False),
        _a("d1-003", ago_h=5),
    ]
    assert stats.wrong_qids(attempts, bank) == ["d1-002", "d1-001"]


def test_an_item_since_corrected_leaves_the_review_list():
    bank = Bank((_item("d1-001"),))
    attempts = [_a("d1-001", ago_h=10, correct=False), _a("d1-001", ago_h=1)]
    assert stats.wrong_qids(attempts, bank) == []


def test_review_ignores_cooldowns():
    """A wrong answer a minute ago is still reviewable -- tiers do not apply here."""
    bank = Bank((_item("d1-001"),))
    assert stats.wrong_qids([_a("d1-001", ago_h=0.01, correct=False)], bank) == ["d1-001"]
