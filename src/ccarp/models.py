"""Frozen dataclasses for everything that crosses a module boundary.

Attempt.from_json ignores unknown keys on purpose: progress.jsonl is append-only and
committed, so rows written by a future version must still parse in an older one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .config import CONFIDENCE_LEVELS


@dataclass(frozen=True)
class Objective:
    id: str
    name: str


@dataclass(frozen=True)
class Domain:
    id: str
    name: str
    weight: float
    items: int
    objectives: tuple[Objective, ...]


@dataclass(frozen=True)
class Blueprint:
    exam: dict
    domains: tuple[Domain, ...]

    @property
    def total_items(self) -> int:
        return sum(d.items for d in self.domains)

    @property
    def objective_ids(self) -> frozenset[str]:
        return frozenset(o.id for d in self.domains for o in d.objectives)

    def domain(self, domain_id: str) -> Domain | None:
        return next((d for d in self.domains if d.id == domain_id), None)


@dataclass(frozen=True)
class Option:
    key: str
    text: str
    correct: bool
    rationale: str


@dataclass(frozen=True)
class Item:
    qid: str
    obj: str
    rev: int
    format: str
    stem: str
    principle: str
    options: tuple[Option, ...]
    select_n: int = 1

    @property
    def domain_id(self) -> str:
        return self.qid.split("-", 1)[0]

    @property
    def correct_keys(self) -> frozenset[str]:
        return frozenset(o.key for o in self.options if o.correct)

    @property
    def is_multiple_response(self) -> bool:
        return self.format == "multiple_response"

    def grade(self, chosen: frozenset[str]) -> bool:
        """All-or-nothing: every correct option and no incorrect ones."""
        return chosen == self.correct_keys


@dataclass(frozen=True)
class Attempt:
    ts: datetime
    session: str
    mode: str
    qid: str
    obj: str
    rev: int
    correct: bool
    confidence: str
    secs: int

    @property
    def dedup_key(self) -> tuple[str, str, str]:
        return (self.session, self.qid, self.ts.isoformat())

    @property
    def confident_correct(self) -> bool:
        return self.correct and self.confidence == "sure"

    def to_json(self) -> dict:
        return {
            "ts": self.ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "session": self.session,
            "mode": self.mode,
            "qid": self.qid,
            "obj": self.obj,
            "rev": self.rev,
            "correct": self.correct,
            "confidence": self.confidence,
            "secs": self.secs,
        }

    @classmethod
    def from_json(cls, raw: dict) -> Attempt:
        # Python 3.11 fromisoformat parses the trailing Z natively.
        ts = datetime.fromisoformat(raw["ts"])
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        confidence = raw["confidence"]
        if confidence not in CONFIDENCE_LEVELS:
            raise ValueError(f"unknown confidence {confidence!r}")
        return cls(
            ts=ts.astimezone(UTC),
            session=raw["session"],
            mode=raw["mode"],
            qid=raw["qid"],
            obj=raw["obj"],
            # rev predates nothing, but tolerate a row written before it existed.
            rev=int(raw.get("rev", 1)),
            correct=bool(raw["correct"]),
            confidence=confidence,
            secs=int(raw["secs"]),
        )


@dataclass(frozen=True)
class Shortfall:
    """What selection could not serve, and when the next item frees up."""

    requested: int
    served: int
    in_cooldown: int
    next_free_in: float | None = None  # hours
    next_free_tier: str | None = None

    @property
    def short(self) -> int:
        return max(0, self.requested - self.served)


@dataclass
class Bank:
    items: tuple[Item, ...] = field(default_factory=tuple)

    def __len__(self) -> int:
        return len(self.items)

    def by_qid(self, qid: str) -> Item | None:
        return next((i for i in self.items if i.qid == qid), None)

    def filter(self, domain: str | None = None, obj: str | None = None) -> Bank:
        items = self.items
        if domain:
            items = tuple(i for i in items if i.domain_id == domain)
        if obj:
            items = tuple(i for i in items if i.obj == obj)
        return Bank(items)
