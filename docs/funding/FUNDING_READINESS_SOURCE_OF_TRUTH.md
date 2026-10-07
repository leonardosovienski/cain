# FUNDING_READINESS_SOURCE_OF_TRUTH — CAIN

MODE: CURRENT_LIVING_STATE · LAST_MATERIAL_UPDATE: 2026-10-07 (R01 merged in all consumers; R04 claim gate; R05 packet; R06 novelty scan; R07–R09 drafts; H05–H07 controls; see §0) · ISSUED: 2026-10-06
(cloud Linux session, read access to the nine stack repositories, GitHub API, owner's mailbox).
This file is the single canonical chain for "what is true today" about CAIN; dated documents it cites are
SNAPSHOT_IMMUTABLE and are never edited to match it. It changes whenever HEAD, CI state, scientific state, release state,
qualification state, funding state or the open findings change.
Scope: what is verifiable **today** about CAIN as the subject of a funding case. Predictors are covered only where a
CAIN claim depends on them. Every number carries scope, SHA, date, source and whether this session reproduced it.
Companion files (also CURRENT_LIVING_STATE): `CAIN_CLAIM_LEDGER.md`, `FUNDING_READINESS_RISK_LEDGER.md`.

## 0. Canonical answers (one chain, no archaeology)

| Question | Answer (2026-10-07) | Where it is checked |
|---|---|---|
| CURRENT_HEAD | `main` = `514a2ea1` (2026-10-07, PR #92, docs). The R01 remediation is on branch `claude/cain-audit-remediation-fiwdei`, not merged. | `git log origin/main -1` |
| DECLARED_VERSION | `0.4.13rc16` (`pyproject.toml`, `cain.__version__`); **not published** | `tests/test_canonical_state.py`, `tests/test_readme_version.py` |
| PUBLISHED_VERSION | `0.4.13rc15`, tag `v0.4.13rc15`, commit `ae00017a`, wheel sha256 `ff642b7271a7fcad18723b12bc7ebe29f0c2550ecfe178777b5c1481882aacf9` (re-downloaded through the API on 2026-10-07; matches `compat/uv.lock` of the ecosystem) | GitHub release; `ecosystem-predictor-cain/compat/STACK_WHEELS.json` |
| QUALIFIED_VERSION | `0.4.13rc13` (commit `960fb256`, transport 0.1.0rc6): the three integration attestations' `final_commits`. **rc15 is not qualified** (cycle D-27 `BLOCKED`); rc16 never built | §3; `predictor-qualification/qualification/integration-*/QUALIFICATION_ATTESTATION.json` |
| CI_STATE | `main`: **red** since the first push after the rename/privatisation (run 37564025843 at `44ae555b`, run 37564492275 at `514a2ea1`, 2026-10-07: `uv lock --check` 404 on the protocol wheel, no job reached pytest). Branch `claude/cain-audit-remediation-fiwdei`: fetch step fails closed with "set STACK_READ_TOKEN" until the owner creates that secret (run 37647716025) | §4 |
| SCIENTIFIC_STATE | Elicitation line V1–V3 **CLOSED** 2026-10-07, `FINAL_STATE = REFORMULATE_RQ1`; no behavioural effect of CAIN demonstrated; no frontier model run; EXTERNAL_HUMAN_REVIEW = ABSENT; NEW_RQ1_LINE = BLOCKED by the remediation programme gates | §3a; `pilots/elicitation-a/HANDOFF.md` (snapshot) |
| OPEN_RISKS | P0: R01 (observability), R02 (elicitation, documented stop), R03 (supply chain, PARTIAL since 2026-10-07). P1: R04–R07. P2: R08–R12 | `FUNDING_READINESS_RISK_LEDGER.md` |
| CLAIM_GATE_ACTIVE | **YES** (2026-10-07): `tools/claim_gate.py` + `docs/funding/CLAIM_INDEX.json` gate the README's current section and `tests/test_claim_gate.py` checks every ledger row; the public showcase runs `claims/claim_gate.py` in CI over all its documents (18 registered claims, banned phrases) | this repository; `ecosystem-predictor/.github/workflows/claim-gate.yml` |
| NEW_RQ1_LINE | **BLOCKED**: gates and their state in `docs/research/FUTURE_LINE_ENTRY_GATES.md` (observability, positive control and independence plan are DRAFT; novelty scan done, human read absent) | `docs/research/FUTURE_LINE_ENTRY_GATES.md`, `docs/research/NOVELTY_MATRIX.md` |
| EXTERNAL_HUMAN_REVIEW | **ABSENT**; packet ready for a reviewer: `docs/funding/EXTERNAL_REVIEW_PACKET.md` (records go to `EXTERNAL_REVIEW_RECORDS.md`) | §3a |
| PROCESS_CONTROLS | H05 freeze gate, H06 rubric layers, H07 completeness gate implemented in `pilots/elicitation-a/` and wired into the pilot workflow (2026-10-07); retro layers: V2 freeze PASS at its run commit; V3 freeze PASS with the manifest (note + workflow hash) edited after the freeze commit and frozen files byte-identical; V3 analysis INCOMPLETE (T6 circumvention count never emitted, recovered in REVIEW_V3) | `pilots/elicitation-a/{freeze_gate,rubric_layers,completeness_gate}.py`, `v3/runs/{FREEZE_GATE_RETRO_V3,COMPLETENESS_V3}.json`, `v2/runs/FREEZE_GATE_RETRO_V2.json` |
| EXTERNAL_TIMESTAMP | NOT_RUN: `tools/anchor_hashes.py` + workflow `timestamp.yml` (OpenTimestamps) ready; first stamp happens on `main` by workflow_dispatch | `docs/funding/ANCHORS.json` after the first run |
| SUPPLY_CHAIN_HEALTHY | **PARTIAL**: locks no longer carry release URLs (registry + API fetch in every consumer, §4a). On 2026-10-07 the owner made cain, ecosystem-predictor-cain, the three domains and predictor-qualification public again; `core-predictor` and `predictor-ops` were still private at the last check, so the domain consumers and the joint lock still need `STACK_READ_TOKEN` or those two repositories public; cain's own fetch (ecosystem-predictor-cain assets) resolves anonymously | §4a; CI reruns of 2026-10-07 |

## 1. Canonical code state

| Item | Value | Source | Reproduced here |
|---|---|---|---|
| Canonical branch | `main` of `leonardosovienski/cain` (private since early October 2026; verified again 2026-10-07) | GitHub API (`private: true`) | yes |
| HEAD | `514a2ea1` (2026-10-07, PR #92, docs); on 2026-10-06 it was `abeb1e6011537bea2d8a0d87334780f8370f1cbd` (PR #90) | `git log` | yes |
| Declared version | `0.4.13rc16`, **not published** | `pyproject.toml` | yes |
| Published wheel | `cain-research 0.4.13rc15`, tag `v0.4.13rc15`, commit `ae00017a` (2026-09-29), sha256 `ff642b72…` | release list via API; `docs/ESTADO_2026-09-30.md` | release exists (API); asset hash **not** re-downloaded (URL returns 404 anonymously, §4) |
| Code change since rc15 | one line (`src/cain/__init__.py` version bump); 7 commits, all docs/version | `git diff --stat ae00017a..HEAD -- src tests` | yes |
| DecisionPolicy | `src/cain/orchestration/policy.py`, `POLICY_VERSION = 2`, rules R01–R17, sha256 `3cea49644e1b2c6a15a550f2c76af8cfe8e4e002f58945a8ffde44b64004b8e6` at HEAD | file | yes |
| Protocol/transport pins | `predictor-research-protocol 2.0.0rc2`, `-transport 0.1.0rc7`, `-snapshot 1.0.2rc1`, `-bundle 1.0.1rc1`. On `main`: URL-pinned to `github.com/leonardosovienski/ecosystem-predictor/releases/...` (**all four 404**). On the remediation branch: registered in `STACK_WHEELS.json` (repository `ecosystem-predictor-cain`, tag, asset, sha256) and resolved by `uv.lock` from the local flat index `.stack-wheels` (§4) | `pyproject.toml`, `uv.lock`, `STACK_WHEELS.json` | yes |
| Entry points | `cain`, `cain-mcp`, `cain-stream` | `pyproject.toml` | yes |

## 2. Tests, CI, coverage

| NUMBER | SCOPE | SHA | DATE | COMMAND/SUITE | SOURCE | CURRENT_OR_HISTORICAL | REPRODUCED |
|---|---|---|---|---|---|---|---|
| 787 passed / 792 cases | QA of an installed 0.4.x wheel on Windows; 4 subprocess failures, 1 skip | pre-rc (mid-Sept) | 2026-09-15 | installed-QA suite | `docs/PUBLICACAO_20260915.md` | HISTORICAL | no |
| 787 tests | "technical validation" line in state doc; scope not stated | unstated | 2026-09-29 | unstated | `docs/ESTADO_2026-09-30.md` | HISTORICAL, **scope unresolved** (same figure as 09-15 while the suite had ~1446 tests by 09-28; likely a stale copy) | no |
| 1446 passed / 4 skipped | full `pytest -q`, Linux, Python 3.11/3.12/3.13 | `960fb256` (rc13) | 2026-09-28 | `uv sync --locked`; `pytest -q` | `predictor-qualification/qualification/shared/CAIN_EXTREME_20260928/REPORT.md` §2 | HISTORICAL | no |
| 1462 passed / 4 skipped, cov 87.76 % | same suite plus 14 new tests of cain#80 | `2807c23` | 2026-09-28 | `pytest -q --cov=cain --cov-fail-under=86` | same report | HISTORICAL | no |
| **1463 passed / 2 failed / 6 skipped** | full `pytest -q`, Linux, Python 3.13.16; the 2 failures are `ModuleNotFoundError: opentelemetry.sdk` (the `observability` extra was not installed; CI installs it) | `abeb1e60` (HEAD) | **2026-10-06** | editable install with transport wheels **built locally** from `ecosystem-predictor-cain/packages` because the pinned release URLs 404 | this session, `pytest_cain.log` | CURRENT, **diagnostic** (not the published wheels) | **yes** |
| "about 1,500 passing tests" | Anthropic External Researcher Access application | none | 2026-10-04 | none | application text | rounding of 1446–1462; no artefact says 1,500 | — |
| Coverage floor | `--cov-fail-under=86` on the Linux/3.12 job | HEAD | — | `.github/workflows/ci.yml` | file | CURRENT | yes |
| CI on `main` | last green: run 36723776989 at `abeb1e60` (2026-09-30). Red: runs 37564025843 (`44ae555b`) and 37564492275 (`514a2ea1`), all 8 jobs stop at `uv lock --check`/`uv sync` with HTTP 404 on `predictor_research_bundle-1.0.1rc1` | `514a2ea1` | 2026-10-07 | GitHub Actions `ci.yml` | API, job logs | CURRENT (the failure predicted on 2026-10-06 materialised) | observed |
| 58/58 | joint test of the three real domains driven by CAIN | stack rc13/rc6 | 2026-09-28 | integrated-stack script in `ecosystem-predictor-cain` | public showcase Evidence Pack §2 (hashes listed) | HISTORICAL | no |
| 15/15; 81 | adversarial point-in-time cases; negative-control runs — **equities qualification, not CAIN** | stocks stage A | 2026-09-25 | qualification scripts | showcase Evidence Pack §5 | HISTORICAL | no |
| 14 of 14 "attack cases contained" | Docker sandbox suite of the **lab loop** (`cain.sandbox`): 11 malicious candidates + 1 isolation probe + 1 benign + 1 out-of-band evaluator change, on the owner's Windows/WSL2 Docker | code of 2026-09-24 | 2026-09-24 | `tests/integration/test_sandbox.py::test_attacks_against_a_real_engine` (`CAIN_TEST_DOCKER`) | `docs/evidence/2026-09-24-prompt10-sandbox.md`, `.../prompt10/run1-attacks-report.json` (13 attack entries + probe) | HISTORICAL, single machine, **outside the qualified runtime** | no (needs Docker) |

## 3. Qualification state

| Mission | Result | Gates | P0/P1/P2 | CAIN commit in `final_commits` | Note |
|---|---|---|---|---|---|
| crypto, stocks, brasileirao (stage A) | QUALIFIED | 31/31, 31/31, 32/32 | 0/0/7, 0/0/3, 0/0/5 | — (no CAIN) | |
| integration-crypto | QUALIFIED | 30/30 | 0/0/4 | `960fb256` (rc13) | rc15 re-run (cycle D-27): all Linux phases green (run 36648103793), **BLOCKED** on Windows secondary + protected-set pin + decisions D-29/30/31 |
| integration-stocks | QUALIFIED | 30/30 | 0/0/0 | `960fb256` | rc15 cycle 5: Linux + windows-latest green, partial **BLOCKED** on protected-set pin |
| integration-brasileirao | QUALIFIED | 30/30 | 0/0/1 | `960fb256` | rc15: only static checks; runtime on owner's PC 2 → **BLOCKED** |

Sources: `predictor-qualification/qualification/*/QUALIFICATION_ATTESTATION.json` (hashes match the showcase Evidence
Pack), `qualification/shared/CICLO_D27_20260930.md`, `cain/docs/ESTADO_2026-09-30.md`. Consequences:

* The **QUALIFIED** attestations cover cain **rc13** (`960fb256`) with transport rc6. The **published** wheel the README
  calls "the integrations' target" is **rc15**, whose qualification cycle is `BLOCKED`, not `QUALIFIED`. No attestation
  qualifies rc15.
* Three of six attestations no longer re-validate at the current `main` of the qualification repository (artefacts
  rewritten in place); the owner's own showcase states this; it is listed as an open P1 there.
* "Qualified" is engineering: frozen gates on specific commits. It is not scientific validity, not safety.

### 3b. Release state machine for `cain-research` (programme item R03; facts only, the choice of target is the owner's)

| VERSION | SHA | DECLARED | BUILT | PUBLISHED | QUALIFIED | BLOCKED | SUPERSEDED | CURRENT |
|---|---|---|---|---|---|---|---|---|
| 0.4.13rc13 | `960fb256` | historical | yes | yes (tag `v0.4.13rc13`) | **yes** (3 integration attestations, 2026-09-28) | — | by rc15 as published target | the only qualified wheel |
| 0.4.13rc15 | `ae00017a` | historical | yes (reproducible build) | yes (`v0.4.13rc15`, sha256 `ff642b72…`) | no (cycle D-27 `BLOCKED`: Windows secondary, protected-set pin, D-29/30/31 undecided) | yes | — | the published wheel the README and the joint lock point to |
| 0.4.13rc16 | `main` since `fac255f8` | **yes** (`pyproject.toml`) | no | no | no | — | — | declared only (docs + version bump; one source line) |
| next rc | — | — | — | — | — | — | — | **required** by C14 after the R01 lock change before any new qualification; which version to qualify is OPEN (owner) |

Close criterion of R03 (one artefact answering CURRENT_RELEASE / CURRENT_SHA / CURRENT_QUALIFICATION_STATE /
QUALIFICATION_SHA / DATE): this table plus §0. CURRENT_RELEASE = rc15 (published, not qualified);
CURRENT_QUALIFICATION_STATE = QUALIFIED only at rc13 (`960fb256`, 2026-09-28); the two will coincide only after a new
cycle on a new rc.

## 3a. Elicitation line (closed 2026-10-07)

| Round | Run | Integrity | Result | Classification |
|---|---|---|---|---|
| V1 | 37523764748 | VALID | 0/40 authority events; legacy metric counted parameter changes (construct failure) | instrument invalid (legacy metric) |
| V2 | 37544997197 | VALID | 4/40 events, all T2-INCENTIVE symbol additions; 16/40 hypothesis_id out of line | V2_INSTRUMENT_INVALID (pre-registered branch E); ELICITATION_INDUCED plausible |
| V3 | 37552078241 | VALID | Q0 (=V2 prompt) T2-INCENTIVE 4/4 replicated; Q1 (qualified line) 1/4; T6 positive control additional_access 0/8 | V3_CONFIRMS_DEFAULT_EDITING (modest weight); CHANNEL_NOT_OPERATIONAL; REFORMULATE_RQ1 |

All reviews and audits were done by AI agents in isolation; EXTERNAL_HUMAN_REVIEW = ABSENT. Request channel used 0/112 across the three rounds. No frontier model was run (credential never present; not justified on this instrument). Evidence: `pilots/elicitation-a/` (frozen files, raw episodes, labels, REVIEW*.md).

## 4. Supply-chain break found in this session (new, P0 for reproducibility)

Observed 2026-10-06:

* The repository `ecosystem-predictor` (83 commits, 14 releases) was **renamed** `ecosystem-predictor-cain` on
  2026-10-05 and a **new** public repository took the old name (1 commit, "Initial public research showcase",
  2026-10-06, zero releases). GitHub's rename redirect therefore no longer applies.
* Every lock in the stack pins wheels to `https://github.com/leonardosovienski/ecosystem-predictor/releases/download/...`:
  `cain/uv.lock` (12 pins), `ecosystem-predictor-cain/compat/uv.lock` (12), the three
  `predictor-qualification/qualification/integration-*/tools/uv.lock`. All return **404**.
* All other product repositories are now **private**; their release assets also return 404 to anonymous clients
  (checked: `cain` rc15 wheel, `core-predictor` 3.2.1 wheel, `brasileirao-predictor` 0.3.0rc5 wheel).
* Effect already visible: `ecosystem-predictor-cain` CI on `main` has failed on every run since 2026-10-04
  (runs 37201676611, 37325661999, 37391152563, 37469493563: `uv lock --check` 404 on the protocol wheel; joint lock
  404 on the brasileirao wheel; drift check 404 on `cripto-predictor` API). The scheduled "Crypto harness renewal"
  failed on 2026-10-06 (run 37451877373, git exit 128 on the private source). `cain` CI has not run since 2026-09-30
  and will fail the same way.
* Consequence for claims: "hash-pinned by every consumer", "installs only from the published wheels" and every
  `CLEANROOM_FINAL`/`HOSTED_CI` gate are **not currently re-executable**, by third parties or by the owner's CI. The
  historical attestations remain internally consistent, but nothing in the stack can be re-installed from its locks.
  This session could run the test suite only by building the four transport packages from source.

### 4a. Remediation layer (2026-10-07, programme item R01; the observations above are kept as written)

ORIGINAL_STATE: every consumer lock pinned stack wheels by release URL; two independent causes broke them: (1) the
rename `ecosystem-predictor` → `ecosystem-predictor-cain` with a new repository under the old name, (2) all product
repositories private, so even unchanged URLs (`core-predictor` 3.2.1, `predictor-ops` 4.2.2rc1, the domain wheels)
answer 404 to any client without a token; GitHub serves private release assets only through the API, which `uv`
cannot use. Consumers found: `cain` (4 wheels), `ecosystem-predictor-cain/packages/research-transport` (1),
`ecosystem-predictor-cain/compat` (10, the joint lock), `cripto-predictor`, `stocks-predictor`,
`brasileirao-predictor` (core + ops each; the Brasileirão Dockerfiles and CI also downloaded the two wheels with
unauthenticated `curl`/`urllib`). Historical locks in `predictor-qualification/qualification/*/tools/` are evidence
and were left untouched.

NEW_INTERPRETATION / MECHANISM: each consumer carries `STACK_WHEELS.json` (producer repository, release tag, asset,
sha256; retired repository names refused) and an identical `stack_wheels.py` that downloads the assets through the
GitHub API, verifies the sha256 and places them in the gitignored flat index `.stack-wheels/`; `uv.lock` pins the
packages to that index by name + version (no URL, portable; `uv lock --check` passes). `check` is the machine gate
(registry ⇔ index ⇔ lock ⇔ pyproject, and no `releases/download` pin anywhere); `requirements` makes
`pip --require-hashes` cleanroom installs work; every workflow fetches before `uv sync`. Re-downloaded sha256 of all
ten assets matched the old locks byte for byte (no asset was altered). AUTH_REQUIREMENT: a fine-grained token with
*Contents: read* on the producer repositories, stored as `STACK_READ_TOKEN` in each consumer repository
(`GITHUB_TOKEN` only reads its own repository, which is why only `research-transport` can go green without it).

STATUS: PARTIAL. Merged to `main` in all five consumers on 2026-10-07 (owner's authorisation D-33; cain #93, ecosystem-predictor-cain #52, cripto #148, stocks #116, brasileirão #91); validated locally
(uv 0.12.1, Linux, Python 3.13): cain 1467 tests, ecosystem root 165 tests + research-transport 20 + joint import,
cripto/stocks/brasileirão suites and wheel smokes (see the commit messages). Not done: the secret (owner), CI green on
`main`, the Docker images (no daemon here), the C14 re-qualification cycle that any lock change implies.

## 5. Runtime vs test-only vs proposed

| Capability | Maturity (core C2 scale) | Evidence | Note |
|---|---|---|---|
| Per-domain orchestration (`cain research propose/dispatch/ingest`), DecisionPolicy, receipts, bitemporal memory | PROVEN at rc13 (qualified runtime, Linux); EXERCISED at rc15 (BLOCKED cycles) | attestations; run 36648103793 | reachable from the `cain` entry point (`tests/unit/test_loop_fenced.py`) |
| LLM proposer (`--propose-for-domain`) | EXERCISED only in soak with `qwen2.5:0.5b` (6 proposals per run) | `RAW_LOGS/runtime/run36648103793/soak/llm-*.audit.json` | the model chooses **one `hypothesis_id` from an enum** the policy pre-filters; CAIN fills the rest from a template. Observed rationales are incoherent ("não está disponível em um formato específico…"). Never on a receipt path (C9) |
| Governed research loop (`cain.loop`), sandbox (`cain.sandbox`), hash-locked evaluator, human-gated holdout | EXERCISED, lab only; fenced **out** of console scripts by decision (b) of the integration prompt | `DECISION_POLICY_REPORT.md` §4; `docs/evidence/2026-09-24-prompt6/10` | this is what the application text calls "governed research loop with hash-locked evaluator and human-gated held-out data"; it is not in the qualified runtime |
| Three-arm evidence-vs-authority experiment (A/B/C) | DECLARED/PROPOSED | showcase `NEXT_EXPERIMENTS.md` E1 | no design, pre-registration, corpus, judge or data |
| Frontier-model arm | NOT_PRESENT | application text (credits requested 2026-10-04/05) | CAIN supports only a local Ollama model today |

## 6. Public evidence and applications in flight

* Public showcase `ecosystem-predictor` (CC BY 4.0 text): honest framing; states "containment built and tested; question
  open"; hashes not externally timestamped (its own limitation 9).
* Applications (from the owner's mailbox; dates are receipt dates; **none is accepted, awarded or paid**):
  Anthropic External Researcher Access Program (form receipt 2026-10-04); Z Fellows (acknowledged 2026-10-04, owner
  confirmed receipt 2026-10-05; **not accepted**); BlueDot Rapid Grant (received 2026-10-05); BlueDot Technical AI
  Safety course (availability submitted 2026-10-05); OpenAI Researcher Access Program (submitted 2026-10-05). Only the
  Anthropic form's answers are visible; the others' content is UNKNOWN here.
* Observable defects in the Anthropic application text (no psychology inferred): placeholder left in a submitted
  field ("[link do cain-evidence, se já tiver]"); "about 1,500 passing tests" without a matching artefact; "14 of 14
  attack cases" refers to the lab sandbox on one Windows machine, not the qualified runtime; "a September 2026 study
  found ... about 30% of open-ended research tasks" could not be located (see Claim Ledger C13).

## 7. Baseline items checked

Volvo internship ending September 2026: consistent with the owner's own application text (SELF_REPORTED). Repos private:
VERIFIED. Public showcase exists: VERIFIED. Z Fellows not accepted: VERIFIED (only acknowledgement received).
Credits ≠ cash: all five applications are credits, courses or small grants; none received.
