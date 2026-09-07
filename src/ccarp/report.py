"""Bank measurements: what the bank looks like, not whether it is allowed.

Pure -- returns data, prints nothing. The thresholds and the pass/fail judgement live in
lint.py; this module only counts. Splitting them means CI can show the numbers on every PR
while the gate is tightened separately.

The distribution measures here are the classic test-construction tells. None of them proves
an item is bad, but an author working at volume drifts into all of them, and unlike "is this
distractor a real practice?" they are actually computable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Bank, Blueprint, Item


@dataclass(frozen=True)
class DomainReport:
    domain_id: str
    name: str
    have: int
    need: int
    objectives_total: int
    objectives_covered: int
    uncovered: tuple[str, ...]
    key_counts: dict[str, int] = field(default_factory=dict)
    correct_longest: int = 0
    multiple_response: int = 0
    top_principle: tuple[str, int] | None = None

    @property
    def complete(self) -> bool:
        return self.have >= self.need

    @property
    def key_skew(self) -> float:
        """Share held by the most common answer key. Uniform is 1/n_options."""
        total = sum(self.key_counts.values())
        return max(self.key_counts.values()) / total if total else 0.0

    @property
    def longest_share(self) -> float:
        return self.correct_longest / self.have if self.have else 0.0

    @property
    def principle_share(self) -> float:
        if not self.have or not self.top_principle:
            return 0.0
        return self.top_principle[1] / self.have


def _mean_len(texts: list[str]) -> float:
    return sum(len(t) for t in texts) / len(texts) if texts else 0.0


def correct_is_longest(item: Item) -> bool:
    """True when a test-taker could pick the answer by counting characters."""
    correct = [o.text for o in item.options if o.correct]
    others = [o.text for o in item.options if not o.correct]
    if not correct or not others:
        return False
    return max(len(t) for t in correct) > max(len(t) for t in others)


def length_ratio(item: Item) -> float:
    """Longest correct option over the mean length of the distractors."""
    correct = [o.text for o in item.options if o.correct]
    others = [o.text for o in item.options if not o.correct]
    mean_other = _mean_len(others)
    if not correct or not mean_other:
        return 0.0
    return max(len(t) for t in correct) / mean_other


def domain_report(bp: Blueprint, bank: Bank, domain_id: str) -> DomainReport:
    domain = bp.domain(domain_id)
    items = [i for i in bank.items if i.domain_id == domain_id]

    key_counts: dict[str, int] = {}
    for item in items:
        for key in sorted(item.correct_keys):
            key_counts[key] = key_counts.get(key, 0) + 1

    principles: dict[str, int] = {}
    for item in items:
        principles[item.principle] = principles.get(item.principle, 0) + 1
    top = max(principles.items(), key=lambda kv: kv[1]) if principles else None

    seen_objs = {i.obj for i in items}
    all_objs = tuple(o.id for o in domain.objectives) if domain else ()
    uncovered = tuple(o for o in all_objs if o not in seen_objs)

    return DomainReport(
        domain_id=domain_id,
        name=domain.name if domain else domain_id,
        have=len(items),
        need=domain.items if domain else 0,
        objectives_total=len(all_objs),
        objectives_covered=len(all_objs) - len(uncovered),
        uncovered=uncovered,
        key_counts=key_counts,
        correct_longest=sum(1 for i in items if correct_is_longest(i)),
        multiple_response=sum(1 for i in items if i.is_multiple_response),
        top_principle=top,
    )


def build(bp: Blueprint, bank: Bank) -> list[DomainReport]:
    return [domain_report(bp, bank, d.id) for d in bp.domains]
