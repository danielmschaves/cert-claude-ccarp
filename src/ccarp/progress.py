"""The one piece of state: an append-only JSONL log.

Two rules drive the implementation. Rows are written and fsynced the moment an item is
done, so Ctrl-C mid-session loses nothing. And a malformed line warns and is skipped --
a corrupted row must never stand between you and a study session.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .config import PROGRESS_PATH
from .models import Attempt


def read(path: Path | None = None) -> list[Attempt]:
    p = Path(path or PROGRESS_PATH)
    if not p.exists():
        return []

    attempts: list[Attempt] = []
    seen: set[tuple[str, str, str]] = set()
    skipped = 0

    for lineno, line in enumerate(p.read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            attempt = Attempt.from_json(json.loads(line))
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            skipped += 1
            print(f"warn: {p.name}:{lineno} skipped ({exc})", file=sys.stderr)
            continue
        # Union-merge can duplicate a line verbatim; the log is the truth, not the count.
        if attempt.dedup_key in seen:
            continue
        seen.add(attempt.dedup_key)
        attempts.append(attempt)

    if skipped:
        print(f"warn: skipped {skipped} malformed row(s)", file=sys.stderr)

    attempts.sort(key=lambda a: a.ts)
    return attempts


def append(attempt: Attempt, path: Path | None = None) -> None:
    """One row, flushed and fsynced. Deliberately not buffered across items."""
    p = Path(path or PROGRESS_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(attempt.to_json(), separators=(",", ":")) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def latest_by_qid(attempts: list[Attempt]) -> dict[str, Attempt]:
    """Last attempt per qid. Input is assumed sorted by ts ascending."""
    return {a.qid: a for a in attempts}


def history_by_qid(attempts: list[Attempt]) -> dict[str, list[Attempt]]:
    out: dict[str, list[Attempt]] = {}
    for a in attempts:
        out.setdefault(a.qid, []).append(a)
    return out
