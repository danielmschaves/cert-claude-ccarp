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


def _fmt_hours(hours: float) -> str:
    if hours < 1:
        return f"{int(hours * 60)}m"
    return f"{int(hours)}h{int((hours % 1) * 60):02d}m"


def shortfall(sf) -> None:
    """Say exactly how short the run is. Never silently serve fewer."""
    if sf.served == 0:
        head = c(f"nothing to serve (asked for {sf.requested})", YELLOW)
    elif sf.short:
        head = c(f"served {sf.served} of {sf.requested} · {sf.short} short", YELLOW)
    else:
        return
    tail = ""
    if sf.in_cooldown:
        tail = f" · {sf.in_cooldown} in cooldown"
        if sf.next_free_in is not None:
            tail += f" · soonest in {_fmt_hours(sf.next_free_in)} ({sf.next_free_tier})"
    out(head + tail)


def question(item, index: int, total: int) -> None:
    out()
    out(f"{c(f'[{index}/{total}]', DIM)} {c(item.qid, BOLD)} {c('· obj ' + item.obj, DIM)}")
    out()
    for line in _wrap(item.stem):
        out(f"  {line}")
    out()
    verb = f"Select {item.select_n}." if item.is_multiple_response else "Select 1."
    out(f"  {c(verb, DIM)}")
    out()
    for o in item.options:
        for i, line in enumerate(_wrap(o.text, width=88)):
            out(f"    {o.key})  {line}" if i == 0 else f"        {line}")
    out()


def _wrap(text: str, width: int = 92) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


def ask_answer(item) -> frozenset[str] | None:
    """Returns the chosen keys, or None if the user quit."""
    valid = {o.key.upper() for o in item.options}
    want = item.select_n
    prompt = "answer" if want == 1 else f"answer (choose {want}, e.g. a,c)"
    while True:
        try:
            raw = input(f"  {c(prompt + '>', BOLD)} ").strip()
        except EOFError:
            return None
        if raw.lower() in {"q", "quit"}:
            return None
        chosen = frozenset(p.strip().upper() for p in raw.replace(" ", ",").split(",") if p.strip())
        if not chosen:
            continue
        if not chosen <= valid:
            out(f"  {c('unknown option(s): ' + ', '.join(sorted(chosen - valid)), YELLOW)}")
            continue
        if len(chosen) != want:
            out(f"  {c(f'pick exactly {want}', YELLOW)}")
            continue
        return chosen


def ask_confidence() -> str | None:
    """Asked before the answer is revealed -- never after."""
    mapping = {"s": "sure", "u": "unsure", "g": "guess"}
    while True:
        try:
            raw = input(f"  {c('confidence (s)ure / (u)nsure / (g)uess>', BOLD)} ").strip().lower()
        except EOFError:
            return None
        if raw in {"q", "quit"}:
            return None
        if raw in mapping:
            return mapping[raw]
        if raw in mapping.values():
            return raw


def reveal(item, chosen: frozenset[str], correct: bool) -> None:
    out()
    keys = ", ".join(sorted(item.correct_keys))
    if correct:
        out(f"  {c('correct', GREEN)}")
    else:
        out(f"  {c('incorrect', RED)} — answer: {c(keys, BOLD)}")
        if item.is_multiple_response:
            out(f"  {c('multiple-response items score all-or-nothing', DIM)}")
    out(f"  {c('principle:', DIM)} {item.principle}")
    out()
    for o in item.options:
        mark = "✓" if o.correct else " "
        picked = "←" if o.key.upper() in chosen else " "
        colour = GREEN if o.correct else DIM
        head = c(f"  {mark} {picked} {o.key})", colour)
        for i, line in enumerate(_wrap(o.rationale, width=84)):
            out(f"{head} {line}" if i == 0 else f"         {line}")


def session_summary(mode: str, results: list[tuple[str, bool, str]]) -> None:
    out()
    if not results:
        out(c("no items answered", DIM))
        return
    n = len(results)
    right = sum(1 for _, ok, _ in results if ok)
    sure_right = sum(1 for _, ok, conf in results if ok and conf == "sure")
    out(c("─" * 60, DIM))
    out(f"{c(mode, BOLD)}  {right}/{n} correct ({right / n:.0%})  ·  "
        f"{sure_right} confident-correct")
    missed = [q for q, ok, _ in results if not ok]
    if missed:
        out(f"{c('missed:', DIM)} {' '.join(missed)}")


def _bar(have: int, need: int, width: int = 12) -> str:
    filled = min(width, round(width * have / need)) if need else width
    return "█" * filled + "·" * (width - filled)


def bank_report(reports: list) -> None:
    total_have = sum(r.have for r in reports)
    total_need = sum(r.need for r in reports)
    out(f"{c('bank', BOLD)}  {total_have}/{total_need} items")
    out()
    for r in reports:
        state = c("ok", GREEN) if r.complete else c(f"{r.need - r.have} short", YELLOW)
        out(f"  {c(r.domain_id, BOLD)} {_bar(r.have, r.need)} {r.have:>2}/{r.need:<2} {state}"
            f"   {c(r.name, DIM)}")
        if r.have:
            objs = f"obj {r.objectives_covered}/{r.objectives_total}"
            if r.uncovered:
                objs += c(f" (missing {', '.join(r.uncovered)})", YELLOW)
            keys = " ".join(f"{k}:{n}" for k, n in sorted(r.key_counts.items()))
            out(f"      {c(objs, DIM)}  {c('keys ' + keys, DIM)}  "
                f"{c(f'longest-correct {r.longest_share:.0%}', DIM)}  "
                f"{c(f'MR {r.multiple_response}', DIM)}")
    out()


def bank_report_markdown(reports: list) -> None:
    """Rendered into the CI job summary so quality is visible on the PR page."""
    total_have = sum(r.have for r in reports)
    total_need = sum(r.need for r in reports)
    out(f"## Bank report — {total_have}/{total_need} items\n")
    out("| domain | items | objectives | answer keys | correct-is-longest | MR | top principle |")
    out("|---|---|---|---|---|---|---|")
    for r in reports:
        items = f"{r.have}/{r.need}" + ("" if r.complete else f" ⚠️ {r.need - r.have} short")
        objs = f"{r.objectives_covered}/{r.objectives_total}"
        if r.uncovered:
            objs += f" ⚠️ missing {', '.join(r.uncovered)}"
        keys = " ".join(f"{k}:{n}" for k, n in sorted(r.key_counts.items())) or "—"
        if r.have and r.key_skew > 0.4:
            keys += f" ⚠️ {r.key_skew:.0%} on one key"
        longest = f"{r.longest_share:.0%}" if r.have else "—"
        if r.have and r.longest_share > 0.5:
            longest += " ⚠️"
        principle = "—"
        if r.top_principle:
            principle = f"{r.principle_share:.0%} share"
            if r.principle_share > 0.34:
                principle += " ⚠️"
        out(f"| `{r.domain_id}` | {items} | {objs} | {keys} | {longest} | {r.multiple_response} "
            f"| {principle} |")
    out()
    out("⚠️ marks a distribution tell worth a look, not a failure: answer keys clustered on one "
        "letter, the correct option being the longest too often, or one principle carrying too "
        "much of a domain. See `CLAUDE.md` for the authoring rules.")
