# ccarp

Drill tool for the **Anthropic Claude Certified Architect – Professional** exam.

Local, single-user, zero runtime dependencies. Questions are data; your attempt history is one
append-only JSONL file you commit alongside them.

```bash
uv run ccarp validate            # check blueprint + banks
uv run ccarp drill -n 10         # drill, newest material first
uv run ccarp drill --domain d3   # or narrow to one domain / objective
```

## How it picks questions

Each run drains tiers in order and falls to the next **only when the current one is dry**, so a
repeat run serves new material rather than the same items:

| tier | meaning | cooldown |
|---|---|---|
| `unseen` | never attempted | — |
| `wrong` | last attempt incorrect | 24h |
| `shaky` | correct but not confident | 72h |
| `solid` | correct and confident | 14d |
| `retired` | two confident-corrects in a row | 30d, then demoted on any slip |

When the tiers can't fill your run it serves fewer and tells you how short it is and when the
next item frees up. It never silently repeats an item.

## Exam facts

63 items · 120 minutes · criterion-referenced · scaled 100–1000 · cut 720. Sourced from Guide
v1.0 (July 2026) — **re-verify at trust.anthropic.com / Partner Academy.** The blueprint lives in
`blueprint.json`; `validate` asserts its weights sum to 100%, its item counts sum to 63, and it
declares 38 objectives.

The raw-to-scaled mapping is **not published.** Any scaled figure this tool shows is named
`scaled_score_est`, is shown beside the raw percent, and is never turned into a pass/fail verdict.

## Layout

```
blueprint.json     source of truth for domains, weights, objectives
banks/dN.json      the questions
progress.jsonl     append-only attempt log (committed)
src/ccarp/         the tool
```

See `CLAUDE.md` for the authoring rules and design invariants.
