"""Tier assignment and drill ordering.

Pure: a function of (bank, attempts, now). `now` is passed in, never read from the clock,
which is the only reason the cooldown boundaries are testable at all.

An attempt recorded against an older `rev` counts for coverage but not for tiering -- a
revised item re-enters as unseen, because your history is about a question that no longer
exists in that form.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from .config import COOLDOWN_HOURS, TIER_ORDER
from .models import Attempt, Bank, Item, Shortfall


def _stable_order(qid: str) -> str:
    """Deterministic shuffle: same bank always presents unseen items in the same order."""
    return hashlib.sha256(qid.encode()).hexdigest()


def classify(item: Item, history: list[Attempt]) -> str:
    """Which tier an item sits in, given its attempts (ascending by ts)."""
    current = [a for a in history if a.rev == item.rev]
    if not current:
        return "unseen"

    latest = current[-1]
    if not latest.correct:
        return "wrong"
    if latest.confidence != "sure":
        return "shaky"
    # Two consecutive confident-corrects retires an item -- suppressed, then demoted.
    if len(current) >= 2 and current[-2].confident_correct:
        return "retired"
    return "solid"


def _eligible_at(tier: str, history: list[Attempt], item: Item) -> datetime | None:
    """When this item next becomes eligible. None means 'now'."""
    if tier == "unseen":
        return None
    current = [a for a in history if a.rev == item.rev]
    if not current:
        return None
    return current[-1].ts + timedelta(hours=COOLDOWN_HOURS[tier])


def select(
    bank: Bank,
    attempts: list[Attempt],
    now: datetime,
    n: int,
    tier_order: tuple[str, ...] = TIER_ORDER,
) -> tuple[list[Item], Shortfall]:
    """Drain tiers in order, falling through only when a tier is dry.

    Never pads a short run by blending tiers, and never serves an item twice.
    """
    history: dict[str, list[Attempt]] = {}
    for a in attempts:
        history.setdefault(a.qid, []).append(a)

    buckets: dict[str, list[tuple, Item]] = {t: [] for t in tier_order}
    blocked: list[tuple[datetime, str]] = []

    for item in bank.items:
        h = history.get(item.qid, [])
        tier = classify(item, h)
        if tier not in buckets:
            continue  # tier not drained in this mode
        free_at = _eligible_at(tier, h, item)
        if free_at is not None and free_at > now:
            blocked.append((free_at, tier))
            continue
        # unseen sorts by a stable hash; every other tier is oldest-attempt-first.
        key = (_stable_order(item.qid),) if tier == "unseen" else (h[-1].ts.isoformat(),)
        buckets[tier].append((key, item))

    served: list[Item] = []
    for tier in tier_order:
        if len(served) >= n:
            break
        for _, item in sorted(buckets[tier], key=lambda pair: pair[0]):
            if len(served) >= n:
                break
            served.append(item)

    next_free_in = next_free_tier = None
    if blocked and len(served) < n:
        free_at, tier = min(blocked, key=lambda pair: pair[0])
        next_free_in = (free_at - now).total_seconds() / 3600
        next_free_tier = tier

    return served, Shortfall(
        requested=n,
        served=len(served),
        in_cooldown=len(blocked),
        next_free_in=next_free_in,
        next_free_tier=next_free_tier,
    )


def tier_counts(bank: Bank, attempts: list[Attempt]) -> dict[str, int]:
    history: dict[str, list[Attempt]] = {}
    for a in attempts:
        history.setdefault(a.qid, []).append(a)
    counts = dict.fromkeys(TIER_ORDER, 0)
    for item in bank.items:
        counts[classify(item, history.get(item.qid, []))] += 1
    return counts
