# FUNDING_READINESS_SOURCE_OF_TRUTH — CAIN

Issued 2026-10-06 (cloud Linux session, read access to the nine stack repositories, GitHub API, owner's mailbox).
Scope: what is verifiable **today** about CAIN as the subject of a funding case. Predictors are covered only where a
CAIN claim depends on them. Every number carries scope, SHA, date, source and whether this session reproduced it.
Companion files: `CAIN_CLAIM_LEDGER.md`, `FUNDING_READINESS_RISK_LEDGER.md`.

## 1. Canonical code state

| Item | Value | Source | Reproduced here |
|---|---|---|---|
| Canonical branch | `main` of `leonardosovienski/cain` (private since early October 2026) | GitHub API (`private: true`) | yes |
| HEAD | `abeb1e6011537bea2d8a0d87334780f8370f1cbd` (2026-09-30, PR #90, docs only) | `git log` | yes |
| Declared version | `0.4.13rc16`, **not published** | `pyproject.toml` | yes |
| Published wheel | `cain-research 0.4.13rc15`, tag `v0.4.13rc15`, commit `ae00017a` (2026-09-29), sha256 `ff642b72…` | release list via API; `docs/ESTADO_2026-09-30.md` | release exists (API); asset hash **not** re-downloaded (URL returns 404 anonymously, §4) |
| Code change since rc15 | one line (`src/cain/__init__.py` version bump); 7 commits, all docs/version | `git diff --stat ae00017a..HEAD -- src tests` | yes |
| DecisionPolicy | `src/cain/orchestration/policy.py`, `POLICY_VERSION = 2`, rules R01–R17, sha256 `3cea49644e1b2c6a15a550f2c76af8cfe8e4e002f58945a8ffde44b64004b8e6` at HEAD | file | yes |
| Protocol/transport pins | `predictor-research-protocol 2.0.0rc2`, `-transport 0.1.0rc7`, `-snapshot 1.0.2rc1`, `-bundle 1.0.1rc1`, all URL-pinned to `github.com/leonardosovienski/ecosystem-predictor/releases/...` | `pyproject.toml`, `uv.lock` (12 URL pins) | yes; **all four URLs 404** (§4) |
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
| CI on `main` | run 36723776989 `success` at `abeb1e60` | `abeb1e60` | 2026-09-30 | GitHub Actions `ci.yml` | API | CURRENT (last run); **expected to fail on the next run** (§4) | observed |
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
