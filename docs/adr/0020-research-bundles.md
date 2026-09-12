# Records + Objects + References + Lineage

Status: locally implemented candidate; bounded Windows validation. No operational activation,
remote publication, scientific promotion or new economic evidence. Baseline is in
[BUNDLE_BASELINE.md](../research/BUNDLE_BASELINE.md).

## Decision and boundaries

Keep ResearchSnapshotV1 and its existing tables/queries. Add independently distributable
ResearchBundleV1 in Ecosystem's packages/research-bundle. Producers consume that contract,
not CAIN. CAIN consumes the same contract, never the domain runtime or producer DB. Core/Ops
need no change. A dataset is a logical entity, represented by received artifacts or references;
an artifact descriptor is not its content hash. The hash proves byte identity, not scientific truth.

Rejected: embedding datasets into SnapshotV1, reading producer databases from CAIN, a universal
market schema, a heavyweight external platform, and indiscriminate transfer of producer data.
These alternatives would couple authorities or increase exposure without supplying provenance.
Domain payloads retain their semantics. Scientific state is read-only; no frozen trials, models,
holdouts, cohorts or metrics are recalculated.

## Contract and identity

See the contract package README and packaged JSON Schema for the full required fields, grammar,
caps and canonicalization. It reuses the Snapshot serializer with no Unicode normalization.
Raw UTF-8 manifest and its hash are preserved separately from semantic bundle_id. Array ordering
and nulls remain meaningful. Entity signatures cover status, axis, clocks, payload, evidence and
supersession. Same producer namespace/id/revision with divergent content is CONFLICT, including
across stored scopes; import time never resolves truth. External relation endpoints must be
explicit; local endpoints must resolve. Role/type extensions use namespaced identifiers.

## Receiver authorization

Policy v1/v2 and their grants retain exactly their Snapshot meaning. Policy v3 adds required
`bundle_grants` independently of `grants`, while retaining v2 `imports`. Each bundle grant names
user/project/collection, domain/repository/publisher/stream, source allowlist, restriction-policy
allowlist, generate, roles, reference_only, max_manifest_bytes, max_object_bytes and max_received_bytes.
No missing grant permits bundles. Producer read/generate restrictions can only reduce permission.
One grant must admit an entire import and its limits; partial grants do not combine budgets.

Every query/materialization rechecks receiver policy. Entity membership is scope+bundle+entity;
resource membership is scope+bundle+descriptor. Same bytes can have independent memberships.
Role revocation removes resource metadata and relations to that local resource. Full revocation
removes bundle entities and receipts containing counts. Physical blobs remain until a separate
administrator decision; no automatic garbage collection. Unauthorized materialization is NOT_FOUND.
The app's existing loopback local scope selection remains organization, not remote user authentication.
Orphan inventory is local administrator CLI only, not an HTTP or scoped query capability.

## CAS and consistency

Default is `<research-db-parent>/research-objects`; override with CAIN_RESEARCH_OBJECTS or
CLI `bundle --objects`. Layout: `sha256/ab/<64-character digest>`. Physical paths never use a
producer filename. Import authorizes the whole manifest before artifact I/O, checks caps/free
space, safely opens regular input files, streams to staging on the CAS filesystem while hashing,
checks exact size/hash, fsyncs, promotes using exclusive hard link and syncs the directory where
supported. Existing blobs are reverified and reused; divergent blobs are not overwritten.

POSIX source traversal uses descriptor-relative O_NOFOLLOW on each transport component. Windows
rejects reparse points/junctions, opens with read sharing only (denying concurrent writers/deletion),
checks the final handle path and copies that handle. Both inspect file metadata before/after copy.
Destination directory creation checks links before descending. Storage/import root ancestors and
receiver policy remain administrator-owned: this is not a sandbox against a malicious local admin
replacing trusted root directories, changing policy or mutating DB/CAS directly. Windows cannot
claim POSIX directory-fsync guarantees. Hard-link support is required; failure is closed.

Filesystem + SQLite is not one ACID transaction. Durable immutable objects precede the SQLite
metadata commit. SQLite BEGIN IMMEDIATE serializes imports; failure after promotion may leave
an orphan. Tests inject projection failure, verify orphan reporting and successful retry. Staging
leftovers are reported, never silently ingested/deleted. Disk preflight is advisory, not reservation.
Scopes are bounded to 100 bundles/20 MB raw manifests; repeated rejected authorized operations can
still consume orphan storage. No claim of perfect disk-exhaustion prevention is made.

## Queries, verification and rebuilding

New tables research_bundles, research_entities, research_bundle_entities, research_artifacts,
research_relations and research_bundle_receipts are additive. Relevant scope, identity, hash,
membership and endpoint indexes are present; no arbitrary payload index. Queries verify authorized
raw manifests and projection consistency before filtering, return deterministic bounded pages,
and never open artifacts. Entity/resources/relations pages are independent. Verify additionally
checks every received object; missing/truncated/corrupt bytes are corruption, not references.
Rebuild uses raw manifests and never fetches sources or repairs blobs; complete scope authorization
is required, and corruption aborts the transaction.

CLI: `cain research ... bundle import|query|artifacts|lineage|historian|verify|rebuild|materialize|receipts|orphans`.
Materialize requires bundle ID, descriptor ID and an explicit new destination; it rechecks
authorization and hash, creates exclusively and does not overwrite. Read-only POST routes:
`/research/bundles/query`, `/artifacts`, `/lineage`, `/historian`. No remote fetch/blob/admin endpoint.
Historian metadata_context combines existing snapshots with bundle metadata, bounded to 100 KB,
labels FACTUAL and leaves derived empty. It is not persisted, so revocation is re-evaluated on every
call. Existing extractive LLM explanations remain SnapshotV1-only; richer LLM synthesis over bundles
is deliberately not enabled by this candidate. Large object content never enters a prompt.

## Backup and rollback

Administrative archive backup v2 includes workspace DB, knowledge documents, research DB, exact
receiver policy and every raw-manifest-reachable received blob, including revoked memberships.
Projection/raw consistency and content hashes are checked. Blobs deduplicate by digest; completion
manifest is last. Backups are independent SQLite snapshots, not a global transaction. Restore checks
the manifest, all files, reachable objects and policy before a new destination, then checks SQLite
integrity and DB-to-CAS references before RESTORE_COMPLETE. Original policy is preserved; activation
is manual and must review restored grants/import roots. Hashes detect corruption, not malicious
replacement of both content and unsigned manifest by a trusted administrator.

Version 1 backups remain restorable. Research-only DB backup/restore refuses received objects and
directs the operator to complete archive backup; references-only databases need no CAS bytes. New
tables are compatible with the baseline service's old Snapshot queries (tested with actual baseline
source). Rollback: stop using the candidate, restore the previous installed wheel and previous
v1/v2 policy; preserve the research DB, CAS, manifests and backups. Old CAIN ignores extra tables;
do not run its incomplete DB-only backup as a replacement for the v2 archive. No destructive
downgrade migration or removal of research data is required.

## Real producer scope and temporal meaning

Crypto exports the pinned scientific charter, literal hypothesis statuses and its explicit trial
identity mappings. Optional pinned GarimpoInvestimentos/trials.json admission preserves only
charter-selected records, including existing params, metrics, notes and registered_at. Selected
records are received canonical JSON representations, explicitly distinguished from whole original
file bytes. Missing records remain references; absent trial status stays UNKNOWN. No metric is
recomputed, and no exact input dataset or attestation is fabricated.

Brasileirao exports literal registry rows and references named in that registry. Selected horizon
text is retained. No admissible prediction/settlement was available in this allowlist; timestamps
remain null. Existing bitemporal code distinguishes event_at, published_at and ingested_at, and PIT
requires publication/ingestion at the applicable cutoff. Those clocks must remain distinct in any
future producer slice; no second temporal engine was added and no prediction was executed.

Stocks exports an existing engineering receipt's exact catalog source version: source_id, source
file hash, rows hash, observed_at, date range and counts remain distinct. observed_at is recorded_at
of catalog knowledge; available_at stays null because historical public availability is not
certified. Source and raw receipt are references; licensing is UNKNOWN. This is an exact existing
source-version anchor, not a fabricated DatasetSelection execution receipt or a new simulation.
The real DatasetSelection contract requires explicit source_ids/observed_before/start/end and has
not been replaced with latest. No domain database was opened by these exporters.

## External principles revalidated

Official documentation consulted during this task, without installing any platform:

- [MLflow artifact stores](https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/): metadata and artifact storage are separate.
- [DVC internal cache](https://doc.dvc.org/user-guide/project-structure/internal-files): content-addressed indirection and deduplication.
- [OpenLineage object model](https://openlineage.io/docs/spec/object-model/): explicit datasets, runs, inputs and outputs.
- [lakeFS internals](https://docs.lakefs.io/concepts/internals/): immutable data objects and metadata references.
- [Git objects](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects.html): content-addressed objects.

These support the architecture principles, not scientific validity or compatibility certification.

## Completion iteration

Entity/revision/domain/bundle filters now constrain incident lineage and resources.
Exact detail is available through bundle entity/artifact CLI and POST
/research/bundles/entity and /research/bundles/artifact. Relation type and artifact
identity are explicit filters; pages stay bounded and external endpoints never trigger I/O.

POST /research/bundles/explain admits only producer AND receiver generation grants.
It joins Snapshot received evidence and Bundle entity/relation metadata, with 20000-byte
input and 6000-byte output caps. Quotes must match supplied text exactly. All supplied
inputs are reauthorized after inference, including uncited inputs; failure returns fresh
facts and a generic error. Synthesis is DERIVED, semantic_support=not_certified. Responses
are ephemeral: no history cache, source insertion or replay. No artifact content is opened.

Crypto can explicitly pin both pipeline-power/2 harness attestations; expiry and control
verdicts remain literal, without trial linkage or current-validity inference. Brasileirão
can pin the existing contaminated retrospective replay; three clocks remain distinct and
PIT availability remains NOT_PROVEN. Stocks source inventory is not relabeled as an
executed DatasetSelection. Derived IDs are labeled content_hash/source_locator/source_key.

Process-exit tests now interrupt before promotion and before projection commit. Recovery
reports staging/orphans, preserves absence of false records, and retries successfully.
ENOSPC injection cleans incomplete staging. These tests are not physical power-loss tests.
Windows Python 3.11 and 3.14 were added to local validation; Linux requires another host
because WSL and Docker are unavailable here. No global runtime or operation was changed.
