"""Every tunable number in the project. If a magic number appears elsewhere, move it here.

Exam facts (item count, weights, cut score) do NOT live here -- they belong to
blueprint.json, which is the source of truth for what the exam is.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BLUEPRINT_PATH = ROOT / "blueprint.json"
BANKS_DIR = ROOT / "banks"
PROGRESS_PATH = ROOT / "progress.jsonl"

QID_PATTERN = r"^d[1-7]-\d{3}$"
CONFIDENCE_LEVELS = ("sure", "unsure", "guess")

# Cooldowns in elapsed hours -- never calendar days. A 9pm drill must not block a 9am one.
COOLDOWN_HOURS = {
    "unseen": 0,
    "wrong": 24,
    "shaky": 72,
    "solid": 24 * 14,
    "retired": 24 * 30,
}

# Order tiers are drained in. Selection falls to the next tier only when the current is dry.
TIER_ORDER = ("unseen", "wrong", "shaky", "solid", "retired")

# M2 ships with the first two only; M4 swaps in the full ladder.
TIER_ORDER_M2 = ("unseen", "wrong")

DEFAULT_DRILL_N = 20
LAST_N_WINDOW = 50

# Warn when the blueprint citation goes stale.
BLUEPRINT_STALE_DAYS = 90
