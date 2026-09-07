"""The one question loop. drill, exam and review differ only in the arguments passed here.

The ordering inside the loop is load-bearing: `correct` is computed but not handed to the
presenter until confidence has come back, so confidence cannot be captured after a reveal
even by accident.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from . import progress as progress_mod
from . import render
from .models import Attempt, Item


def new_session_id(mode: str, now: datetime | None = None) -> str:
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%MZ")
    return f"{mode}-{stamp}"


def run(
    items: list[Item],
    mode: str,
    session: str,
    reveal: bool = True,
    progress_path=None,
    presenter=render,
    clock=None,
) -> list[tuple[str, bool, str]]:
    """Serve each item, recording one row per item. Returns (qid, correct, confidence).

    With a clock, the run stops the moment time is up. Items never reached are the caller's
    to record -- see cli._cmd_exam, which writes them at grading as incorrect.
    """
    results: list[tuple[str, bool, str]] = []
    total = len(items)

    for index, item in enumerate(items, start=1):
        if clock is not None:
            if clock.expired:
                presenter.time_up()
                break
            warning = clock.due_warning()
            if warning is not None:
                presenter.time_warning(warning)
        presenter.question(item, index, total, clock=clock)
        started = time.monotonic()

        chosen = presenter.ask_answer(item)
        if chosen is None:
            break

        # Graded here, but deliberately not shown until confidence is in.
        correct = item.grade(chosen)

        confidence = presenter.ask_confidence()
        if confidence is None:
            break

        secs = int(time.monotonic() - started)
        attempt = Attempt(
            ts=datetime.now(UTC),
            session=session,
            mode=mode,
            qid=item.qid,
            obj=item.obj,
            rev=item.rev,
            correct=correct,
            confidence=confidence,
            secs=secs,
        )
        # Written and fsynced now: Ctrl-C after this point loses nothing.
        progress_mod.append(attempt, progress_path)
        results.append((item.qid, correct, confidence))

        if reveal:
            presenter.reveal(item, chosen, correct)

    return results
