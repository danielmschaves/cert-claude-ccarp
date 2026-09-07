"""Grading an exam sitting and estimating a scaled score.

The single place the scaled-score caveat lives. The raw-to-scaled mapping is NOT published
by Anthropic, so everything here is named as an estimate and no pass/fail verdict is ever
produced: under this estimator the 720 cut implies roughly 44/63, but that number is an
artifact of assuming linearity, and real criterion-referenced scaling rarely is.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from datetime import datetime

from .models import Attempt, Bank, Blueprint, Item

CAVEAT = (
    "scaled_score_est is a linear estimate; Anthropic does not publish the raw-to-scaled "
    "mapping. Under this estimator the {cut} cut implies about {implied}/{total} raw."
)


def scaled_score_est(pct: float, scale: dict) -> int:
    """round(100 + 900 * pct), per the project's stated estimator."""
    lo, hi = int(scale["min"]), int(scale["max"])
    return round(lo + (hi - lo) * pct)


def implied_raw_threshold(scale: dict, total: int) -> int:
    """How many items the cut corresponds to under the estimator. Always shown with it."""
    lo, hi, cut = int(scale["min"]), int(scale["max"]), int(scale["cut"])
    # Smallest raw count whose estimate reaches the cut, so ceiling rather than round.
    return math.ceil((cut - lo) / (hi - lo) * total)


def caveat_line(scale: dict, total: int) -> str:
    return CAVEAT.format(cut=scale["cut"], implied=implied_raw_threshold(scale, total),
                         total=total)


@dataclass(frozen=True)
class DomainScore:
    domain_id: str
    name: str
    correct: int
    total: int

    @property
    def pct(self) -> float:
        return self.correct / self.total if self.total else 0.0


@dataclass(frozen=True)
class ExamResult:
    raw_correct: int
    raw_total: int
    unanswered: int
    by_domain: tuple[DomainScore, ...]
    scaled_score_est: int
    cut: int
    implied_raw: int
    caveat: str
    elapsed_secs: int

    @property
    def pct(self) -> float:
        return self.raw_correct / self.raw_total if self.raw_total else 0.0


def draw(bp: Blueprint, bank: Bank, seed: str) -> tuple[list[Item], dict[str, int]]:
    """Blueprint quota per domain, uniform random within it.

    Deliberately NOT unseen-preferring: weighting toward material you have not met would
    make the mock easier or harder than the real thing depending on your history.
    """
    rng = random.Random(seed)
    picked: list[Item] = []
    short: dict[str, int] = {}
    for d in bp.domains:
        pool = [i for i in bank.items if i.domain_id == d.id]
        if len(pool) < d.items:
            short[d.id] = d.items - len(pool)
            continue
        picked.extend(rng.sample(pool, d.items))
    rng.shuffle(picked)
    return picked, short


def new_seed(now: datetime) -> str:
    """Short, embedded in the session id, so a sitting is reproducible with no schema change."""
    return hashlib.sha256(now.isoformat().encode()).hexdigest()[:8]


def grade(
    bp: Blueprint, served: list[Item], attempts: list[Attempt], elapsed_secs: int
) -> ExamResult:
    by_qid = {a.qid: a for a in attempts}
    answered = {a.qid for a in attempts if a.secs > 0}

    scores: list[DomainScore] = []
    for d in bp.domains:
        items = [i for i in served if i.domain_id == d.id]
        if not items:
            continue
        scores.append(DomainScore(
            domain_id=d.id,
            name=d.name,
            correct=sum(1 for i in items if by_qid.get(i.qid) and by_qid[i.qid].correct),
            total=len(items),
        ))

    total = len(served)
    correct = sum(s.correct for s in scores)
    pct = correct / total if total else 0.0
    scale = bp.exam["scale"]

    return ExamResult(
        raw_correct=correct,
        raw_total=total,
        unanswered=total - len(answered),
        by_domain=tuple(scores),
        scaled_score_est=scaled_score_est(pct, scale),
        cut=int(scale["cut"]),
        implied_raw=implied_raw_threshold(scale, total),
        caveat=caveat_line(scale, total),
        elapsed_secs=elapsed_secs,
    )
