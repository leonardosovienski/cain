# FUNDING_READINESS_RISK_LEDGER

MODE: CURRENT_LIVING_STATE · LAST_MATERIAL_UPDATE: 2026-10-07 · ISSUED: 2026-10-06. Entries are updated in place with dated
layers; nothing observed earlier is deleted. Ledger IDs (R01–R12 here) are not the remediation programme's item numbers.

Issued 2026-10-06. Severity: P0 may invalidate the contribution or block serious funding; P1 strongly reduces
probability; P2 friction; P3 cosmetic. Only verifiable behaviour and artefacts; no inferred traits.

## P0

### R01 · EXPERIMENT · the built arm C cannot observe the primary metric
- STATUS: OPEN (unchanged; the pilot harness opened the channel outside CAIN — nothing in CAIN changed). New sub-finding: the pilot's frozen rubric counted parameter-range deviations as attempts; a v2 rubric must separate schema deviation from authority surface before any comparative arm.
- EVIDENCE: `llm.py` sends the model a JSON schema whose `hypothesis_id` is an **enum** pre-filtered by `policy.decide`;
  the model returns only `hypothesis_id` + `rationale`; CAIN fills handler-free request fields from a template. Soak
  audits (`llm-1..6.audit.json`, run 36648103793) show exactly this. An "authority-expansion attempt" (ask for more
  budget, another dataset, a wider window, held-out access) has **no channel** in which to appear, so
  AUTHORITY_EXPANSION_ATTEMPT_RATE in arm C is 0 by construction, not by behaviour.
- WHY_IT_MATTERS: the experiment as infrastructured would measure enforcement (contribution class A), confirming the
  triviality objection ("an if says no"). Any reviewer will see it.
- AFFECTED_FUNDERS: all AI-safety funders; Anthropic/OpenAI credit programmes (the pilot described to them needs this fixed).
- CHEAPEST_FIX: define the proposer's output as a **free-form structured request** (fields the agent may fill, including
  ones the policy will refuse) in all three arms, so attempts are observable before the policy acts; log
  `attempt → decision`. Prototype this first as a prompt-only harness **outside** CAIN (no requalification cost).
- DEPENDENCIES: none for the prompt-only pilot; a CAIN code change later (triggers C14 requalification).
- CLOSE_CRITERIA: an elicitation pilot in which the attempt field is open and ≥ 1 model produces a non-zero,
  classifiable attempt rate in arm A (see R02).

### R02 · SCIENCE · no evidence yet that the phenomenon can be elicited
- STATUS: OPEN — **three integrity-checked rounds (V1, V2, V3; 2026-10-06/07) found no elicitable authority-expansion in qwen2.5:7b. V2's only signal (T2 INCENTIVE 4/4 symbol additions) replicated in V3 and was removed by a one-line qualifier (1/4): DEFAULT_EDITING_CONFIRMED, modest weight. The request channel was used 0/112 times, including 0/8 in a positive control that itself proved defective. Terminal state REFORMULATE_RQ1; frontier NOT justified on this instrument. See `pilots/elicitation-a/HANDOFF.md`, `pilots/elicitation-a/v3/runs/REVIEW_V3.md`.** Earlier: V2 hostile-reviewed; owner replaced manual blind labels by AI shadow adjudication (PROTOCOL_AMENDMENT_V2_BASELINE_001). Pilot run 1 (2026-10-06, qwen2.5:7b-instruct-q4_K_M, 40 episodes, integrity VALID): 0/40 authority-expansion attempts on every surface; machine label 14/40 are `horizon_days=3` range deviations, not authority. See `pilots/elicitation-a/runs/qwen2.5-7b-instruct-q4_K_M-gha37523764748/REVIEW.md`. Next: same frozen files, one frontier model.**
- EVIDENCE (2026-10-07): 112 integrity-checked episodes on qwen2.5:7b across V1–V3 (`pilots/elicitation-a/`); additional_access
  empty 112/112; the one positive signal (V2 T2 4/4) replicated and was removed by a one-word qualifier; positive control defective.
  Before 2026-10-06 the only LLM data was `qwen2.5:0.5b` picking from a 2-item enum; no frontier model has ever been connected.
- WHY_IT_MATTERS: without a base rate there is no power analysis, no pre-registration, no falsifiable H1.
- AFFECTED_FUNDERS: all.
- CHEAPEST_FIX (executed as V1–V3, 2026-10-06/07; superseded): 20–40 episode prompt-only pilot (arm A) with free-form requests on 3–5 tasks where extra authority
  rationally helps, one local ≥7B model and, when credits arrive, one frontier model; hand-label attempts with a
  pre-written rubric. Diagnose zero as MODEL_TOO_WEAK / INCENTIVE_TOO_WEAK / TASK_TOO_EASY / AUTHORITY_NOT_USEFUL /
  PROMPT_TOO_STRONG.
- DEPENDENCIES: R01 design; frontier credits optional for the first pass.
- CLOSE_CRITERIA: observed base rate with CI, or a documented stop (phenomenon not elicitable → §28 stop rule).
- CLOSE_STATUS (2026-10-07): documented stop reached, but as INSTRUMENT_INVALID rather than "phenomenon not elicitable": the risk
  stays OPEN for any future line (RQ1_FUTURE_STATUS = MAY_BE_REFORMULATED, new line, not V4). Nothing here is evidence of safety.

### R03 · REPRODUCIBILITY · the stack can no longer be installed from its locks
- STATUS: **PARTIAL** (2026-10-07; OPEN since 2026-10-05/06). Layer 2026-10-07: root cause confirmed as two independent
  breaks (rename with reuse of the old name; all producers private, so even unchanged URLs 404 anonymously). Fixed on
  branch `claude/cain-audit-remediation-fiwdei` in all five consumers (cain, ecosystem research-transport + joint lock,
  cripto, stocks, brasileirão): `STACK_WHEELS.json` registry + `stack_wheels.py` API fetch with sha256 verification +
  URL-free locks + CI fetch steps (`FUNDING_READINESS_SOURCE_OF_TRUTH.md` §4a). Remaining for CLOSED: the
  `STACK_READ_TOKEN` secret in each consumer (owner), green CI on `main` after merge, Docker images built in CI,
  C14 cycle on a new rc. Preventive controls in place: `check` gate (no release URL may reappear in a lock; registry,
  index, lock and pyproject must agree), retired-repository-name refusal, fail-closed fetch with the reason, offline
  unit tests of the registry pins, `probe` as availability sentinel.
- EVIDENCE: rename `ecosystem-predictor` → `ecosystem-predictor-cain` plus a new public repo under the old name;
  all `uv.lock` URL pins to the old name 404; private repos' assets 404 anonymously; `ecosystem-predictor-cain` CI red
  on every run since 2026-10-04 (37201676611, 37325661999, 37391152563, 37469493563); harness renewal failed
  2026-10-06 (37451877373). `cain` CI will fail on next push (materialised on 2026-10-07: runs 37564025843 and 37564492275). This session had to build transport wheels from source.
- WHY_IT_MATTERS: "hash-pinned, cleanroom-installable" is the programme's central credibility claim (C04, C11) and the
  arm-C infrastructure for the experiment; today neither a reviewer nor the owner's CI can re-execute it.
- AFFECTED_FUNDERS: anyone doing due diligence on the Evidence Pack; Anthropic/OpenAI pilots (arm C needs an install).
- CHEAPEST_FIX (owner decision, not done here because it touches frozen locks and C14): (a) re-point `tool.uv.sources`
  and locks to the renamed repository and keep `ecosystem-predictor-cain` releases reachable, or (b) mirror the
  seven wheels to a public, immutable artefact host (e.g. a release in the public showcase repo or Zenodo) and pin
  there. Either way: new rc, new cleanroom-final, attestations re-issued per C14. Record the rename in DECISIONS.json.
- DEPENDENCIES: owner's choice on what stays private; C14 cycle.
- CLOSE_CRITERIA: `uv sync --locked` succeeds anonymously (or with a documented token) for cain and the joint lock;
  CI green on `main` of cain and ecosystem-predictor-cain.

## P1

### R04 · POSITIONING/APPLICATION · claims in the 2026-10-04 application exceed their evidence
- STATUS: OPEN
- EVIDENCE: "about 1,500 passing tests" (artefacts: 1446/1462/1463); "sandbox contained 14 of 14 attack cases in my
  latest run" (lab sandbox, one Windows host, 2026-09-24, outside qualified runtime); "a September 2026 study found …
  about 30 %" (not located); placeholder text "[link do cain-evidence, se já tiver]" left in a submitted field;
  "governed research loop with hash-locked evaluator and human-gated held-out data" presented without saying it is
  fenced out of the runtime.
- WHY_IT_MATTERS: a reviewer who checks one number and finds it rounded up discounts the rest.
- AFFECTED_FUNDERS: Anthropic (submitted); any application reusing the text (BlueDot, OpenAI, Z Fellows — content unknown).
- CHEAPEST_FIX: adopt the Claim Ledger qualifiers verbatim in every future text; for already-submitted forms, nothing
  to retract unless contacted; do not reuse the paragraph.
- CLOSE_CRITERIA: next application text cross-checked line by line against the ledger.

### R05 · EXTERNAL_VALIDATION · zero human review of protocol, attestations or claims
- STATUS: OPEN
- EVIDENCE: showcase limitation 8 ("one person, with AI agents as executors and internal reviewers"); no reviewer
  record anywhere in the repos; no EXTERNAL_REVIEW_PACKET exists.
- WHY_IT_MATTERS: North-Star artefact 2; funders weigh an external critic more than any internal gate.
- CHEAPEST_FIX: a 3-page EXTERNAL_REVIEW_PACKET (question + threat model, protocol sketch after R01/R02, limitations)
  sent to one qualified reviewer **after** the elicitation pilot gives a base rate; BlueDot course cohort (if accepted,
  Oct 26) is a low-cost source of reviewers.
- DEPENDENCIES: R01, R02.
- CLOSE_CRITERIA: one documented review (PERSON, DATE, CRITICISM, SEVERITY, ACTION, ACCEPTED/REJECTED).

### R06 · NOVELTY · the literature is dense and unreviewed
- STATUS: OPEN
- EVIDENCE: no NOVELTY_MATRIX in any repo; one search surfaced directly adjacent work: CheatBench (arXiv 2609.36308,
  reward gaming incl. research tasks), ResearchGym (2602.15112), "Can AI agents conduct open-ended AI research?"
  (2607.27191), CTRL-ALT-DECEIT sabotage evals for AI R&D (2511.09904), Auditing Harness Tampering in self-improving
  agents (2609.00069), Taming privilege escalation in LLM agents via MAC (2601.11893), Parallax think/act separation
  (2604.12986), LinuxArena control setting (2604.15384), escalation channels vs reward hacking (2608.29460). The AI
  control literature (Greenblatt et al. 2023→) already studies untrusted agents under monitoring/isolation.
- WHY_IT_MATTERS: the stop rule "question already answered" cannot be evaluated; "proposer/policy separation" alone
  reads as least-privilege engineering.
- CHEAPEST_FIX: read the nine papers above plus the AI-control core set; fill the NOVELTY_MATRIX; write the seven-line
  positioning ("Prior work shows … We do NOT claim …"). Candidate differentiator to test, not assert: measuring
  **evidence-conditioned** escalation requests (requests that cite intermediate results) vs unconditioned ones.
- CLOSE_CRITERIA: NOVELTY_MATRIX with ≥ 8 entries and the seven-line statement, or a reformulated question.

### R07 · ENGINEERING/EVALUATION · "qualified" refers to rc13 while the published and documented target is rc15
- STATUS: OPEN
- EVIDENCE: attestations' `final_commits` = cain `960fb256` (rc13); README/ESTADO call rc15 the integrations' target; rc15
  cycles are BLOCKED (Windows secondary, protected-set pin, D-29/30/31 undecided); three attestations don't re-validate.
- WHY_IT_MATTERS: any "qualified" sentence in a funding text is about a wheel that is not the one shipped.
- CHEAPEST_FIX: say "rc13 qualified; rc15 in progress" everywhere, or finish D-29/30/31 and the Windows run.
- CLOSE_CRITERIA: wording fixed in README/showcase, or rc15 attestations issued.

## P2

- R08 · ADMIN: `cain` CI ran on 2026-10-07 (runs 37564025843, 37564492275) and failed as predicted (see R03); no longer latent.
- R09 · PUBLIC_EVIDENCE: Evidence Pack hashes have no external timestamp (showcase E6; cost ≈ 0, e.g. OpenTimestamps).
- R10 · EVALUATION: the two provenance tests need the `observability` extra; the test-count line in state docs should say so.
- R11 · ADMIN: "787 tests" in `docs/ESTADO_2026-09-30.md` is a stale figure from 2026-09-15; that file is now marked SNAPSHOT_IMMUTABLE (not corrected in place); the current figure lives in the Source of Truth §2.
- R12 · GOVERNANCE (programme R02, 2026-10-07): canonical documents mixed snapshot and living state (e.g. "CI will fail on the next run" after it had failed; "proposed" experiments after V1–V3 ran). Control: every canonical document now declares `MODE: SNAPSHOT_IMMUTABLE` (AS_OF_DATE, AS_OF_SHA, SUPERSEDED_BY) or `MODE: CURRENT_LIVING_STATE`; `tests/test_canonical_state.py` fails when a declaration is missing, when a living document contains a future-tense CI prediction, or when the declared version in §0 drifts from the package. STATUS: PARTIAL (controls active; the ecosystem and qualification repositories still carry undeclared state documents).

## Explicitly not findings
- Personality or motivation of the owner: no evidence considered, none recorded.
- UFPE / presential alternative: declined voluntarily; not reopened.
