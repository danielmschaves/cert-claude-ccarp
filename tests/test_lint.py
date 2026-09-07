"""Authoring rules. Per-item rules read one item; distribution rules read a domain.

What is NOT tested here, because it cannot be: whether a distractor is a real practice that
is inferior in the given scenario. That remains a human judgement.
"""

from ccarp import bank as bank_mod
from ccarp import blueprint as bp_mod
from ccarp import lint
from ccarp.models import Bank
from tests.helpers import make_item

GOOD_STEM = (
    "A team runs a nightly batch that reconciles orders against shipments. Failures cluster in "
    "one stage but the whole job is retried. Which change best improves reliability?"
)


def _item(qid="d1-001", obj="1.1", **over):
    return bank_mod._item_from_json(make_item(qid, obj, **over))


def _rules(warns):
    return {w.rule for w in warns}


def _keyed(qid, key, obj="1.1", texts=None):
    raw = make_item(qid, obj, stem=GOOD_STEM)
    for o in raw["options"]:
        o["correct"] = o["key"] == key
        if texts:
            o["text"] = texts[o["key"]]
    return bank_mod._item_from_json(raw)


# --- per-item ---------------------------------------------------------------

def test_a_well_formed_item_is_clean():
    assert lint.check_item(_item(stem=GOOD_STEM)) == []


def test_missing_superlative_is_flagged():
    stem = "A team runs a batch job. It fails sometimes. What should they change about it?"
    assert "no-superlative" in _rules(lint.check_item(_item(stem=stem)))


def test_a_one_sentence_stem_is_flagged():
    assert "stem-length" in _rules(lint.check_item(_item(stem="Which option best applies?")))


def test_a_five_sentence_stem_is_flagged():
    stem = "One. Two things happen. Three things happen. Four things happen. Which is best?"
    assert "stem-length" in _rules(lint.check_item(_item(stem=stem)))


def test_all_of_the_above_is_flagged():
    item = make_item(stem=GOOD_STEM)
    item["options"][2]["text"] = "All of the above"
    assert "banned-option" in _rules(lint.check_item(bank_mod._item_from_json(item)))


def test_volatile_figures_are_flagged():
    """Prices, percentages, model ids, years and latency all rot the bank."""
    for bad in ["it costs $400 a month", "accuracy rose 12% overall",
                "they moved to claude-3-opus", "the 2024 benchmark run",
                "a 250ms budget per call", "a 200k tokens context"]:
        stem = f"A team ships a service and {bad}. Load has since doubled. Which fix is best?"
        assert "volatile-figure" in _rules(lint.check_item(_item(stem=stem))), bad


def test_a_much_longer_correct_option_is_flagged():
    item = _keyed("d1-001", "A", texts={
        "A": "a considerably longer and far more carefully written correct answer than the rest",
        "B": "short one",
        "C": "another short",
    })
    assert "length-tell" in _rules(lint.check_item(item))


def test_balanced_option_lengths_pass():
    item = _keyed("d1-001", "A", texts={
        "A": "an answer of roughly ordinary length for this item",
        "B": "another answer of roughly that same length here",
        "C": "a third answer of roughly the same length again",
    })
    assert "length-tell" not in _rules(lint.check_item(item))


# --- distribution -----------------------------------------------------------

def test_key_skew_is_flagged(blueprint_path):
    """The defect that was actually present in D1: every answer was A."""
    bp = bp_mod.load(blueprint_path)
    bank = Bank(tuple(_keyed(f"d1-{n:03d}", "A") for n in range(1, 6)))
    warns = lint.check_domain(bp, bank, "d1")
    assert "key-skew" in _rules(warns)
    assert "guessable without reading" in str(warns[0])


def test_balanced_keys_pass(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    bank = Bank(tuple(
        _keyed(f"d1-{n:03d}", k) for n, k in enumerate("ABCABC", start=1)
    ))
    assert "key-skew" not in _rules(lint.check_domain(bp, bank, "d1"))


def test_domain_wide_length_bias_is_flagged(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    long_correct = {"A": "a much longer and more carefully written correct answer here",
                    "B": "short", "C": "brief"}
    bank = Bank(tuple(_keyed(f"d1-{n:03d}", "A", texts=long_correct) for n in range(1, 5)))
    assert "length-tell" in _rules(lint.check_domain(bp, bank, "d1"))


def test_one_principle_carrying_a_domain_is_flagged(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    bank = Bank(tuple(
        _item(f"d1-{n:03d}", stem=GOOD_STEM, principle="grounding") for n in range(1, 5)
    ))
    assert "principle-reuse" in _rules(lint.check_domain(bp, bank, "d1"))


def test_an_empty_domain_produces_no_distribution_warnings(blueprint_path):
    bp = bp_mod.load(blueprint_path)
    assert lint.check_domain(bp, Bank(), "d3") == []


def test_objective_gap_only_fires_once_a_domain_is_full(blueprint_path):
    """A partial domain is not yet guilty of skipping an objective."""
    bp = bp_mod.load(blueprint_path)
    partial = Bank(tuple(_keyed(f"d7-{n:03d}", "ABC"[n % 3], obj="7.1") for n in range(1, 3)))
    assert "objective-gap" not in _rules(lint.check_domain(bp, partial, "d7"))

    full = Bank(tuple(_keyed(f"d7-{n:03d}", "ABCA"[n % 4], obj="7.1") for n in range(1, 5)))
    assert "objective-gap" in _rules(lint.check_domain(bp, full, "d7"))


# --- the real bank ----------------------------------------------------------

def test_the_shipped_bank_is_clean(blueprint_path):
    """Regression guard: D1 shipped with 91% of answers on key A and no question in the stem."""
    bp = bp_mod.load(blueprint_path)
    assert lint.run(bp, bank_mod.load()) == []
