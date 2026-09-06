"""The loop's ordering is load-bearing, so it gets a test rather than a comment.

A fake presenter records the order of calls; render.py is never involved.
"""

import json

from ccarp import bank as bank_mod
from ccarp import runner
from tests.helpers import make_item


class FakePresenter:
    def __init__(self, answers, confidences):
        self.answers = list(answers)
        self.confidences = list(confidences)
        self.calls: list[str] = []

    def question(self, item, index, total):
        self.calls.append("question")

    def ask_answer(self, item):
        self.calls.append("ask_answer")
        return self.answers.pop(0) if self.answers else None

    def ask_confidence(self):
        self.calls.append("ask_confidence")
        return self.confidences.pop(0) if self.confidences else None

    def reveal(self, item, chosen, correct):
        self.calls.append("reveal")


def _items(n=1):
    return [bank_mod._item_from_json(make_item(f"d1-{i:03d}")) for i in range(1, n + 1)]


def test_confidence_is_asked_before_the_reveal(tmp_path):
    p = FakePresenter([frozenset("A")], ["sure"])
    runner.run(_items(1), "drill", "s", progress_path=tmp_path / "pl", presenter=p)
    assert p.calls.index("ask_confidence") < p.calls.index("reveal")


def test_one_row_per_item_is_written(tmp_path):
    path = tmp_path / "progress.jsonl"
    p = FakePresenter([frozenset("A"), frozenset("B")], ["sure", "guess"])
    runner.run(_items(2), "drill", "s1", progress_path=path, presenter=p)
    rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    assert [r["qid"] for r in rows] == ["d1-001", "d1-002"]
    assert [r["correct"] for r in rows] == [True, False]
    assert [r["confidence"] for r in rows] == ["sure", "guess"]


def test_quitting_mid_run_keeps_completed_rows(tmp_path):
    """Ctrl-C / quit must lose nothing already answered."""
    path = tmp_path / "progress.jsonl"
    p = FakePresenter([frozenset("A"), None], ["sure"])
    runner.run(_items(3), "drill", "s1", progress_path=path, presenter=p)
    rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    assert len(rows) == 1
    assert rows[0]["qid"] == "d1-001"


def test_quitting_at_the_confidence_prompt_writes_no_row(tmp_path):
    """No confidence means no row: a half-answered item is not data."""
    path = tmp_path / "progress.jsonl"
    p = FakePresenter([frozenset("A")], [None])
    runner.run(_items(1), "drill", "s1", progress_path=path, presenter=p)
    assert not path.exists() or path.read_text().strip() == ""


def test_reveal_is_skipped_in_exam_mode(tmp_path):
    p = FakePresenter([frozenset("A")], ["sure"])
    runner.run(_items(1), "exam", "s", reveal=False, progress_path=tmp_path / "pl", presenter=p)
    assert "reveal" not in p.calls


def test_multiple_response_scores_all_or_nothing(tmp_path):
    path = tmp_path / "progress.jsonl"
    raw = make_item("d1-001", format="multiple_response", select_n=2)
    raw["options"][1]["correct"] = True  # A and B correct
    item = bank_mod._item_from_json(raw)

    p = FakePresenter([frozenset({"A"})], ["sure"])  # partial answer
    runner.run([item], "drill", "s", progress_path=path, presenter=p)
    rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    assert rows[0]["correct"] is False
