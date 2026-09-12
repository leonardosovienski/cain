# Exact candidate Linux validation

This kit reconstructs candidate d00bbc6fb910b3c51be6720d21012f4655258468adb7d7335451974929c58752.
The transport manifest identity is ef7db4251dfaaf91bf6cbc0e2d3bfad8c8ad19a100d690574da351b9fc51958a,
using the separate cain-candidate/1 algorithm. Neither identity is a Git commit.
At the historical tested commit below, the branch root retained baseline source.
The current branch also materializes that exact candidate directly in src/.
cain-overlay.zip preserves the original candidate runtime. The workflow reconstructs it and checks all recorded bytes before execution.

The exact runtime at commit f0cfb92b20a41e615d28f41e93bae589d680cf84 passed
[Actions run 34702803998](https://github.com/leonardosovienski/cain/actions/runs/34702803998).
CAIN/Bundle/Snapshot validation covers Python 3.11 through 3.14 on Linux: 574 passed
and two Windows-only launcher skips per version. Separate targeted POSIX checks
passed without skips. Producer export-tool integration covers Python 3.13 and 3.14,
including real public Snapshot and Bundle exports, import, backup, offline restore,
and materialization of received objects. This does not validate full scientific runtimes.

CI exports already public committed producer sources and uploads bounded evidence
and command receipts, including public metadata and text. No private scientific
database or local Windows staging corpus was uploaded. Source grants were preserved.
The Linux Stocks Bundle contains two entities; the preserved Windows corpus has
three because it also contains an optional selection that was not reproduced in CI.

Publication of this validation branch and Actions was authorized. No merge, release,
active installation, or scientific execution was performed. A later README-only
commit does not change the tested runtime and must not be described as a new CI run.