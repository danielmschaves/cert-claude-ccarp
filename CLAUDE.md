# ccarp — Claude Certified Architect – Professional drill tool

Local CLI for drilling the CCARP exam. Single user, no server, no database.

## Non-negotiables

1. **Questions are data.** They live in `banks/d1.json` … `banks/d7.json`. A stem, option,
   answer key or rationale anywhere in `src/` is a bug — including in tests, which use
   `tests/fixtures/`.
2. **`progress.jsonl` is the only state.** Append-only, committed. Never rewrite, reorder,
   compact or delete a line. Every statistic and selection decision is derived at read time. No
   caches, no derived files, no SQLite.
3. **`blueprint.json` is the source of truth** for domains, weights, objectives and item counts.
   Never hardcode a weight or count — read it. `config.py` holds tunables; the blueprint holds
   the exam's own facts.
4. **`render.py` is the only module that may touch stdin/stdout.**
5. **`selection.py` and `stats.py` are pure** functions of `(bank, attempts, now)`. Pass `now`
   in; never call `datetime.now()` inside them.
6. **Zero runtime dependencies.** Stdlib only; dev-only `pytest`, `ruff`. A new runtime dep needs
   a reason in the commit message.

## Exam facts (Guide v1.0, July 2026)

63 items · 120 min · multiple-choice and multiple-response with the select count stated per item
· standalone items, no linked scenarios · criterion-referenced · scaled 100–1000 · cut 720 ·
score report gives percent-correct by domain.

**Re-verify at trust.anthropic.com / Partner Academy before trusting any of this.** When it
changes, edit `blueprint.json` and bump `retrieved` — never patch a number into code.

## The scaled score is an estimate and must always say so

The raw-to-scaled mapping is **not published**. We use `scaled_est = round(100 + 900 * pct)`.

- Always name it `scaled_score_est`. Never `score`, never `scaled_score`.
- Always beside the raw percent, raw first.
- Always print the caveat and the implied raw threshold (~44/63 under this estimator).
- **Never print PASS or FAIL.** We do not know the raw cut.

## Item schema

```json
{
  "qid": "d3-014",
  "obj": "3.5",
  "rev": 1,
  "format": "multiple_response",
  "select_n": 2,
  "stem": "Two to three sentences of concrete situation.",
  "principle": "progressive disclosure",
  "options": [
    {"key": "A", "text": "...", "correct": true,  "rationale": "why this is best here"},
    {"key": "B", "text": "...", "correct": false, "rationale": "real practice, wrong here because ..."}
  ]
}
```

`qid` is globally unique, `^d[1-7]-\d{3}$`, and its domain must match both the file it lives in
and the `obj` prefix. **Bump `rev` whenever the stem, options or key change** — attempts at an
older `rev` still count for coverage but no longer count toward mastery.

## Authoring rules

- 2–3 sentences of **concrete situation**. A named system, a real constraint. No abstractions.
- **Superlative stem**: "best reduces", "most likely first place to investigate". The task is
  ranking real options, not recalling a fact.
- **One best answer**, defensible from the named `principle`. Can't name the principle → the
  item isn't ready.
- **Distractors are real practices that are inferior *here*.** Never falsehoods, never
  eliminable without reading the scenario. If an option can be struck on sight, rewrite it.
- **Analyze/Evaluate only.** If the answer is recallable from a doc page, cut the item.
- **No volatile figures**: no prices, context sizes, model IDs, dated benchmarks. For D2
  model-selection items name model *roles* ("the fastest small model", "the frontier reasoning
  model"), never products.
- **No all-of-the-above / none-of-the-above.**
- Every option carries a rationale, including the correct one. The rationales are the study
  material; the score is not.

## Progress rows

```json
{"ts":"2026-09-06T14:02:11Z","session":"drill-20260906T1402Z","mode":"drill",
 "qid":"d3-014","obj":"3.5","rev":1,"correct":true,"confidence":"sure","secs":47}
```

One row per item, appended and fsynced the moment the item is done. Unknown keys ignored on
read; a malformed line warns and is skipped, never crashes a session.

**MR items score all-or-nothing** — every correct option and no incorrect ones. Say so in the UI
on reveal.

**In a timed exam every served item gets a row at grading time.** Items never reached are written
`correct: false, confidence: "guess", secs: 0`, and the report says `N items unanswered (scored
incorrect)`. This is the one place a row is written at grading rather than immediately.

## Selection tiers

`unseen` → `wrong` (24h) → `shaky` = right-but-guessed (72h) → `solid` = right+sure (14d) →
`retired` after two consecutive confident-corrects (30d, then demoted back on any slip).

Fill from the top tier down. **Fall through only when a tier is dry** — never blend to pad a
count. When the tiers can't fill the run, serve fewer and say exactly how short and when the next
item frees up:
`served 7 of 20 · 13 short · 41 in cooldown · soonest in 6h12m (wrong)`. Never silently repeat.

Cooldowns are **elapsed UTC hours**, not calendar days. `exam` ignores tiers and draws the
blueprint quota uniformly at random per domain.

## Stats

Report **coverage and mastery together, always** — either alone misleads.
`coverage` = distinct items seen ÷ bank. `mastery` = latest attempt correct **and** sure ÷ bank.
Correctness lifetime **and** last-50.

## Commands

```
uv run ccarp validate            # blueprint sums, schema, referential integrity
uv run ccarp drill [-n 20] [--domain d3] [--obj 3.5]
uv run ccarp stats [--by-objective]
uv run ccarp exam --timed
uv run ccarp review --wrong
```

`validate` exits 1 on structural error, 0 on lint warns, and must pass on empty banks.
`validate --strict` promotes authoring warnings to errors — that is what CI gates on.

Lint has two halves. Per-item rules read one item (stem length, superlative present, no
all/none-of-the-above, no volatile figures, option count, per-item length ratio). **Distribution
rules read a whole domain** and catch what no single item reveals: answer keys clustered on one
letter, the correct option being longest too often, one `principle` carrying a domain, an
objective left empty in a full domain. Those are the tells an author drifts into at volume.

Not checkable by machine, and therefore still on you: whether a distractor is a real practice
that is inferior *in this scenario*.

## Build state

M1 `validate` ✅ · M2 `drill` ✅ (full 5-tier ladder) · A0 CI + `report` ✅ · A1 `stats` +
`review --wrong` ✅ · A2 `lint` ✅ · A3 `exam --timed` ✅ · then six authoring branches.

`exam` refuses to start until every domain meets its blueprint quota, so it stays blocked
until the authoring branches land. That is deliberate: a 58-item mock is not a mock.

Banks: **d1 has 10 items; d2–d7 are empty.** Authoring the remaining six domains is the
long pole, and `validate` reports the per-domain gap on every run.

## Conventions

- Python ≥ 3.11, `uv` for everything. `uv run`, never a bare `python`.
- `ts` is ISO-8601 UTC with `Z`.
- Confidence (`sure|unsure|guess`) is captured **before** reveal. The loop must make this
  structurally impossible to get wrong.
- `Ctrl-C` mid-session loses nothing and leaves valid JSONL.
- Commit `progress.jsonl` with the work; `.gitattributes` sets `merge=union` on it.
