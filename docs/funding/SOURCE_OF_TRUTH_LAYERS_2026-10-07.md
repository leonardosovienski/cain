# FUNDING_READINESS_SOURCE_OF_TRUTH — layers of 2026-10-06/07 moved out of the living document

> MODE: SNAPSHOT_IMMUTABLE · AS_OF_DATE: 2026-10-07 · AS_OF_SHA: bd611ba · SUPERSEDED_BY: docs/funding/FUNDING_READINESS_SOURCE_OF_TRUTH.md (§0, §1, §3, §4a)
> (dated record; the three blocks below were cut verbatim from the living Source of Truth on 2026-10-08 so that it carries only the current state; nothing here is corrected in place)

## §1 (2026-10-06/07 morning) — Canonical code state as observed then

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

## §3 (2026-09-30 / 2026-10-07 morning) — Qualification state as observed then

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

## §4 (2026-10-06) — Supply-chain break as observed then

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
