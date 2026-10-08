# FUNDING_READINESS_SOURCE_OF_TRUTH — CAIN

MODE: CURRENT_LIVING_STATE · LAST_MATERIAL_UPDATE: 2026-10-08 (closure audit of the remediation phase: §0 re-verified from fresh clones and the GitHub API, §8 owner-only actions, §9 closure; earlier: 2026-10-07 R01 merged in all consumers, R04 claim gate, R05 packet, R06 novelty scan, R07–R09 drafts, H05–H07 controls) · ISSUED: 2026-10-06
(cloud Linux session, read access to the nine stack repositories, GitHub API, owner's mailbox).
This file is the single canonical chain for "what is true today" about CAIN; dated documents it cites are
SNAPSHOT_IMMUTABLE and are never edited to match it. It changes whenever HEAD, CI state, scientific state, release state,
qualification state, funding state or the open findings change.
Scope: what is verifiable **today** about CAIN as the subject of a funding case. Predictors are covered only where a
CAIN claim depends on them. Every number carries scope, SHA, date, source and whether this session reproduced it.
Companion files (also CURRENT_LIVING_STATE): `CAIN_CLAIM_LEDGER.md`, `FUNDING_READINESS_RISK_LEDGER.md`.

## 0. Canonical answers (one chain, no archaeology)

| Question | Answer (2026-10-08 unless dated otherwise) | Where it is checked |
|---|---|---|
| CURRENT_HEAD | `main` = `acb74d80` (PR #101, 2026-10-07) plus the closure layer of 2026-10-08 (this PR). Every PR of the remediation programme for this repository is merged (R01 #93 … #101); tag `v0.4.13rc16` = `de5db06b`; no branch other than `main`, no open PR (verified by API 2026-10-08 for all nine repositories). | `git log origin/main -1`; GitHub API |
| DECLARED_VERSION | `0.4.13rc16` (`pyproject.toml`, `cain.__version__`); published (see PUBLISHED_VERSION) | `tests/test_canonical_state.py`, `tests/test_readme_version.py` |
| PUBLISHED_VERSION | `0.4.13rc16`, tag `v0.4.13rc16`, commit `de5db06b`, wheel sha256 `d8fca502420f66ebb39dc98f965895e17530c42ee413af61798e7a7dcfc9a302` (Release run 37696634940, reproducible double build; re-downloaded anonymously and equal to a local reproducible build). Package code identical to rc15 (`src/cain/__init__.py` version line only); the lock moved to the hash-pinned registry (R01/D-32). The ecosystem joint lock (`compat/STACK_WHEELS.json`, ecosystem 0.2.2, `6aeec475`) pins rc16 since 2026-10-07 (evening). Previous: rc15 `ae00017a`, sha256 `ff642b72…` | GitHub release; `RELEASE_NOTES/v0.4.13rc16.md` |
| QUALIFIED_VERSION | **`0.4.13rc16`** (`de5db06b`, transport 0.1.0rc7) by the integration-crypto (rc16, re-issued rc16e after the ecosystem joint lock adopted rc16) and integration-stocks (cycle 6, re-issued cycle 7) attestations, QUALIFIED on 2026-10-07/08 under D-34 (owner-delegated D-29/D-30/D-31 written the same day; crypto stage A V1.2 QUALIFIED). integration-brasileirao stays at rc13 (`960fb256`): its rc16 cycle has only the static checks, the runtime needs the owner's PC 2 (D-19/D-25). rc15 was never qualified (cycle D-27 BLOCKED, superseded by rc16) | §3; `predictor-qualification/qualification/integration-*/QUALIFICATION_ATTESTATION.json` |
| CI_STATE | 2026-10-08: run 37709839394 at `acb74d80`, **8/8 jobs success** (test 3.11–3.14, windows-tests, windows-launcher, typecheck, coverage). Across the stack, every push workflow on `main` is green except stocks-predictor's `CI Pipeline` (run 37696634847 at `82dbb0c5`), red only at the step "Current R8 operational evidence identities" = EXPECTED_NON_CI_EVIDENCE_GATE (owner's private data, §8). Earlier layer: `main`: Linux jobs **green** since the R01 merge (run 37651563333 at `3a06659`, 2026-10-07, after the owner made the producers public). `windows-tests` was red at `45cb865` and `a0edfcc` (runs 37653818187, 37658373586): a fixture of the H05 freeze-gate test wrote its frozen files with text-mode newline translation, so on Windows the gate correctly failed closed on the hash mismatch; fixed in PR #96 (byte-exact fixture). Historical: red 2026-10-07 before R01 (runs 37564025843, 37564492275: `uv lock --check` 404 on the protocol wheel) | §4 |
| SCIENTIFIC_STATE | Elicitation line V1–V3 **CLOSED** 2026-10-07, `FINAL_STATE = REFORMULATE_RQ1`; no behavioural effect of CAIN demonstrated; no frontier model run; EXTERNAL_HUMAN_REVIEW = ABSENT; NEW_RQ1_LINE = BLOCKED by the remediation programme gates | §3a; `pilots/elicitation-a/HANDOFF.md` (snapshot) |
| OPEN_RISKS | P0: R01 OPEN (observability), R02 OPEN (elicitation, documented stop). R03 CLOSED 2026-10-07. P1: R04 PARTIAL, R05 OPEN (human), R06 PARTIAL (human read), R07 CLOSED 2026-10-08. P2: R08 note, R09 PARTIAL (stamp created, upgrade pending), R10, R11, R12 CLOSED as control 2026-10-08, R13 CLOSED as controls, R14 owner-only | `FUNDING_READINESS_RISK_LEDGER.md` |
| VISIBILITY / PUBLIC_CODE_POLICY | **PUBLIC** — explicit owner decision: D-11 (`predictor-qualification/qualification/DECISIONS.json`, "todos os repos do dono são públicos") and the owner's action of 2026-10-07 (all nine repositories public; verified by API 2026-10-08, D-35 records it). Licence classification: eight repositories are SOURCE_AVAILABLE under a proprietary licence (`LICENSE`: All Rights Reserved; **not open source**); the showcase's text is CC BY 4.0. Consequence: no current document may say "all code is private"; the supply chain does not depend on any private asset. Historical: private from early October 2026 until 2026-10-07 | GitHub API (`visibility`), `LICENSE` files |
| REPRODUCIBILITY | PUBLIC_REPRODUCIBILITY for the stack install (anonymous registry fetch + locks, see SUPPLY_CHAIN_HEALTHY). PARTIAL for two evidence items that need the owner's private data: the stocks R8 operational seal and the brasileirão integration runtime (PC 2); a third party cannot reproduce those two | §8 |
| NOVELTY | NOVELTY_AI_SCAN = COMPLETE (17 entries, `docs/research/NOVELTY_MATRIX.md`); HUMAN_NOVELTY_READ = NO; NOVELTY_STATUS = **NARROW_GAP_CANDIDATE**, not ESTABLISHED | `docs/research/NOVELTY_MATRIX.md` |
| CAIN_BEHAVIORAL_EFFECT · FRONTIER · V4 | CAIN_BEHAVIORAL_EFFECT = NOT_DEMONSTRATED (never tested) · FRONTIER_RUN = NOT_EXECUTED · V4_ALLOWED = NO · CURRENT_LINE_STATUS = CLOSED · CURRENT_RQ1_STATE = REFORMULATE_RQ1 | §3a; `pilots/elicitation-a/HANDOFF.md` |
| CLOSURE | 2026-10-08: **CLOSED_WITH_OWNER_ACTIONS** (§9); the only list of owner-only actions is §8 | §8, §9 |
| CLAIM_GATE_ACTIVE | **YES** (2026-10-07; 2026-10-08 regression vectors `claim_gate.py selftest` in cain and in the showcase CI: ISO and slash dates, versions, SHAs, percentages, real ratios, counts, amounts): `tools/claim_gate.py` + `docs/funding/CLAIM_INDEX.json` gate the README's current section and `tests/test_claim_gate.py` checks every ledger row; the public showcase runs `claims/claim_gate.py` in CI over all its documents (18 registered claims, banned phrases) | this repository; `ecosystem-predictor/.github/workflows/claim-gate.yml` |
| NEW_RQ1_LINE | **BLOCKED**: gates and their state in `docs/research/FUTURE_LINE_ENTRY_GATES.md` (observability, positive control and independence plan are DRAFT; novelty scan done, human read absent) | `docs/research/FUTURE_LINE_ENTRY_GATES.md`, `docs/research/NOVELTY_MATRIX.md` |
| EXTERNAL_HUMAN_REVIEW | **ABSENT**; packet ready for a reviewer: `docs/funding/EXTERNAL_REVIEW_PACKET.md` (records go to `EXTERNAL_REVIEW_RECORDS.md`) | §3a |
| PROCESS_CONTROLS | H05 freeze gate, H06 rubric layers, H07 completeness gate implemented in `pilots/elicitation-a/` and wired into the pilot workflow (2026-10-07); retro layers: V2 freeze PASS at its run commit; V3 freeze PASS with the manifest (note + workflow hash) edited after the freeze commit and frozen files byte-identical; V3 analysis INCOMPLETE (T6 circumvention count never emitted, recovered in REVIEW_V3) | `pilots/elicitation-a/{freeze_gate,rubric_layers,completeness_gate}.py`, `v3/runs/{FREEZE_GATE_RETRO_V3,COMPLETENESS_V3}.json`, `v2/runs/FREEZE_GATE_RETRO_V2.json` |
| EXTERNAL_TIMESTAMP | STAMP_CREATED = YES (2026-10-07, workflow `timestamp.yml` runs 37653866039 at `45cb865` and 37693878433 at `c943434`): `docs/funding/ANCHORS.json` (17 records: pilot designs, manifests, raw episodes, reviews, the two ledgers, `STACK_WHEELS.json`) with proofs `ANCHORS.json.ots` and `ANCHORS.20261007T220538Z.json.ots`. OTS_PENDING_UPGRADE = YES: the proofs are calendar commitments; `ots upgrade` to a Bitcoin block attestation has not been run (calendars unreachable from the remediation container; §8). EXTERNAL_ATTESTATION_VERIFIED = NO. Not covered: the qualification attestations and the showcase Evidence Pack hashes themselves. Earlier layer (2026-10-07 morning): NOT_RUN | `docs/funding/ANCHORS.json`, `.ots` files, `ots info` |
| SUPPLY_CHAIN_HEALTHY | **YES**, re-verified 2026-10-08 from fresh `--depth 1` clones of `main` with **no token in the environment**: `stack_wheels.py fetch` + `check` + `uv lock --check` PASS in cain, ecosystem research-transport, ecosystem `compat/` (joint lock; `uv sync --locked` + import: cain 0.4.13rc16, transport 0.1.0rc7, core 3.2.1, ops 4.2.2rc1), cripto, stocks and brasileirão; `uv sync --locked` PASS in the four product consumers; cain synced with the CI extras (dev, vision, observability) and ran its full suite (1489 passed / 4 skipped); the ten distinct registry assets (twenty fetches) matched their sha256. cain's optional `[verify]` extra needs torch from download.pytorch.org, unreachable from this container (environment, not supply chain). No consumer carries a `releases/download` pin. Classification: PUBLIC_REPRODUCIBILITY for the stack install. Earlier layer (2026-10-07, evening: the C14 cycle on rc16 closed, see QUALIFIED_VERSION; earlier the same day: YES for availability, PARTIAL for qualification): locks carry no release URLs (registry + API fetch in every consumer, §4a); all nine repositories are public again, so every registry fetch resolves anonymously (`STACK_READ_TOKEN` optional, the job token is the CI fallback since PR #96 and its siblings). `main` CI green with the registry in cain (Linux, 37651563333), ecosystem-predictor-cain (37651560309), cripto-predictor (37663192063, Trivy clean after urllib3 2.8.0), brasileirão (37662106707); stocks red only on the owner-data evidence step. Dev-extra vulnerability audit done (`pip-audit` over the exported locks: pytest and virtualenv bumped in ecosystem-predictor-cain, cripto, brasileirão; residual: multidict 6.7.1 pinned exactly by ccxt 4.5.85). Not CLOSED: the C14 re-qualification cycle on a new rc | §4a; CI reruns of 2026-10-07 |

## 1. Canonical code state

Layer 2026-10-08 (closure): the table below is the 2026-10-06/07 (morning) snapshot, kept as written. Current values: HEAD `acb74d80` (`main`, PR #101); the repository is **public** since 2026-10-07 (proprietary licence, source-available); declared = published = `0.4.13rc16` (`de5db06b`, wheel sha256 `d8fca502…`, re-downloaded anonymously on 2026-10-08 by the clean-clone fetch); the four protocol/transport pins come from `STACK_WHEELS.json` through the registry index (no URL pin; `uv lock --check` PASS); code change since rc15 remains the version line; DecisionPolicy sha256 unchanged.

| Item | Value (layer 2026-10-06/07) | Source | Reproduced here |
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
| **1463 passed / 2 failed / 6 skipped** | full `pytest -q`, Linux, Python 3.13.16; the 2 failures are `ModuleNotFoundError: opentelemetry.sdk` (the `observability` extra was not installed; CI installs it) | `abeb1e60` | 2026-10-06 | editable install with transport wheels **built locally** from `ecosystem-predictor-cain/packages` because the pinned release URLs 404 | that session, `pytest_cain.log` | HISTORICAL (was CURRENT, diagnostic, until 2026-10-08) | yes (then) |
| **1489 passed / 4 skipped** | full `pytest -q`, Linux, Python 3.13.16, fresh clone of `main`, `uv sync --locked` with the CI extras (dev, vision, observability), stack wheels fetched anonymously from the registry | `acb74d80` | **2026-10-08** | `uv run --locked pytest -q` | closure audit (scratch log of the session) | CURRENT (installed from the lock; the published rc16 wheel is byte-identical in `src/cain` except the version line) | **yes** |
| "about 1,500 passing tests" | Anthropic External Researcher Access application | none | 2026-10-04 | none | application text | rounding of 1446–1462; no artefact says 1,500 | — |
| Coverage floor | `--cov-fail-under=86` on the Linux/3.12 job | HEAD | — | `.github/workflows/ci.yml` | file | CURRENT | yes |
| CI on `main` | last green: run 36723776989 at `abeb1e60` (2026-09-30). Red: runs 37564025843 (`44ae555b`) and 37564492275 (`514a2ea1`), all 8 jobs stop at `uv lock --check`/`uv sync` with HTTP 404 on `predictor_research_bundle-1.0.1rc1` | `514a2ea1` | 2026-10-07 | GitHub Actions `ci.yml` | API, job logs | HISTORICAL (the failure predicted on 2026-10-06 materialised; fixed by R01 the same day) | observed |
| CI on `main` | run 37709839394 at `acb74d80`: all eight jobs `success` | `acb74d80` | 2026-10-08 | GitHub Actions `ci.yml` | API | CURRENT | observed |
| 58/58 | joint test of the three real domains driven by CAIN | stack rc13/rc6 | 2026-09-28 | integrated-stack script in `ecosystem-predictor-cain` | public showcase Evidence Pack §2 (hashes listed) | HISTORICAL | no |
| 15/15; 81 | adversarial point-in-time cases; negative-control runs — **equities qualification, not CAIN** | stocks stage A | 2026-09-25 | qualification scripts | showcase Evidence Pack §5 | HISTORICAL | no |
| 14 of 14 "attack cases contained" | Docker sandbox suite of the **lab loop** (`cain.sandbox`): 11 malicious candidates + 1 isolation probe + 1 benign + 1 out-of-band evaluator change, on the owner's Windows/WSL2 Docker | code of 2026-09-24 | 2026-09-24 | `tests/integration/test_sandbox.py::test_attacks_against_a_real_engine` (`CAIN_TEST_DOCKER`) | `docs/evidence/2026-09-24-prompt10-sandbox.md`, `.../prompt10/run1-attacks-report.json` (13 attack entries + probe) | HISTORICAL, single machine, **outside the qualified runtime** | no (needs Docker) |

## 3. Qualification state

Layer 2026-10-08 (closure; current attestations at `predictor-qualification` `main` `aea5e0b7`, every checker `attest.py check` OK, `MANIFEST.sha256` OK):

| Mission | Result | Gates | P0/P1/P2 | CAIN wheel / commit | Environments | Attestation sha256 (first 12) | Supersedes |
|---|---|---|---|---|---|---|---|
| crypto (stage A, V1.2) | QUALIFIED | 31/31 | 0/0/8 | — (cripto 1.2.0rc4 `21f8b182`) | Linux hosted · Windows hosted (D-30) | `0c8589b128a1` | `2b1491a03a6b` (V1.1) |
| stocks (stage A) | QUALIFIED | 31/31 | 0/0/3 | — (stocks 0.3.0rc2) | Linux hosted · Windows hosted | `e0f2e28ddd0c` | `4896575fd15c` |
| brasileirao (stage A) | QUALIFIED | 32/32 | 0/0/5 | — (brasileirão 0.3.0rc3) | owner_linux · local Windows | `a4fa2fee25b6` | `efc566716dfc` |
| integration-crypto (rc16e) | QUALIFIED | 30/30 | 0/0/4 | **rc16** `de5db06b` | Linux hosted · Windows hosted (D-31) | `263bd04e282e` | `cc44bdf984c9` (rc16) |
| integration-stocks (cycle 7) | QUALIFIED | 30/30 | 0/0/0 | **rc16** `de5db06b` | Linux hosted · Windows hosted (D-1) | `359c0a49b97e` | `f70b54cc7cdc` (cycle 6) |
| integration-brasileirao | QUALIFIED | 30/30 | 0/0/1 | **rc13** `960fb256` | owner_linux · local Windows | `99dd94bdac94` | `8aef11046708` |

Scope statement: cain rc16 is qualified by two of the three integrations (crypto, stocks), on hosted Linux primary and hosted Windows secondary; the football integration is qualified at rc13 only, and its rc16 cycle holds the static checks (`ATTESTATION_PARTIAL_rc16-static.json`, 2026-10-07) until the owner's runtime (§8). "QUALIFIED" is engineering (C22). The table below is the 2026-09-30/10-07 (morning) layer, kept as written.

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
  rewritten in place); the owner's own showcase states this; it is listed as an open P1 there. Layer 2026-10-08: resolved —
  the three were superseded by re-issues (crypto V1.2, integration-crypto rc16/rc16e, integration-stocks cycles 6/7) and
  all six current attestations re-validate at `main` `aea5e0b7` (six `attest.py check` OK); the showcase was corrected the same day.
* "Qualified" is engineering: frozen gates on specific commits. It is not scientific validity, not safety.

### 3b. Release state machine for `cain-research` (programme item R03; facts only, the choice of target is the owner's)

| VERSION | SHA | DECLARED | BUILT | PUBLISHED | QUALIFIED | BLOCKED | SUPERSEDED | CURRENT |
|---|---|---|---|---|---|---|---|---|
| 0.4.13rc13 | `960fb256` | historical | yes | yes (tag `v0.4.13rc13`) | **yes** (3 integration attestations, 2026-09-28; integration-brasileirao's still current) | — | by rc16 for integration-crypto and integration-stocks (attestations preserved as superseded files) | qualified wheel of integration-brasileirao |
| 0.4.13rc15 | `ae00017a` | historical | yes (reproducible build) | yes (`v0.4.13rc15`, sha256 `ff642b72…`) | no (cycle D-27 `BLOCKED`; D-29/30/31 were written only on 2026-10-07, for rc16) | historical | by rc16 | the wheel the ecosystem joint lock (`compat/`) still pins |
| 0.4.13rc16 | `de5db06b` (tag) | **yes** (`pyproject.toml`) | yes (reproducible double build, run 37696634940) | yes (`v0.4.13rc16`, sha256 `d8fca502…`) | **yes** (integration-crypto rc16, integration-stocks cycle 6; 2026-10-07, D-34) | — | — | **CURRENT**: published and qualified; integration-brasileirao pending on the owner's runtime |

Close criterion of R03 (one artefact answering CURRENT_RELEASE / CURRENT_SHA / CURRENT_QUALIFICATION_STATE /
QUALIFICATION_SHA / DATE): this table plus §0. CURRENT_RELEASE = rc16; CURRENT_SHA = `de5db06b`;
CURRENT_QUALIFICATION_STATE = QUALIFIED (integration-crypto, integration-stocks); QUALIFICATION_SHA = the two
`QUALIFICATION_ATTESTATION.json` files of 2026-10-07 in `predictor-qualification`; DATE = 2026-10-07. Historical layer
(same day, morning): CURRENT_RELEASE was rc15 (published, not qualified) and QUALIFIED only at rc13 (`960fb256`, 2026-09-28).

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

LAYER 2026-10-07 (evening): the owner made all nine repositories public, so the anonymous fetch works and the secret is
optional; every consumer's workflows fall back to the job token (`secrets.STACK_READ_TOKEN || github.token`) because
Dependabot-triggered runs carry no repository secrets and an anonymous fetch hit GitHub's rate limit (cripto PR #147).
`main` CI green with the registry: cain Linux 37651563333, ecosystem-predictor-cain 37651560309, cripto-predictor
37663192063 (container job incl. Trivy), brasileirão 37662106707; stocks 37651574443 red only at "Current R8
operational evidence identities" (owner data). Docker images are built in CI (cripto `container`, brasileirão image
jobs). Still open at that point: the C14 cycle on a new rc — done later the same day (rc16 published; integration-crypto and
integration-stocks re-qualified; the ecosystem joint lock adopted rc16 and the attestations were re-issued once more, rc16e / cycle 7).
R03 CLOSED; the brasileirão integration's runtime re-qualification is the owner's (D-19/D-25).

## 5. Runtime vs test-only vs proposed

| Capability | Maturity (core C2 scale) | Evidence | Note |
|---|---|---|---|
| Per-domain orchestration (`cain research propose/dispatch/ingest`), DecisionPolicy, receipts, bitemporal memory | PROVEN at rc13 (qualified runtime, Linux); EXERCISED at rc15 (BLOCKED cycles) | attestations; run 36648103793 | reachable from the `cain` entry point (`tests/unit/test_loop_fenced.py`) |
| LLM proposer (`--propose-for-domain`) | EXERCISED only in soak with `qwen2.5:0.5b` (6 proposals per run) | `RAW_LOGS/runtime/run36648103793/soak/llm-*.audit.json` | the model chooses **one `hypothesis_id` from an enum** the policy pre-filters; CAIN fills the rest from a template. Observed rationales are incoherent ("não está disponível em um formato específico…"). Never on a receipt path (C9) |
| Governed research loop (`cain.loop`), sandbox (`cain.sandbox`), hash-locked evaluator, human-gated holdout | EXERCISED, lab only; fenced **out** of console scripts by decision (b) of the integration prompt | `DECISION_POLICY_REPORT.md` §4; `docs/evidence/2026-09-24-prompt6/10` | this is what the application text calls "governed research loop with hash-locked evaluator and human-gated held-out data"; it is not in the qualified runtime |
| Three-arm evidence-vs-authority experiment (A/B/C) | DECLARED/PROPOSED | showcase `NEXT_EXPERIMENTS.md` E1 | no design, pre-registration, corpus, judge or data |
| Frontier-model arm | NOT_PRESENT | application text (credits requested 2026-10-04/05) | CAIN supports only a local Ollama model today |

Layer 2026-10-08: the first row is PROVEN at **rc16** (integration-crypto rc16e, runs 37703318858 Linux and Windows; integration-stocks cycle 7, run 37704456789), not only at rc13; the rc15 BLOCKED cycles are historical.

## 6. Public evidence and applications in flight

* Public showcase `ecosystem-predictor` (CC BY 4.0 text): honest framing; states "containment built and tested; question
  open"; hashes not externally timestamped (its own limitation 9). Layer 2026-10-08: the cain artefacts listed in
  `ANCHORS.json` are stamped (calendar proof, upgrade pending); the showcase's limitation 9 and Evidence Pack §7 carry the
  same scoped statement since 2026-10-08.
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
VERIFIED on 2026-10-06 (public again since 2026-10-07, re-verified 2026-10-08). Public showcase exists: VERIFIED. Z Fellows not accepted: VERIFIED (only acknowledgement received).
Credits ≠ cash: all five applications are credits, courses or small grants; none received.

## 8. OWNER_ONLY_REMAINING_ACTIONS (the single canonical list; 2026-10-08)

Everything an agent session could execute in the remediation phase is done. The items below need the owner, an external
machine, private data or an outside human. Other documents point here instead of repeating them.

| # | OWNER_ACTION | WHY_AGENT_CANNOT_CLOSE | BLOCKS_WHAT | CLOSE_CRITERION |
|---|---|---|---|---|
| 1 | integration-brasileirao rc16 runtime on PC 2 (`owner_linux`, D-19/D-25) and the local Windows smoke, then `attest.py final` and the PR | the Brasileirão data is private and not redistributable (D-11, D-19); the runtime exists only on the owner's PC 2 | rc16 qualification of the football integration (stays QUALIFIED at rc13; partial `ATTESTATION_PARTIAL_rc16-static.json`) | attestation QUALIFIED with cain `de5db06b` in `final_commits`, merged to `main` |
| 2 | stocks-predictor R8 operational-evidence reseal with the preserved real file (`docs/engineering/2026-09-30-license-reseal/README.md` in that repository) | the verifier ties the receipt to the owner's preserved data population; resealing with public data would loosen the seal (CICLO_D27 item 4) | the step "Current R8 operational evidence identities" of stocks `CI Pipeline` on `main` (the only red automated check in the stack) | stocks `main` CI green on a run after the reseal commit |
| 3 | External human review of the protocol, attestations and claims (R05) | an AI session cannot be the external reviewer | EXTERNAL_HUMAN_REVIEW = ABSENT; any "externally/independently validated" wording; the three design gates of the new line (R07–R09) | a record in `docs/funding/EXTERNAL_REVIEW_RECORDS.md` with PERSON, BACKGROUND, DATE, MATERIAL_REVIEWED, FINDINGS, RESPONSE |
| 4 | Human read of `docs/research/NOVELTY_MATRIX.md` (R06) | novelty is a judgement a human reader must make; the matrix is an AI scan | NOVELTY_STATUS stays NARROW_GAP_CANDIDATE; a new RQ1 line stays BLOCKED | the reader's note (name, date, verdict) appended to the matrix |
| 5 | `ots upgrade docs/funding/ANCHORS.json.ots docs/funding/ANCHORS.20261007T220538Z.json.ots` once the calendars have anchored, then `ots verify` and commit the upgraded proofs (R09/R10) | the OpenTimestamps calendars are unreachable from the remediation container; the upgrade needs a machine with network access to them | EXTERNAL_ATTESTATION_VERIFIED = YES | upgraded `.ots` files committed; `ots verify` output recorded in `ANCHORS.json` (`note` layer) |
| 6 | Public metadata (R12/R14): set the GitHub description and topics of `ecosystem-predictor` and `cain` | the session proxy refuses repository-settings writes (HTTP 403 on 2026-10-08, PATCH and PUT) | nothing material (polish). Proposed texts: showcase — "Public research showcase and evidence pack (CC BY 4.0): prediction systems in three domains, qualification attestations, and a closed diagnostic line on research-agent authority demand. Evidence, not implementation.", topics `ai-safety research-agents evidence-pack negative-results reproducibility research-showcase`; cain — "CAIN: deterministic research-orchestration agent for the predictor stack (proposes only; versioned decision policy; capital forbidden). Research prototype, proprietary licence; evidence in the ecosystem-predictor showcase.", topics `research-agent ai-safety decision-policy containment python` (the present cain description, about "persistent identity in multi-agent systems", is from an earlier project phase) | description and topics visible on GitHub |
| 7 | CR-F022 (crypto domain contract, P2): decide whether to update the result-layout text of `DOMAIN_RESEARCH_CONTRACT.json`, which reopens `DOMAIN_CONTRACT` and the V2 freeze (C14) | a frozen contract changes only by the owner's decision (C19/C24.4) | nothing current (P2, no gate); it stays an open P2 in the crypto attestation | a DECISIONS.json entry: fix in a future cycle, or accept as is |

## 9. Closure of the remediation phase (2026-10-08)

FINAL VERDICT: **CLOSED_WITH_OWNER_ACTIONS** — every agent-executable remediation (R01–R12, H01–H07) is merged and re-verified at
the final HEADs; what remains is §8. ENGINEERING_STATE = HEALTHY · SUPPLY_CHAIN = HEALTHY (public reproducibility) · RELEASE_STATE =
CONSISTENT (rc16 declared = published = qualified for crypto/stocks integrations; football integration at rc13) · QUALIFICATION =
CURRENT_WITH_SCOPED_OWNER_BLOCKERS · CLAIM_GATE = ACTIVE · CONSISTENCY_GATE = ACTIVE (`tests/test_canonical_state.py`, the claim
gates, the attestation checkers, `MANIFEST.sha256`) · SCIENTIFIC_LINE_V1_V3 = CLOSED · NEW_RQ1 = BLOCKED · FRONTIER = NOT_RUN ·
EXTERNAL_HUMAN_REVIEW = ABSENT · NOVELTY_HUMAN_REVIEW = PENDING · OWNER_ONLY_ACTIONS = EXPLICIT (§8).

Entrypoints: SCIENTIFIC_CONTINUATION = `docs/research/FUTURE_LINE_ENTRY_GATES.md` · FUNDING_DUE_DILIGENCE = this file ·
QUALIFICATION = `predictor-qualification/README.md` (current state, then the historical record) · OWNER_ACTIONS = §8 ·
scientific record of the closed line = `pilots/elicitation-a/HANDOFF.md` (snapshot). Final HEADs of the nine repositories are
listed in the closure PR descriptions of 2026-10-08 and re-checked by `git log origin/main -1`.
