# Atualização 0.4.4

Consulte [DELIVERY_044.md](DELIVERY_044.md): política v2, exportadores reais Stocks/Brasileirão e backup completo. O protocolo abaixo descreve a base 0.4.3, ainda compatível; a indicação final de fixtures foi superada pela integração real delimitada.

# Cain 0.4.3 local L0 pilot

Cain now imports admitted local publications, queries structured records, displays
coverage and preserved evidence, and optionally explains through its existing local
provider protocol. Research is separate from conversational memory and scientific
producer state. Without `CAIN_RESEARCH_POLICY` the research API is disabled; legacy
projects, sessions, preferences, history and feedback retain their existing storage.

The research panel now records the selected existing workspace session. Use
"Histórico de pesquisa desta conversa" to reopen a query after restart. Deterministic
queries run again under current permissions; saved explanations are marked historical
and withheld before retrieval when any supporting publication is no longer readable.
The legacy conversational turn/decision/feedback identifiers are unchanged.

CLI history uses the same service: `cain research --session SESSION history` and
`cain research --session SESSION recall ENTRY_ID` (with the usual policy/database/scope
options). Omitting the session selects only unsessioned CLI history. API callers can
use `POST /research/readiness` for a measured storage/query check of a selected scope;
capabilities alone does not attest availability or inference.

Every query verifies all admitted projection rows and membership before applying
filters. Corrupt or missing filter columns/links therefore fail explicitly rather
than manufacturing an empty result. Rebuild repairs projections from preserved originals.

The evaluation harness accepts `--config EXISTING_LOCAL_CONFIG` to run both documentary
and structured model arms with the same provider and per-arm call budget. Without that
option it makes zero model calls. Exact source-ID filters are available to both arms;
the documentary catalogue comes directly from admitted publications. Semantic scoring
remains a human task, never inferred from quote validity. Real documentary compatibility
examples can be prepared with `evaluation/document_examples.py` from its two explicitly
pinned supported reports; it is local curation, not an official domain exporter.

## Install and run

Install the small contract wheel first, or provide its directory to pip. From this
checkout: `python -m pip install --find-links vendor -e ".[dev]"`. For installed
distribution: `python -m pip install --find-links WHEELS "cain-research[api]==0.4.3"`.
WHEELS must contain Cain and `predictor_research_snapshot-1.0.0-py3-none-any.whl`.
The unmodified Python >=3.11 requirement is retained; the local run used 3.12.

Set `CAIN_RESEARCH_POLICY` to a trusted receiver policy JSON, `CAIN_RESEARCH_DB` to
Cain's research database and `CAIN_DB` to its legacy database. Then run:

```text
python -m uvicorn cain.api:create_app --factory --host 127.0.0.1 --port 8877
```

The Windows initializer's `api` and `web` modes no longer prepare Ollama. Help,
imports, queries and evidence inspection need no provider or embeddings. Health
identifies `cain-local-api`, API contract 1, and explicitly leaves inference and
provider availability unverified. A service merely answering HTTP is not proof of
inference. Model absence is never disguised by FakeLLM. The local user selector is
organization, not remote authentication; preserve loopback, Host and Origin checks.

## Receiver policy

```json
{"version":1,"import_root":"C:\\Cripto\\cain-l0\\publications","grants":[{
 "user":"leo","project":"","collection":"crypto","domain":"crypto",
 "repository":"https://github.com/leonardosovienski/cripto-predictor",
 "publisher":"crypto-local","stream":"frozen-reports",
 "sources":["charters/scientific_state.json","docs/EVIDENCE_REGISTRY.md"],
 "policies":["crypto-frozen-reports-local/1"],"generate":true}]}
```

This example authorizes only this local report acervo. Copying labels from a package
does not authenticate its author; control the inbox, policy and database with OS
permissions. Restrict sources before importing. Policy is re-read for queries and
evidence inspection, so revocation also hides stored content. There is no remote
fetch, scientific database access, embedding or automatic web fallback. A grant is
specific to user/project/acervo and producer namespace. Other projects need their
own explicit grant and import. Permission cannot be broadened by imported text.

## CLI

Global research options precede the subcommand. The policy, db and scope below are
shared by all operations; API/UI call the same application service.

```text
cain research --policy POLICY --db DATABASE --user leo --collection crypto import frozen-reports-observed.json
cain research --policy POLICY --db DATABASE query --source-id H6
cain research --policy POLICY --db DATABASE query --domain crypto --status CLOSED_INSUFFICIENT_SAMPLE --limit 10 --offset 0
cain research --policy POLICY --db DATABASE query --text INCONCLUSIVE
cain research --policy POLICY --db DATABASE coverage
cain research --policy POLICY --db DATABASE evidence PUBLICATION_ID:EVIDENCE_ID
cain research --policy POLICY --db DATABASE receipts
cain research --policy POLICY --db DATABASE verify
cain research --policy POLICY --db DATABASE rebuild
cain research --policy POLICY --db DATABASE backup NEW_BACKUP.db
cain research restore BACKUP.db NEW_RESTORE.db
cain research --policy POLICY --db DATABASE explain "O que a fonte registra?" --source-id H6 --config CONFIG.toml
```

Other query filters: `--kind`, `--revision`, `--reason`, `--completeness`.
All outputs are JSON. Import paths are relative to the admitted import root.
Traversal, absolute paths, symlinks/junctions and unsupported objects are rejected.
Source/status/reference IDs are data, not SQL, filesystem paths or executable plans.

## Interface

Open the existing Cain app, select local user `leo` and project `Geral`, expand
**Pesquisa · L0 Historian**, keep acervo `crypto`, enter `H6` in **Identidade da
fonte**, and click **Consultar acervo**. Expand **Cobertura, lacunas e limitações**
and the source entry. **Inspecionar evidência preservada** resolves an application
reference ID. Clearing the ID enumerates records with next/previous pages.
Changing user or project clears results and requests the new scope. After restarting
the application the imported acervo and evidence remain queryable.

The optional explanation button sends only the question and admitted evidence to
the configured local provider. Factual states and counts stay deterministic;
generated claims must be exact quotes from supplied evidence and known reference
IDs. Synthesis is separately marked proposed and semantically uncertified. Timeout,
truncation, invalid JSON/types/citations and unsupported quotes produce explicit
failures. Input budget is 6000 UTF-8 bytes; response budget is 6000 bytes; question
limit is 1000 characters. Oversize requests fail with guidance rather than hidden
truncation, retries or model substitution. The provider's actual measured metadata
and missing digest are explicit. Explanations and query receipts use Cain's own
scoped operational history and never become scientific source records.

## Persistence and recovery decision

One separate SQLite database contains (1) received raw publications, (2) rebuildable
record and membership projections, (3) receipts, conflicts and query/response history.
There is no two-store atomicity claim: inline evidence and projection commit together
in SQLite. Import validation precedes promotion. Same occurrence/revision with
divergent payload rejects the complete publication and records a conflict. Failure
receipts commit separately after rollback; inability to write that receipt is an
explicit error. Unknown or excluded content is not retained in diagnostic quarantine.

Reimporting an identical publication produces another receipt, not duplicate
records. Namespaces prevent cross-domain collisions; supersedes links are preserved,
unordered revisions coexist, and omitted records never delete history. Counts
distinguish revisions and source occurrences, and are never trial counts.

`rebuild` verifies the archive and replaces only the projection in one transaction.
`backup` uses SQLite's online backup API, including active transactions/WAL semantics;
`restore` accepts only a new destination. Backups preserve all scopes and operational
history, so they are local administrator operations, not HTTP endpoints. Use OS
protection for backup files. Keep policy and source authorization documents alongside
the backup; backing up bytes does not grant future permission to read them.

Rollback: stop the local process, retain research.db and its consistent backup,
then use the old Cain code against the untouched legacy db. Research data remains
in the separate database; do not run old code as a research-db migrator. Removing the
research policy disables the feature without erasing archives or receipts. This
pilot does not migrate an active personal database.

## Scope and validation limits

Transport limit: 2 MB/publication, 200 records and 200 evidence objects, 100000
characters/object, nesting depth 18. Consumer limits: 500 publications and 20 MB
admitted content per acervo, page size 1–50, response <=1 MB. Large scopes fail
explicitly and should be split; this is a deliberately small local pilot.

The initial exporter admits two frozen Crypto reports, totaling 15 source records
and 7 evidence objects. They are documented claims/status reports, not reproduced
trials. The separate ongoing Crypto checkout and later research are outside this
snapshot. No universal absence, current truth, statistical power, profit or research
learning follows from an engineering test passing. Structured reasons absent from
the source stay null; narrative evidence may explain them to a reader.

The independent contract distribution belongs to Ecosystem, and the exporter to
Crypto. Cain does not import predictor internals; predictors do not depend on Cain.
Stocks/Brasileirão are represented only by explicitly synthetic compatibility cases.
Their capabilities registry is not on this file bridge and was not changed. Core and
Ops are not changed. There is no new Trial Registry, evaluator, executor or autonomy.

See `evaluation/l0_protocol.json` and `evaluation/evaluate_l0.py` for the fixed
small-corpus recovery comparison. The documentary baseline receives the same
curation, identity filter and evidence. Model unavailability leaves that comparison
partial; passing five curated questions is not evidence of advantage over RAG.
