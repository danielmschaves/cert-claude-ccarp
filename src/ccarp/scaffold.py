"""Skeletons for new items, shaped so the mechanical parts cannot be got wrong.

Writes nothing. Like bank.py this module only reads the bank and returns data -- the
skeleton goes to stdout for you to paste. `progress.jsonl` stays the only file the tool
ever writes.

The suggested answer key is the point of this module as much as the qid is. D1 originally
shipped with 91% of its correct answers on key A, which made the whole domain scoreable
without reading a stem. Proposing the least-used key at authoring time attacks that at the
moment the item is written, rather than catching it in lint afterwards.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Bank, Blueprint
from .report import domain_report

TODO_STEM = (
    "TODO 2-3 sentences of concrete situation -- a named system and a real constraint -- "
    "ending in a superlative question (best / most likely first)."
)
TODO_PRINCIPLE = "TODO the named principle the correct answer follows from"
TODO_CORRECT = "TODO the option that is best here"
TODO_DISTRACTOR = "TODO a real practice, inferior in THIS scenario"
TODO_RATIONALE_OK = "TODO why this is best here, from the principle"
TODO_RATIONALE_NO = "TODO what makes it a real practice, then why it loses here"

_QID_SUFFIX = re.compile(r"^d[1-7]-(\d{3})$")


@dataclass(frozen=True)
class Guidance:
    """What the author should know before writing, drawn from the current bank."""

    domain_id: str
    have: int
    need: int
    key_counts: dict[str, int]
    suggested_keys: tuple[str, ...]
    uncovered: tuple[str, ...]
    longest_share: float


def next_qid(bank: Bank, domain_id: str) -> str:
    """One past the highest suffix in use. Never reuses a number, even after a deletion:
    a reused qid would silently inherit the deleted item's history in progress.jsonl."""
    used = [
        int(m.group(1))
        for i in bank.items
        if (m := _QID_SUFFIX.match(i.qid)) and i.domain_id == domain_id
    ]
    return f"{domain_id}-{(max(used) + 1) if used else 1:03d}"


def suggest_keys(key_counts: dict[str, int], n_options: int) -> tuple[str, ...]:
    """Least-used keys first, so the answer key evens out as the domain grows."""
    keys = [chr(ord("A") + n) for n in range(n_options)]
    return tuple(sorted(keys, key=lambda k: (key_counts.get(k, 0), k)))


def skeleton(
    qid: str,
    obj: str,
    correct: set[str],
    n_options: int = 4,
    fmt: str = "multiple_choice",
    select_n: int = 1,
) -> dict:
    return {
        "qid": qid,
        "obj": obj,
        "rev": 1,
        "format": fmt,
        "select_n": select_n,
        "stem": TODO_STEM,
        "principle": TODO_PRINCIPLE,
        "options": [
            {
                "key": key,
                "text": TODO_CORRECT if key in correct else TODO_DISTRACTOR,
                "correct": key in correct,
                "rationale": TODO_RATIONALE_OK if key in correct else TODO_RATIONALE_NO,
            }
            for key in (chr(ord("A") + n) for n in range(n_options))
        ],
    }


def build(
    bp: Blueprint,
    bank: Bank,
    obj: str,
    count: int = 1,
    n_options: int = 4,
    fmt: str = "multiple_choice",
    select_n: int = 1,
) -> tuple[list[dict], Guidance]:
    domain_id = "d" + obj.split(".", 1)[0]
    r = domain_report(bp, bank, domain_id)
    suggested = suggest_keys(r.key_counts, n_options)

    items: list[dict] = []
    counts = dict(r.key_counts)
    qid_seed = int(next_qid(bank, domain_id).split("-")[1])

    for n in range(count):
        # Re-rank after each item so a run of several spreads across keys.
        order = suggest_keys(counts, n_options)
        correct = set(order[:select_n])
        items.append(skeleton(
            f"{domain_id}-{qid_seed + n:03d}", obj, correct, n_options, fmt, select_n
        ))
        for key in correct:
            counts[key] = counts.get(key, 0) + 1

    return items, Guidance(
        domain_id=domain_id,
        have=r.have,
        need=r.need,
        key_counts=r.key_counts,
        suggested_keys=suggested,
        uncovered=r.uncovered,
        longest_share=r.longest_share,
    )
