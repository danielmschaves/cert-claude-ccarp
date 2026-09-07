"""Argument parsing and exit codes. No logic lives here."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from . import bank as bank_mod
from . import blueprint as blueprint_mod
from . import progress as progress_mod
from . import render, report, runner, selection, stats, validate
from .config import DEFAULT_DRILL_N


def _cmd_validate(args: argparse.Namespace) -> int:
    errors, warnings, summary = validate.run()
    render.validate_report(errors, warnings, summary)
    return 1 if errors else 0


def _cmd_drill(args: argparse.Namespace) -> int:
    bank = bank_mod.load().filter(domain=args.domain, obj=args.obj)
    if not len(bank):
        render.err("no items match -- author some in banks/ first")
        return 1

    attempts = progress_mod.read()
    items, shortfall = selection.select(bank, attempts, datetime.now(UTC), args.n)
    render.shortfall(shortfall)
    if not items:
        return 0

    session = runner.new_session_id("drill")
    try:
        results = runner.run(items, mode="drill", session=session)
    except KeyboardInterrupt:
        render.out()
        results = []
    render.session_summary("drill", results)
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    bp = blueprint_mod.load()
    reports = report.build(bp, bank_mod.load())
    if args.markdown:
        render.bank_report_markdown(reports)
    else:
        render.bank_report(reports)
    return 0


def _cmd_stats(args: argparse.Namespace) -> int:
    bp = blueprint_mod.load()
    bank = bank_mod.load()
    render.stats_report(
        stats.build(bp, bank, progress_mod.read(), datetime.now(UTC)),
        by_objective=args.by_objective,
    )
    return 0


def _cmd_review(args: argparse.Namespace) -> int:
    """Tier-free on purpose: you asked for the wrong ones, so cooldowns do not apply."""
    bank = bank_mod.load().filter(domain=args.domain, obj=args.obj)
    attempts = progress_mod.read()
    qids = stats.wrong_qids(attempts, bank)[: args.n]
    if not qids:
        render.out("nothing to review -- no item's latest attempt was incorrect")
        return 0

    items = [bank.by_qid(q) for q in qids]
    try:
        results = runner.run(items, mode="review", session=runner.new_session_id("review"))
    except KeyboardInterrupt:
        render.out()
        results = []
    render.session_summary("review", results)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ccarp",
        description="Drill the Claude Certified Architect - Professional exam.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="check blueprint and banks")
    p_validate.set_defaults(func=_cmd_validate)

    p_report = sub.add_parser("report", help="bank composition and quality tells")
    p_report.add_argument("--markdown", action="store_true", help="emit a markdown table")
    p_report.set_defaults(func=_cmd_report)

    p_drill = sub.add_parser("drill", help="drill questions, newest material first")
    p_drill.add_argument("-n", type=int, default=DEFAULT_DRILL_N, help="how many items")
    p_drill.add_argument("--domain", help="restrict to one domain, e.g. d3")
    p_drill.add_argument("--obj", help="restrict to one objective, e.g. 3.5")
    p_drill.set_defaults(func=_cmd_drill)

    p_stats = sub.add_parser("stats", help="coverage, mastery and correctness")
    p_stats.add_argument("--by-objective", action="store_true", help="break out all 38 objectives")
    p_stats.set_defaults(func=_cmd_stats)

    p_review = sub.add_parser("review", help="re-drill items you got wrong")
    p_review.add_argument("--wrong", action="store_true", help="(default; accepted for symmetry)")
    p_review.add_argument("-n", type=int, default=DEFAULT_DRILL_N, help="how many items")
    p_review.add_argument("--domain", help="restrict to one domain, e.g. d3")
    p_review.add_argument("--obj", help="restrict to one objective, e.g. 3.5")
    p_review.set_defaults(func=_cmd_review)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
