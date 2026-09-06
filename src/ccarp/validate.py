"""Hard structural checks. Errors exit 1; warnings never block a study session.

What is checked here is what a machine can actually know: sums, uniqueness, referential
integrity, answer-key arity. Authoring quality ("is this distractor a real practice?")
is not machine-checkable and lives in lint.py at warn level.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from . import bank as bank_mod
from . import blueprint as blueprint_mod
from .config import BLUEPRINT_STALE_DAYS, QID_PATTERN
from .models import Blueprint

_QID_RE = re.compile(QID_PATTERN)


def _check_item(item, declared_domain: str, bp: Blueprint) -> list[str]:
    errors: list[str] = []
    qid = item.qid

    if not _QID_RE.match(qid):
        errors.append(f"{qid}: qid must match {QID_PATTERN}")
        return errors  # everything below derives from a well-formed qid

    # Three ways to get the domain wrong, all silent if unchecked.
    if item.domain_id != declared_domain:
        errors.append(
            f"{qid}: lives in {declared_domain}.json but qid says {item.domain_id}"
        )
    obj_domain = "d" + item.obj.split(".", 1)[0]
    if obj_domain != item.domain_id:
        errors.append(f"{qid}: obj {item.obj} does not belong to domain {item.domain_id}")
    if item.obj not in bp.objective_ids:
        errors.append(f"{qid}: obj {item.obj} is not in the blueprint")

    if item.rev < 1:
        errors.append(f"{qid}: rev must be >= 1")
    if not item.stem.strip():
        errors.append(f"{qid}: empty stem")
    if not item.principle.strip():
        errors.append(f"{qid}: no principle named")

    keys = [o.key for o in item.options]
    if len(keys) != len(set(keys)):
        errors.append(f"{qid}: duplicate option keys")
    if len(keys) < 3:
        errors.append(f"{qid}: needs at least 3 options, has {len(keys)}")
    for o in item.options:
        if not o.rationale.strip():
            errors.append(f"{qid}: option {o.key} has no rationale")

    n_correct = len(item.correct_keys)
    if item.format == "multiple_choice":
        if n_correct != 1:
            errors.append(f"{qid}: multiple_choice needs exactly 1 correct option, has {n_correct}")
        if item.select_n != 1:
            errors.append(f"{qid}: multiple_choice must have select_n=1")
    elif item.format == "multiple_response":
        if item.select_n < 2:
            errors.append(f"{qid}: multiple_response needs select_n >= 2, has {item.select_n}")
        if item.select_n != n_correct:
            errors.append(
                f"{qid}: select_n={item.select_n} but {n_correct} options are marked correct"
            )
        if n_correct >= len(keys):
            errors.append(f"{qid}: every option is correct")
    else:
        errors.append(f"{qid}: unknown format {item.format!r}")

    return errors


def run(
    blueprint_path: Path | None = None, banks_dir: Path | None = None
) -> tuple[list[str], list[str], dict]:
    """Return (errors, warnings, summary)."""
    errors: list[str] = []
    warnings: list[str] = []

    bp = blueprint_mod.load(blueprint_path)
    errors.extend(blueprint_mod.check(bp))

    retrieved = bp.exam.get("retrieved")
    if retrieved:
        retrieved_on = datetime.strptime(retrieved, "%Y-%m-%d").replace(tzinfo=UTC).date()
        age = (datetime.now(UTC).date() - retrieved_on).days
        if age > BLUEPRINT_STALE_DAYS:
            warnings.append(
                f"blueprint retrieved {retrieved} ({age}d ago) -- "
                f"re-verify at {bp.exam.get('source', 'the source')}"
            )

    seen_qids: dict[str, str] = {}
    per_domain: dict[str, int] = {}
    for domain in bank_mod.DOMAIN_IDS:
        db, declared = bank_mod.load_domain(domain, banks_dir)
        per_domain[domain] = len(db)
        if declared is not None and declared != domain:
            errors.append(f"{domain}.json declares domain {declared!r}")
        for item in db.items:
            # qid uniqueness is global, not per-file: history is keyed on it.
            if item.qid in seen_qids:
                errors.append(f"duplicate qid {item.qid} in {seen_qids[item.qid]} and {domain}")
            else:
                seen_qids[item.qid] = domain
            errors.extend(_check_item(item, domain, bp))

    total = sum(per_domain.values())
    shortfalls = {
        d.id: (per_domain.get(d.id, 0), d.items)
        for d in bp.domains
        if per_domain.get(d.id, 0) < d.items
    }
    summary = {
        "blueprint_items": bp.total_items,
        "objectives": len(bp.objective_ids),
        "bank_total": total,
        "per_domain": per_domain,
        "exam_ready": not shortfalls,
        "shortfalls": shortfalls,
    }
    return errors, warnings, summary
