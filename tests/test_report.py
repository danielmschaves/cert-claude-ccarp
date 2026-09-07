"""Bank measurements, including the tells that betray a guessable item."""

from ccarp import bank as bank_mod
from ccarp import blueprint as bp_mod
from ccarp import report
from ccarp.models import Bank
from tests.helpers import make_item


def _item(qid="d1-001", obj="1.1", **over):
    return bank_mod._item_from_json(make_item(qid, obj, **over))


def _keyed(qid, obj, correct_key, texts=None):
    """An item whose correct answer is `correct_key`."""
    raw = make_item(qid, obj)
    for o in raw["options"]:
        o["correct"] = o["key"] == correct_key
        if texts:
            o["text"] = texts[o["key"]]
    return bank_mod._item_from_json(raw)


def test_counts_against_the_blueprint(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    bank = Bank((_item("d1-001"), _item("d1-002")))
    r = report.domain_report(bp, bank, "d1")
    assert (r.have, r.need) == (2, 11)
    assert r.complete is False


def test_uncovered_objectives_are_named(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    bank = Bank((_item("d1-001", "1.1"),))
    r = report.domain_report(bp, bank, "d1")
    assert r.objectives_covered == 1
    assert set(r.uncovered) == {"1.2", "1.3", "1.4", "1.5", "1.6"}


def test_key_skew_catches_an_answer_key_stuck_on_one_letter(blueprint_path):
    """The defect this whole report exists to surface."""
    bp = bp_mod.load(blueprint_path)
    bank = Bank(tuple(_keyed(f"d1-{n:03d}", "1.1", "A") for n in range(1, 5)))
    r = report.domain_report(bp, bank, "d1")
    assert r.key_counts == {"A": 4}
    assert r.key_skew == 1.0


def test_balanced_keys_have_low_skew(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    bank = Bank((
        _keyed("d1-001", "1.1", "A"),
        _keyed("d1-002", "1.1", "B"),
        _keyed("d1-003", "1.1", "C"),
        _keyed("d1-004", "1.1", "A"),
    ))
    r = report.domain_report(bp, bank, "d1")
    assert r.key_skew == 0.5


def test_correct_is_longest_is_detected():
    item = _keyed("d1-001", "1.1", "A", texts={
        "A": "a considerably longer and more carefully written correct answer",
        "B": "short",
        "C": "also short",
    })
    assert report.correct_is_longest(item) is True
    assert report.length_ratio(item) > 1.4


def test_even_lengths_do_not_trip_the_tell():
    item = _keyed("d1-001", "1.1", "A", texts={
        "A": "an answer of roughly ordinary length here",
        "B": "another answer of roughly the same length",
        "C": "a third answer of roughly that length too",
    })
    assert report.correct_is_longest(item) is False


def test_principle_reuse_is_measured(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    bank = Bank((
        _item("d1-001", principle="same"),
        _item("d1-002", principle="same"),
        _item("d1-003", principle="different"),
    ))
    r = report.domain_report(bp, bank, "d1")
    assert r.top_principle == ("same", 2)
    assert r.principle_share > 0.66


def test_empty_domain_reports_cleanly(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    r = report.domain_report(bp, Bank(), "d3")
    assert (r.have, r.need) == (0, 12)
    assert r.key_skew == 0.0
    assert r.longest_share == 0.0


def test_build_covers_every_blueprint_domain(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    assert [r.domain_id for r in report.build(bp, Bank())] == [d.id for d in bp.domains]
