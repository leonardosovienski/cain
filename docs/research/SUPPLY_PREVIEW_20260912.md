# CAIN Supply: isolated preview candidate

This candidate follows the published/remediated working state at
945f58e9d780d8121c584e7d9bd271d0a7c40296. It is not installed in the active user instance.
Session evidence and the complete manual guide are in
`C:/CAIN/work/supply-preview-20260912`.

Evaluation scenarios, probes and rubric are now packaged as byte-preserved resources.
Default loaders resolve the installed resources; explicit caller paths remain supported.
Execution receipts fingerprint actual installed package bytes instead of claiming an
empty checkout source tree. Git identity remains unknown for an installed distribution.

`cain research ... bundle diagnose` is an explicitly requested structural diagnostic.
`bundle diagnostics` retrieves still-valid diagnostics. They count entities,
relations, received descriptors and reference-only descriptors over generation-authorized
metadata. They do not run models, fetch resources, infer scientific results or become
independent source evidence. The feature is off by default. Repeated creation is
idempotent; scope, policy, source-view or code changes hide prior diagnostics.
Revocation is checked on every read. Historical rows stay in their own SQLite table.
Existing bundles in the real preview deny generation: the operation correctly refuses.
Persistence and revocation tests use synthetic fixtures; no real-corpus benefit is claimed.

The identified `runner.py` session harness executes finite public CLI evaluation cases.
It validates installed code, policy, corpus and prior output hashes on resume; it never
modifies permissions, issues scientific decisions or activates a scheduler.
Its receipts are authored by the Codex engineering harness, not by a model or CAIN learning.

Windows installed tests, CLI population, explicit administrative approval/import,
duplicate admission, offline restore/materialization and revocation are separately
recorded. Linux remains a required unexecuted gate for this new candidate. Historical
Linux failures and their old manifest/overlays have not been rewritten.
