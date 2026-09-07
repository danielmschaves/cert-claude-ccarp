"""Authoring rules, at warn level by default.

Two kinds of rule live here. Per-item rules read one item. Distribution rules read a whole
domain and catch what no single item reveals: the tells that let a test-taker score without
reading the stem. An author working at volume drifts into all of them, which is exactly why
they are checked by machine rather than by intention.

What is deliberately NOT here: "is this distractor a real practice inferior *here*?" That is
the most important authoring rule and it is not machine-checkable. Nothing in this file
should be mistaken for having verified it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Bank, Blueprint, Item
from .report import domain_report, length_ratio

SUPERLATIVE = re.compile(
    r"\b(best|most|least|first|primary|greatest|strongest|worst|highest|lowest)\b", re.IGNORECASE
)
BANNED_OPTIONS = re.compile(r"\b(all|none) of the above\b", re.IGNORECASE)

# Figures that rot: prices, percentages, model ids, dated benchmarks, latency numbers.
VOLATILE = [
    (re.compile(r"[$€£]\s?\d"), "a price"),
    (re.compile(r"\d+\s?%"), "a percentage"),
    (re.compile(r"\b(claude|gpt|gemini|llama|mistral)[\w.-]*\d", re.IGNORECASE), "a model id"),
    (re.compile(r"\b(19|20)\d{2}\b"), "a year"),
    (re.compile(r"\b\d+\s?(ms|milliseconds|tokens?/s|tokens per second)\b", re.IGNORECASE), "a latency or throughput figure"),
    (re.compile(r"\b\d[\d,]*\s?(k|m)?\s?(tokens|token context)\b", re.IGNORECASE), "a context size"),
]

MAX_KEY_SHARE = 0.40
MAX_LONGEST_SHARE = 0.50
MAX_LENGTH_RATIO = 1.4
MAX_PRINCIPLE_SHARE = 0.34
MIN_STEM_SENTENCES = 2
MAX_STEM_SENTENCES = 3


@dataclass(frozen=True)
class Warning_:
    scope: str   # a qid, or a domain id for distribution rules
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.scope}: {self.message}  [{self.rule}]"


def _sentences(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s])


def check_item(item: Item) -> list[Warning_]:
    warns: list[Warning_] = []
    w = warns.append

    n = _sentences(item.stem)
    if not MIN_STEM_SENTENCES <= n <= MAX_STEM_SENTENCES:
        w(Warning_(item.qid, "stem-length",
                   f"stem is {n} sentence(s); want {MIN_STEM_SENTENCES}-{MAX_STEM_SENTENCES}"))

    if not SUPERLATIVE.search(item.stem):
        w(Warning_(item.qid, "no-superlative",
                   "stem has no superlative -- the task should be ranking options, not recall"))

    for opt in item.options:
        if BANNED_OPTIONS.search(opt.text):
            w(Warning_(item.qid, "banned-option", f"option {opt.key} is an all/none-of-the-above"))

    for text, where in [(item.stem, "stem")] + [(o.text, f"option {o.key}") for o in item.options]:
        for pattern, what in VOLATILE:
            if pattern.search(text):
                w(Warning_(item.qid, "volatile-figure", f"{where} contains {what}"))
                break

    if not 3 <= len(item.options) <= 5:
        w(Warning_(item.qid, "option-count", f"{len(item.options)} options; want 3-5"))

    ratio = length_ratio(item)
    if ratio > MAX_LENGTH_RATIO:
        w(Warning_(item.qid, "length-tell",
                   f"correct option is {ratio:.1f}x the mean distractor length "
                   f"(max {MAX_LENGTH_RATIO})"))

    return warns


def check_domain(bp: Blueprint, bank: Bank, domain_id: str) -> list[Warning_]:
    """Rules no single item can violate. This is where volume authoring gets caught."""
    r = domain_report(bp, bank, domain_id)
    if not r.have:
        return []

    warns: list[Warning_] = []
    w = warns.append

    if r.key_skew > MAX_KEY_SHARE:
        top = max(r.key_counts.items(), key=lambda kv: kv[1])
        w(Warning_(domain_id, "key-skew",
                   f"{r.key_skew:.0%} of correct answers are {top[0]} "
                   f"(max {MAX_KEY_SHARE:.0%}) -- guessable without reading"))

    if r.longest_share > MAX_LONGEST_SHARE:
        w(Warning_(domain_id, "length-tell",
                   f"the correct option is longest in {r.longest_share:.0%} of items "
                   f"(max {MAX_LONGEST_SHARE:.0%})"))

    if r.principle_share > MAX_PRINCIPLE_SHARE and r.top_principle:
        w(Warning_(domain_id, "principle-reuse",
                   f"'{r.top_principle[0]}' covers {r.principle_share:.0%} of the domain "
                   f"(max {MAX_PRINCIPLE_SHARE:.0%}) -- one idea in several hats"))

    if r.uncovered and r.complete:
        w(Warning_(domain_id, "objective-gap",
                   f"domain is full but objectives {', '.join(r.uncovered)} have no items"))

    return warns


def run(bp: Blueprint, bank: Bank) -> list[Warning_]:
    warns = [wn for item in bank.items for wn in check_item(item)]
    for d in bp.domains:
        warns.extend(check_domain(bp, bank, d.id))
    return warns
