"""The only module that touches stdin/stdout.

Keeping every print and input here is what makes runner.py testable: the loop is handed
an object with these methods and never knows whether a human is on the other end.
"""

from __future__ import annotations

import sys

BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def _supports_colour() -> bool:
    return sys.stdout.isatty()


def c(text: str, code: str) -> str:
    return f"{code}{text}{RESET}" if _supports_colour() else text


def out(line: str = "") -> None:
    print(line)


def err(line: str) -> None:
    print(line, file=sys.stderr)


def validate_report(errors: list[str], warnings: list[str], summary: dict) -> None:
    out(f"{c('blueprint', BOLD)}  "
        f"{summary['blueprint_items']} items across {summary['objectives']} objectives")

    per_domain = summary["per_domain"]
    total = summary["bank_total"]
    out(f"{c('banks', BOLD)}      {total} items  "
        + "  ".join(f"{d}:{n}" for d, n in sorted(per_domain.items())))

    if summary["exam_ready"]:
        out(f"{c('exam-ready', BOLD)} yes")
    else:
        gaps = "  ".join(
            f"{d} {have}/{need}" for d, (have, need) in sorted(summary["shortfalls"].items())
        )
        out(f"{c('exam-ready', BOLD)} {c('no', YELLOW)}  {gaps}")

    for w in warnings:
        out(f"{c('warn', YELLOW)}  {w}")
    for e in errors:
        err(f"{c('error', RED)} {e}")

    out()
    if errors:
        out(c(f"FAILED with {len(errors)} error(s)", RED))
    else:
        suffix = f" ({len(warnings)} warning(s))" if warnings else ""
        out(c(f"OK{suffix}", GREEN))
