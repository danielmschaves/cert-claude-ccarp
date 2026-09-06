"""Load blueprint.json and assert the exam's own invariants.

These three assertions exist so that editing a weight fails loudly instead of quietly
producing a 62-item exam.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import BLUEPRINT_PATH
from .models import Blueprint, Domain, Objective

WEIGHT_TOLERANCE = 1e-9


def load(path: Path | None = None) -> Blueprint:
    raw = json.loads(Path(path or BLUEPRINT_PATH).read_text())
    domains = tuple(
        Domain(
            id=d["id"],
            name=d["name"],
            weight=float(d["weight"]),
            items=int(d["items"]),
            objectives=tuple(Objective(id=o["id"], name=o["name"]) for o in d["objectives"]),
        )
        for d in raw["domains"]
    )
    return Blueprint(exam=raw["exam"], domains=domains)


def check(bp: Blueprint) -> list[str]:
    """Return a list of error strings; empty means the blueprint is sound."""
    errors: list[str] = []
    declared_total = int(bp.exam["items"])

    weight_sum = sum(d.weight for d in bp.domains)
    if abs(weight_sum - 1.0) > WEIGHT_TOLERANCE:
        errors.append(f"domain weights sum to {weight_sum:.6f}, expected 1.0")

    if bp.total_items != declared_total:
        errors.append(
            f"domain item counts sum to {bp.total_items}, expected {declared_total}"
        )

    for d in bp.domains:
        expected = round(d.weight * declared_total)
        if d.items != expected:
            errors.append(
                f"{d.id}: items={d.items} but round(weight x {declared_total}) = {expected}"
            )

    seen_domains: set[str] = set()
    seen_objectives: set[str] = set()
    for d in bp.domains:
        if d.id in seen_domains:
            errors.append(f"duplicate domain id {d.id}")
        seen_domains.add(d.id)
        expected_prefix = d.id[1:] + "."
        for o in d.objectives:
            if o.id in seen_objectives:
                errors.append(f"duplicate objective id {o.id}")
            seen_objectives.add(o.id)
            if not o.id.startswith(expected_prefix):
                errors.append(f"objective {o.id} does not belong to domain {d.id}")

    return errors
