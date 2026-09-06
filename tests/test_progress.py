"""The append-only log. A corrupted row must never stand between you and a study session."""

import json
from datetime import UTC, datetime

from ccarp import progress
from ccarp.models import Attempt


def _attempt(qid="d1-001", **over):
    base = {
        "ts": datetime(2026, 9, 6, 12, 0, tzinfo=UTC),
        "session": "drill-20260906T1200Z",
        "mode": "drill",
        "qid": qid,
        "obj": "1.1",
        "rev": 1,
        "correct": True,
        "confidence": "sure",
        "secs": 30,
    }
    base.update(over)
    return Attempt(**base)


def test_round_trip(tmp_path):
    p = tmp_path / "progress.jsonl"
    a = _attempt()
    progress.append(a, p)
    assert progress.read(p) == [a]


def test_appends_do_not_overwrite(tmp_path):
    p = tmp_path / "progress.jsonl"
    progress.append(_attempt("d1-001"), p)
    progress.append(_attempt("d1-002"), p)
    assert [a.qid for a in progress.read(p)] == ["d1-001", "d1-002"]


def test_missing_file_is_empty_not_an_error(tmp_path):
    assert progress.read(tmp_path / "nope.jsonl") == []


def test_malformed_line_is_skipped_not_fatal(tmp_path, capsys):
    p = tmp_path / "progress.jsonl"
    progress.append(_attempt("d1-001"), p)
    with p.open("a") as fh:
        fh.write("{not json\n")
    progress.append(_attempt("d1-002"), p)

    attempts = progress.read(p)
    assert [a.qid for a in attempts] == ["d1-001", "d1-002"]
    assert "skipped" in capsys.readouterr().err


def test_duplicate_line_from_union_merge_is_deduped(tmp_path):
    p = tmp_path / "progress.jsonl"
    a = _attempt()
    progress.append(a, p)
    # git merge=union can reproduce an identical line on both sides.
    with p.open("a") as fh:
        fh.write(json.dumps(a.to_json()) + "\n")
    assert len(progress.read(p)) == 1


def test_rows_are_sorted_by_ts(tmp_path):
    p = tmp_path / "progress.jsonl"
    progress.append(_attempt("d1-002", ts=datetime(2026, 9, 6, 13, 0, tzinfo=UTC)), p)
    progress.append(_attempt("d1-001", ts=datetime(2026, 9, 6, 11, 0, tzinfo=UTC)), p)
    assert [a.qid for a in progress.read(p)] == ["d1-001", "d1-002"]


def test_row_without_rev_still_parses(tmp_path):
    """Tolerate a row written before rev existed rather than crashing on it."""
    p = tmp_path / "progress.jsonl"
    raw = _attempt().to_json()
    del raw["rev"]
    p.write_text(json.dumps(raw) + "\n")
    assert progress.read(p)[0].rev == 1


def test_unknown_keys_are_ignored(tmp_path):
    p = tmp_path / "progress.jsonl"
    raw = _attempt().to_json() | {"future_field": "written by a later version"}
    p.write_text(json.dumps(raw) + "\n")
    assert progress.read(p)[0].qid == "d1-001"
