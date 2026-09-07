"""Skeletons for new items. Pure -- reads the bank, writes nothing."""

import pytest

from ccarp import bank as bank_mod
from ccarp import blueprint as bp_mod
from ccarp import scaffold
from ccarp.models import Bank
from tests.helpers import make_item


def _item(qid, obj="1.1", key="A"):
    raw = make_item(qid, obj)
    for o in raw["options"]:
        o["correct"] = o["key"] == key
    return bank_mod._item_from_json(raw)


# --- qid allocation ---------------------------------------------------------

def test_first_item_in_an_empty_domain():
    assert scaffold.next_qid(Bank(), "d3") == "d3-001"


def test_next_qid_follows_the_highest_in_use():
    bank = Bank((_item("d1-001"), _item("d1-007"), _item("d1-003")))
    assert scaffold.next_qid(bank, "d1") == "d1-008"


def test_next_qid_is_scoped_to_its_domain():
    bank = Bank((_item("d1-011"), _item("d2-003", "2.1")))
    assert scaffold.next_qid(bank, "d2") == "d2-004"


def test_a_deleted_number_is_never_reused():
    """A reused qid would silently inherit the deleted item's progress.jsonl history."""
    bank = Bank((_item("d1-001"), _item("d1-005")))  # 002-004 deleted
    assert scaffold.next_qid(bank, "d1") == "d1-006"


# --- answer key suggestion --------------------------------------------------

def test_least_used_key_is_suggested_first():
    assert scaffold.suggest_keys({"A": 9, "B": 1, "C": 4, "D": 0}, 4)[0] == "D"


def test_an_unused_key_beats_a_used_one():
    assert scaffold.suggest_keys({"A": 2, "B": 2}, 4)[:2] == ("C", "D")


def test_suggestion_is_deterministic_on_ties():
    assert scaffold.suggest_keys({}, 4) == ("A", "B", "C", "D")


def test_suggestion_respects_option_count():
    assert scaffold.suggest_keys({}, 5)[-1] == "E"


# --- skeletons --------------------------------------------------------------

def test_skeleton_marks_exactly_the_suggested_key(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    bank = Bank(tuple(_item(f"d1-{n:03d}", key="A") for n in range(1, 5)))
    items, guidance = scaffold.build(bp, bank, "1.1")
    correct = [o["key"] for o in items[0]["options"] if o["correct"]]
    assert correct == [guidance.suggested_keys[0]]
    assert correct != ["A"]  # A is saturated in this bank


def test_a_run_of_items_spreads_across_keys(blueprint_path):
    """Three skeletons in one go must not all land on the same key."""
    bp = bp_mod.load(blueprint_path)
    items, _ = scaffold.build(bp, Bank(), "7.2", count=3)
    keys = [next(o["key"] for o in i["options"] if o["correct"]) for i in items]
    assert len(set(keys)) == 3


def test_a_run_of_items_gets_sequential_qids(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    items, _ = scaffold.build(bp, Bank((_item("d1-011"),)), "1.1", count=3)
    assert [i["qid"] for i in items] == ["d1-012", "d1-013", "d1-014"]


def test_multiple_response_skeleton(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    items, _ = scaffold.build(
        bp, Bank(), "5.1", n_options=5, fmt="multiple_response", select_n=2
    )
    item = items[0]
    assert item["select_n"] == 2
    assert len([o for o in item["options"] if o["correct"]]) == 2
    assert len(item["options"]) == 5


def test_guidance_carries_the_domains_current_state(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    bank = Bank((_item("d1-001", "1.1"),))
    _, g = scaffold.build(bp, bank, "1.1")
    assert (g.domain_id, g.have, g.need) == ("d1", 1, 11)
    assert "1.2" in g.uncovered


# --- the skeleton is a starting point, not a valid item ---------------------

def test_an_unfilled_skeleton_fails_strict_validation(blueprint_path, banks_with, tmp_path):
    """The TODOs must not slip through CI if someone commits one unfilled."""
    from ccarp import validate

    bp = bp_mod.load(blueprint_path)
    items, _ = scaffold.build(bp, Bank(), "1.1")
    banks = banks_with({"d1": items})
    errors, _, _ = validate.run(blueprint_path, banks, strict=True)
    assert errors, "an unfilled skeleton should not pass --strict"


def test_scaffold_writes_nothing(blueprint_path, tmp_path):
    """Like bank.py, this module only reads. progress.jsonl stays the only file we write."""
    bp = bp_mod.load(blueprint_path)
    before = sorted(p.name for p in tmp_path.iterdir())
    scaffold.build(bp, bank_mod.load(), "1.1", count=5)
    assert sorted(p.name for p in tmp_path.iterdir()) == before


@pytest.mark.parametrize("obj,expected", [("1.1", "d1"), ("3.5", "d3"), ("7.2", "d7")])
def test_domain_is_derived_from_the_objective(blueprint_path, obj, expected):
    bp = bp_mod.load(blueprint_path)
    _, g = scaffold.build(bp, Bank(), obj)
    assert g.domain_id == expected
