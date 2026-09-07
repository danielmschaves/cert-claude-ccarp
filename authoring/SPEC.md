# Authoring spec

The rules live in `CLAUDE.md` and are not repeated here. This file is the part `CLAUDE.md`
can't carry: **the pre-flight, worked examples, and the failure modes this bank has actually
suffered.** Read both before writing an item.

It is written to be usable two ways: by a session about to author items, and as the prompt
body if item generation is ever scripted against the API. That is the point of it being a
versioned file rather than a habit — the instruction is reviewable and changes by PR.

---

## Pre-flight — before writing anything

```bash
uv run ccarp report                       # where the bank stands, and its tells
uv run ccarp new-item --obj 3.5           # skeleton with the qid and answer key chosen for you
```

`new-item` proposes the **least-used answer key** in that domain and marks it correct in the
skeleton. Take the suggestion unless the item genuinely reads better another way. This is not
cosmetic — see failure mode 1.

Also read the existing items for that objective before writing. Two items testing the same
distinction with different nouns are worth less than one, and `report`'s `principle` column
only catches it once a domain is a third duplicated.

---

## The one rule no machine checks

> **Distractors are real practices that are inferior *in this scenario*.**

Everything else in `CLAUDE.md` is enforced by `validate --strict`. This one isn't, and it is
the rule that decides whether an item teaches anything. A distractor has to be something a
competent architect would actually propose — then lose to the correct answer *because of a
fact stated in the stem*.

The test: **can you name the sentence in the stem that rules this option out?** If not, either
the stem is missing that sentence or the option is a throwaway.

### Worked example — `d4-006`

> An assistant answering policy questions confidently states a policy that does not exist.
> **Retrieval logs show the correct policy document was returned for that query.** What is the
> most likely first place to investigate?

| option | why it's real | what rules it out |
|---|---|---|
| **C. The prompt may not require answers to come from sources** ✅ | evidence reached the model and went unused; also the cheapest hypothesis to falsify | — |
| A. Stale index | staleness is a top cause of confidently wrong answers | the log line: the right doc came back *for this query* |
| B. Model too small | capability mismatch does produce fabrication | not ruled out, but expensive to test when a cheaper hypothesis upstream is untested |
| D. Chunking split the policy | genuinely produces this kind of confident gap-filling | same log line — retrieval returned the document |

The bolded sentence is doing all the work. Without it, three of these are defensible and the
item has no single best answer.

### Distractors that fail this rule

- **Wrong in general, not wrong here.** "Lower the temperature so replies stay closer to the
  script" against a scope-boundary problem is fine; "disable retrieval" is not — nobody would
  propose it.
- **A strictly-worse restatement of the answer.** If B is A with a word changed, it's filler.
- **Strikeable on sight.** If a reader can eliminate it without the stem, cut it. This is what
  makes an item recall rather than analysis.
- **Correct in a neighbouring situation** is the target to aim for: reranking against a
  precision problem (`d3-008`), rotating a shared token against blast radius (`d3-004`),
  sampling transcripts against a rare-failure hunt (`d3-006`).

---

## Failure modes this bank has actually had

Both were introduced by a careful author and caught only by machine. Assume you will
reproduce them.

**1. Answer keys clustered on one letter.** D1 originally shipped with **91% of correct
answers on A**. The whole domain was scoreable without reading a stem. `new-item` now
proposes the least-used key; `lint` fails the build above 40%.

**2. Stems that never ask a question.** Nine of ten original D1 items were pure scenario —
situation, then options, no task posed. One escaped the superlative check only because
"**first**-notice-of-loss" contains "first". **Every stem ends in a question**, and the
superlative belongs in that question.

**3. The correct option being the longest.** A carefully written correct answer beside three
lazy distractors is a tell. Keep all options within roughly fifteen characters of each other;
`lint` fails a domain above 50%.

---

## Exit checklist

- [ ] Stem is 2–3 sentences and **ends in a superlative question**
- [ ] For every distractor, you can name the sentence in the stem that rules it out
- [ ] `principle` is a real named principle, not a restatement of the answer
- [ ] Every option has a rationale — distractors say what makes them real, *then* why they lose
- [ ] Options are close in length; the correct one is not the longest
- [ ] No prices, context sizes, model IDs, or dated figures — model **roles**, never products
- [ ] `uv run ccarp validate --strict` exits 0
- [ ] `uv run ccarp report` shows no new ⚠️ on the domain you touched

The rationales are the study material. Someone re-reading a missed item learns from them, not
from the score — so write them as the explanation you would want, not as justification.
