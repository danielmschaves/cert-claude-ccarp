"""Coverage, mastery and correctness, derived from progress.jsonl at read time.

Pure: a function of (bank, attempts, now). `now` is passed in and never read from the clock.

Coverage and mastery are computed together and always reported together, because either
alone misleads: 100% coverage at 20% mastery is a different position entirely from 30/30,
and a tool that shows only one of them will flatter you.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .config import LAST_N_WINDOW
from .models import Attempt, Bank, Blueprint


@dataclass(frozen=True)
class Slice:
    """Stats over one subset of the bank -- the whole thing, a domain, or an objective."""

    label: str
    bank_size: int
    seen: int
    mastered: int
    stale: int
    attempts: int
    correct: int

    @property
    def coverage(self) -> float | None:
        return self.seen / self.bank_size if self.bank_size else None

    @property
    def mastery(self) -> float | None:
        return self.mastered / self.bank_size if self.bank_size else None

    @property
    def accuracy(self) -> float | None:
        return self.correct / self.attempts if self.attempts else None


@dataclass(frozen=True)
class Report:
    overall: Slice
    by_domain: tuple[Slice, ...]
    by_objective: tuple[Slice, ...]
    last_n: Slice
    window: int


def _slice(label: str, items, attempts: list[Attempt]) -> Slice:
    """Mastery is rev-aware: an attempt against a superseded item no longer counts.

    Coverage still counts it -- you have seen the question, and pretending otherwise would
    make coverage jump backwards whenever an item is corrected.
    """
    qids = {i.qid for i in items}
    revs = {i.qid: i.rev for i in items}
    relevant = [a for a in attempts if a.qid in qids]

    latest: dict[str, Attempt] = {}
    for a in relevant:
        latest[a.qid] = a  # attempts arrive sorted by ts

    mastered = sum(
        1 for qid, a in latest.items() if a.confident_correct and a.rev == revs[qid]
    )
    stale = sum(1 for qid, a in latest.items() if a.rev != revs[qid])

    return Slice(
        label=label,
        bank_size=len(qids),
        seen=len(latest),
        mastered=mastered,
        stale=stale,
        attempts=len(relevant),
        correct=sum(1 for a in relevant if a.correct),
    )


def build(
    bp: Blueprint, bank: Bank, attempts: list[Attempt], now: datetime | None = None
) -> Report:
    """`now` is accepted for symmetry with selection and for future time-windowed stats."""
    del now  # not needed yet; kept so callers never learn to omit it

    by_domain = tuple(
        _slice(d.id, [i for i in bank.items if i.domain_id == d.id], attempts)
        for d in bp.domains
    )
    by_objective = tuple(
        _slice(o.id, [i for i in bank.items if i.obj == o.id], attempts)
        for d in bp.domains
        for o in d.objectives
    )
    recent = attempts[-LAST_N_WINDOW:]
    return Report(
        overall=_slice("all", bank.items, attempts),
        by_domain=by_domain,
        by_objective=by_objective,
        last_n=_slice(f"last-{LAST_N_WINDOW}", bank.items, recent),
        window=LAST_N_WINDOW,
    )


def wrong_qids(attempts: list[Attempt], bank: Bank) -> list[str]:
    """Items whose most recent attempt was incorrect, oldest first. Tier-free by design."""
    latest: dict[str, Attempt] = {}
    known = {i.qid for i in bank.items}
    for a in attempts:
        if a.qid in known:
            latest[a.qid] = a
    wrong = [a for a in latest.values() if not a.correct]
    wrong.sort(key=lambda a: a.ts)
    return [a.qid for a in wrong]
