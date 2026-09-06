"""Argument parsing and exit codes. No logic lives here."""

from __future__ import annotations

import argparse
import sys

from . import render, validate


def _cmd_validate(args: argparse.Namespace) -> int:
    errors, warnings, summary = validate.run()
    render.validate_report(errors, warnings, summary)
    return 1 if errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ccarp",
        description="Drill the Claude Certified Architect - Professional exam.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="check blueprint and banks")
    p_validate.set_defaults(func=_cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
