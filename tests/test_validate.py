"""Structural checks over the banks. Milestone one is the first test here."""

from ccarp import validate
from tests.helpers import make_item


def test_empty_banks_pass(blueprint_path, empty_banks):
    errors, _, summary = validate.run(blueprint_path, empty_banks)
    assert errors == []
    assert summary["bank_total"] == 0
    assert summary["exam_ready"] is False  # honest: you cannot sit a mock on nothing


def test_duplicate_qid_across_files_is_caught(blueprint_path, banks_with):
    # Same qid in two files: history is keyed on qid, so this must never be silent.
    banks = banks_with({
        "d1": [make_item("d1-001", "1.1")],
        "d2": [make_item("d1-001", "1.1")],
    })
    errors, _, _ = validate.run(blueprint_path, banks)
    assert any("duplicate qid d1-001" in e for e in errors)


def test_qid_must_match_its_file(blueprint_path, banks_with):
    banks = banks_with({"d2": [make_item("d1-005", "1.1")]})
    errors, _, _ = validate.run(blueprint_path, banks)
    assert any("lives in d2.json but qid says d1" in e for e in errors)


def test_obj_must_match_qid_domain(blueprint_path, banks_with):
    banks = banks_with({"d1": [make_item("d1-001", "3.5")]})
    errors, _, _ = validate.run(blueprint_path, banks)
    assert any("obj 3.5 does not belong to domain d1" in e for e in errors)


def test_unknown_obj_is_caught(blueprint_path, banks_with):
    banks = banks_with({"d1": [make_item("d1-001", "1.9")]})
    errors, _, _ = validate.run(blueprint_path, banks)
    assert any("not in the blueprint" in e for e in errors)


def test_malformed_qid_is_caught(blueprint_path, banks_with):
    banks = banks_with({"d1": [make_item("d1-1", "1.1")]})
    errors, _, _ = validate.run(blueprint_path, banks)
    assert any("must match" in e for e in errors)


def test_multiple_choice_needs_exactly_one_correct(blueprint_path, banks_with):
    item = make_item()
    item["options"][1]["correct"] = True
    banks = banks_with({"d1": [item]})
    errors, _, _ = validate.run(blueprint_path, banks)
    assert any("exactly 1 correct" in e for e in errors)


def test_multiple_response_select_n_must_match_key(blueprint_path, banks_with):
    item = make_item(format="multiple_response", select_n=3)
    item["options"][1]["correct"] = True  # 2 correct, select_n says 3
    banks = banks_with({"d1": [item]})
    errors, _, _ = validate.run(blueprint_path, banks)
    assert any("select_n=3 but 2 options are marked correct" in e for e in errors)


def test_multiple_response_needs_select_n_at_least_two(blueprint_path, banks_with):
    banks = banks_with({"d1": [make_item(format="multiple_response", select_n=1)]})
    errors, _, _ = validate.run(blueprint_path, banks)
    assert any("select_n >= 2" in e for e in errors)


def test_option_without_rationale_is_caught(blueprint_path, banks_with):
    item = make_item()
    item["options"][2]["rationale"] = "  "
    banks = banks_with({"d1": [item]})
    errors, _, _ = validate.run(blueprint_path, banks)
    assert any("option C has no rationale" in e for e in errors)


def test_missing_principle_is_caught(blueprint_path, banks_with):
    banks = banks_with({"d1": [make_item(principle="")]})
    errors, _, _ = validate.run(blueprint_path, banks)
    assert any("no principle named" in e for e in errors)


def test_good_item_passes(blueprint_path, banks_with):
    banks = banks_with({"d1": [make_item()]})
    errors, _, summary = validate.run(blueprint_path, banks)
    assert errors == []
    assert summary["bank_total"] == 1
