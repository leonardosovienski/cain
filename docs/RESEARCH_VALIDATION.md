# L0 validation · local execution 2026-09-11

This report describes executed engineering checks, not scientific replication.
Baseline Cain: `c075c93466a9d36c59f3469bacde90cc287e0b70`.
Crypto source/exporter base: `e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f`.
Ecosystem base: `b3f0ea58a2a102a94d5c7c78bd7f8224984fc4d4`.
The existing operational Crypto checkout was separately observed clean at
`39b0f57496cee06e6f8841c2476f8428210aaf76`; it was not modified. The producer's
snapshot is the pinned earlier clone, not an assertion about that newer checkout.
These reads are not an atomic cross-repository snapshot.

| Capability | Real path | Baseline evidence/state | Change | Acceptance |
|---|---|---|---|---|
| Legacy state and turns | runtime/workspace/SQLite | 281 tests passed | No legacy schema migration | Final suite retains regressions |
| API/web without Ollama | Windows startup | Ollama preparation preceded mode dispatch | Prepare only for chat/demo | Actual API/web startup without Ollama; Windows tests |
| Service identity | health/startup | Literal 0.3.0/provisional comparison | Stable service and API-contract identity | Foreign HTTP service refused, left running |
| Package version | init/API/pyproject | init 0.2.0 vs metadata 0.3.0 | Align 0.4.0 | Installed metadata/module/API matched |
| Explicit config | settings | Nonexistent file silently accepted | Fail explicit missing config; strict boolean permissions | Regression tests |
| Research import/query | CLI/API/UI | Absent necessary capability | Shared local service, policy and separate db | Real import, UI query and evidence |
| Contract | shared wheel | Absent necessary boundary | Ecosystem-owned 1.0.0 | Same installed contract on Python 3.12/3.13 |
| Producer | Crypto exporter | Pipeline CLI imports main.run | Independent distribution, early dispatch | 10 isolated exporter tests; real export |
| Historian | existing LLM protocol | Absent necessary capability | Bounded exact quotes + proposed synthesis | Adversarial mocks; local provider unavailable |
| Recovery | research.db | New separate storage | Atomic archive/projection, online backup | Real reimport/rebuild/backup/restore and corruption tests |
| Capabilities registry | Stocks/Ecosystem | Not on chosen bridge | Not applicable; no change | Synthetic heterogeneous namespace/state tests |

Observed final suite: **339 passed, 1 skipped**, Windows, Python 3.12.14.
The skip is symlink creation without Windows privilege. Two upstream FastAPI/
Starlette deprecation warnings remain; assertions were not weakened. The exporter
suite: **10 passed**, Windows, isolated Python 3.13.14, installed exporter wheel.
Ruff passed on changed Cain, contract and Crypto exporter surfaces; JavaScript
syntax check passed. Both isolated installed environments passed `pip check`.
The final suite includes a backup during an uncommitted WAL write and preservation
of readable deterministic facts when generation permission is denied.

The real publication is
`a3d496b452611c1b395cd80c7cadb93c7acc5d2f5f0c786aae675730d0cf02b6`:
15 hypothesis-status/documented-claim records, 7 inline evidence objects.
Input SHA-256:

- charter: `f9d20abdef2fa77df98784a90f5d4c2e1a45907e6438ffa9d8235e5a9e063c75`
- evidence registry: `269df1a109f3dc432cc6d3cc9cc5852bce3e387d4222ea6998ed63fbc0378e30`

Exporter identity is the digest of its uncommitted source at export time:
`87081490928c90e1a322894aff6e1d1cf67d71f7ec114863963dd19ba820aa9d`.
It is deliberately not labeled a commit. The package preserves the measured export
timestamp and leaves unavailable scientific/availability times null. Initial
syntax rehearsal with a supplied future timestamp was not admitted to Cain; only
`frozen-reports-observed.json` is the demonstrated corpus.

One replay command failed with ValueError because PowerShell converted the JSON
timestamp to a localized date. Reading the original JSON timestamp as a string
fixed the command; the repeat exporter output had the identical publication ID.
An actual startup on PowerShell 7 initially failed because the old HTTP catch only
handled Windows PowerShell's exception type. Isolating the probe catch fixed it;
startup/reuse then passed on both shells. A new oversized-input test initially
failed in test setup because pytest embedded 2 MB in the test ID/environment; short
case IDs fixed the harness. Those were real failed attempts, not hidden successes.

Installed-wheel checks used a fresh environment and `python -I` outside all
checkouts. They verified packaged web assets and contract metadata, actual Crypto
import, duplicate receipt, query, evidence, projection rebuild, online backup,
new-destination restore, CLI, API and legacy profile access. Runtime imports came
from site-packages, not sibling repositories or editable installs.

Browser interaction was exercised against the source-based service and then the
installed wheel using the restored database: expand research, query H6, inspect
its charter, open preserved reference, inspect partial coverage, switch local user
and observe zero accessible records, then return to the admitted profile. Screenshot
inspection confirmed the panel remained inside the existing Cain interface. The
installed application is served by the repaired Windows launcher on loopback 8877.

Ollama's local `/api/tags` probe failed with URLError at 127.0.0.1:11434. No model was
downloaded or service installed to fabricate a real inference demonstration.
Provider execution therefore remains unavailable, while adversarial mock cases
exercise timeout, truncation, empty/invalid/oversized responses, unsupported quotes,
citations, scoped evidence and no fallback. Security results cover tested cases;
they are not a universal assurance or an authentication claim.

The prewritten five-question protocol produced 5/5 deterministic state/abstention
checks and 5/5 document-retrieval checks with identical curation and exact ID filters.
There were zero model calls and no measured human time. The dataset is small and
development-curated, with related themes; it does not demonstrate superiority over
RAG, usefulness of generation, scientific learning or profit. Keep deterministic
operation as the default; generation remains optional pending real evaluation.

Unexercised: real provider inference, Python 3.11, Linux/macOS, protected holdouts,
personal scientific databases, a full predictor suite, long-running recovery/power
loss and a human utility study. Core/Ops were unchanged; no scientific operation,
capital permission, scheduling, push, merge or external publication was performed.
