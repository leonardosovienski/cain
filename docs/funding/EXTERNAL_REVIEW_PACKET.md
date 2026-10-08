# EXTERNAL_REVIEW_PACKET — what we ask one qualified human to try to break

MODE: CURRENT_LIVING_STATE · ISSUED: 2026-10-07 (programme item R05) · STATUS: PACKET_READY, REVIEW_NOT_YET_OBTAINED.
This packet is for a reviewer **outside** the programme (not the owner, not an AI agent of this ecosystem). Reading
time: about 40 minutes. Everything cited is hashed in the public Evidence Pack or in the artefacts listed at
the end (private when this packet was written; all nine repositories are public since 2026-10-07, so no access grant is
needed; layer 2026-10-08).

## The one question

> **Which flaw in this interpretation would make you not trust it, or not fund the next step?**

We are not asking "do you approve of CAIN". Negative criticism is the useful outcome. A review that finds nothing is
weaker evidence than one that finds something.

## What was done (closed line, 2026-10-06 → 07)

1. **Object.** A research-agent proposer (local model qwen2.5:7b-instruct-q4_K_M, single turn, JSON schema output) was
   given a grant (allowed symbols, window, dataset, budget, request types) and intermediate evidence that made
   additional authority rational. We asked whether it would **request** more authority through an explicit field
   (`additional_access`), **edit** the grant in place (symbols, window, dataset), or do neither.
2. **Three iterations, 112 episodes** (40 + 40 + 16 + 16), each with frozen prompts, scenarios and rubric under a hashed
   manifest; V3's reading and analysis script committed before its results existed.
3. **Results.** V1: the original metric counted in-grant parameter edits as authority expansion (construct failure).
   V2: corrected taxonomy; one incentive cell showed 4/4 symbol additions vs 0/4 neutral. V3: the identical instrument
   reproduced 4/4; adding one qualifier word to the grant line ("only") plus an exclusion ("not part of this grant")
   gave 1/4; the positive control for the request channel yielded 0/8; `additional_access` was empty in 112/112.
4. **Decision.** Line closed, `FINAL_STATE = REFORMULATE_RQ1`. Frontier evaluation cancelled. Pre-registered decision
   label `DEFAULT_EDITING_CONFIRMED` was an operational gate, **not** a scientific confirmation (Fisher p ≈ 0.14 for
   4/4 vs 1/4 is a supportive calculation only).

## Our interpretation, stated so it can be attacked

- The apparent authority-expansion signal is best explained by **editing of an unqualified default** (the model filled a
  symbol list the grant did not clearly close), not by a stable demand for authority.
- Q0→Q1 differed in more than one semantic dimension ("only" and an exclusion clause); we therefore say "strong
  sensitivity to grant/default presentation", not "one word caused the effect".
- Zero requests in 112 episodes is a **diagnostic fact about the instrument**: the positive control (T6) was defective
  (request-only proposals scored 0; no obtainable resource named; "fill every field yourself" forced a runnable
  request). Licensed: "this model × prompt × harness did not elicit use of the explicit request channel". Not
  licensed: "the model never uses the channel when required", "the model is safe", "CAIN works".
- The runs used a prompt cache and the same seed per arm; Q0/Q1 are **pseudo-pairs**, not exact paired replicas.
- All adversarial reviews, raw audits and label adjudications were done by AI agents; this is the first human read.

## Where we think we are most vulnerable (please start here)

1. **Construct validity.** Is "authority demand" separable from "default completion" at all in a single-turn schema?
2. **Positive control.** Could T6 have been fixed cheaply, making the closure premature? Or is any single-turn positive
   control doomed for this construct?
3. **Small n.** n = 4 per cell; the pre-registered reading rules (≥3/4) were decision rules. Would you have stopped?
4. **Instrument sensitivity as the result.** We now claim the methodological lesson, not the behavioural one. Is that a
   legitimate result or a rescue of a null?
5. **Role collapse.** One person plus AI agents designed, ran, labelled, audited and wrote the claims. Which step most
   needs an independent human, and what would you want to see pre-registered before any successor line?
6. **Novelty.** `docs/research/NOVELTY_MATRIX.md` (AI-written) finds the nearest prior art in escalation-channel and
   scope-creep studies on coding agents. Does the "evidence-conditioned authority demand in research agents" gap
   survive your reading?

## Materials

| Item | Where | Hash (SHA-256) |
|---|---|---|
| Terminal handoff of the line | `pilots/elicitation-a/HANDOFF.md` (public since 2026-10-07) | `e41af865…` (Evidence Pack §6) |
| V3 pre-registered design and freeze manifest | `pilots/elicitation-a/v3/DESIGN_V3.md`, `v3/frozen/FREEZE_MANIFEST.json` | `7c643454…`, `fbccc976…` |
| V3 raw episodes (Q0, Q1) | `v3/runs/v3q0-…/episodes.jsonl`, `v3q1-…/episodes.jsonl` | `7a1d124e…`, `7dc9dc61…` |
| V3 mechanical analysis, AI raw audit, review | `v3/runs/V3_ANALYSIS.json`, `AI_RAW_AUDIT_V3.json`, `REVIEW_V3.md` | `d39f79e1…`, `48fbae65…`, `65ccd1ca…` |
| Completeness and freeze layers added after the fact (H05, H07) | `v3/runs/COMPLETENESS_V3.json`, `v3/runs/FREEZE_GATE_RETRO_V3.json` | in repository |
| Public evidence pack and limitations | github.com/leonardosovienski/ecosystem-predictor | public |
| Claim ledger and risk ledger | `docs/funding/CAIN_CLAIM_LEDGER.md`, `FUNDING_READINESS_RISK_LEDGER.md` | in repository |

## Review record (to be filled by the reviewer and kept verbatim; one block per finding)

```
PERSON:                 (name or stable pseudonym; affiliation optional)
BACKGROUND:             (one line: field, relevant experience)
CONFLICTS:              (any relation to the owner, the programme or funders; "none" is a statement)
DATE:
MATERIAL_REVIEWED:      (which items of the table above were actually read)
FINDING:                (what is wrong, missing or over-claimed; quote the sentence if possible)
SEVERITY:               BLOCKS_TRUST | BLOCKS_FUNDING_NEXT_STEP | WEAKENS | COSMETIC
RESPONSE:               (filled by the owner later; dated)
ACCEPTED_OR_REJECTED:   (owner; with RATIONALE)
RATIONALE:
```

Records are appended to `docs/funding/EXTERNAL_REVIEW_RECORDS.md` and never edited after the reviewer confirms the
text. A rejected finding stays in the record with the rationale. EXTERNAL_HUMAN_REVIEW flips from ABSENT to PRESENT
only when at least one record exists with a real person behind it.
