"""Load banks/d*.json. Never writes. An empty bank is valid -- that is milestone one."""

from __future__ import annotations

import json
from pathlib import Path

from .config import BANKS_DIR
from .models import Bank, Item, Option

DOMAIN_IDS = tuple(f"d{n}" for n in range(1, 8))


def _item_from_json(raw: dict) -> Item:
    options = tuple(
        Option(
            key=o["key"],
            text=o["text"],
            correct=bool(o.get("correct", False)),
            rationale=o.get("rationale", ""),
        )
        for o in raw["options"]
    )
    fmt = raw.get("format", "multiple_choice")
    return Item(
        qid=raw["qid"],
        obj=raw["obj"],
        rev=int(raw.get("rev", 1)),
        format=fmt,
        stem=raw["stem"],
        principle=raw.get("principle", ""),
        options=options,
        select_n=int(raw.get("select_n", 1)),
    )


def load_domain(domain_id: str, banks_dir: Path | None = None) -> tuple[Bank, str | None]:
    """Return (bank, declared_domain). Missing file yields an empty bank, not an error."""
    path = Path(banks_dir or BANKS_DIR) / f"{domain_id}.json"
    if not path.exists():
        return Bank(), None
    raw = json.loads(path.read_text())
    items = tuple(_item_from_json(i) for i in raw.get("items", []))
    return Bank(items), raw.get("domain")


def load(banks_dir: Path | None = None) -> Bank:
    items: list[Item] = []
    for domain_id in DOMAIN_IDS:
        bank, _ = load_domain(domain_id, banks_dir)
        items.extend(bank.items)
    return Bank(tuple(items))
