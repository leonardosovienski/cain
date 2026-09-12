# Records + Objects + References + Lineage

Status: local remediation candidate, 2026-09-12. Previous PASS reports describe
older commits and do not certify the ten findings of the retrospective audit.
See [ordered design](../research/BUNDLE_REMEDIATION_DESIGN.md) and
[current verification](../research/BUNDLE_REMEDIATION.md).

## Publication authority

ResearchSnapshotV1 remains unchanged. The independent Bundle contract has no CAIN
or domain runtime dependency. Core/Ops remain unchanged. CAIN never opens producer
DBs. Entities, descriptors, received objects and opaque references stay distinct.

Policy v1/v2 retain Snapshot semantics. Policy v3 adds explicit bundle grants:
exact scope/origin, sources, policies, roles, reference/generation and size limits.
One grant must admit a whole import. Read grants do not authorize publication.

A trusted local administrator first runs `bundle approve MANIFEST`. This reserves
global namespace/entity/revision signatures and the exact bundle hash for a scope,
without receiving objects or creating readable membership. `bundle import MANIFEST`
requires that approval and current grants. Altered packages require new approval.
Conflicts are administrative; unapproved scoped attempts get NOT_AUTHORIZED without
global conflict inspection. Approvals and reservations survive rebuild and backup.
Existing archives remain readable; new duplicate imports require approval.
There is no approval/import HTTP route. The administrator CLI, database and policy
must not be delegated to hostile scoped consumers. Local scope selection is
organization, not remote login or an OS sandbox for code with database access.

## Identity and authorization

Validator accepts local-research/1 and local-research/2. In profile 2, external
artifact revision is SHA256(canonical(full descriptor)); local artifacts remain
bundle-relative with null revision. Relations require resolved, authorized artifact
descriptors in the caller's archives. No cross-scope or network resolution occurs.
Legacy ambiguous external relations remain in raw archives and are withheld unless
locally resolvable. External never bypasses roles. Old raw bytes are not rewritten.

Each query rechecks permission. Full revocation hides entities/evidence/receipts;
role revocation hides resources and their relations. Verify and rebuild deny the
whole operation before CAS I/O when any bundle/role/reference permission is absent.
Administrative backup independently preserves and verifies revoked objects.

## Durability and raw preservation

CAS uses sha256/prefix/digest, with staging, streamed verification, file fsync,
exclusive hard link, and directory sync before SQLite commit. POSIX synchronizes
parent entries throughout the directory chain, including retries and concurrent
creation. Windows cannot claim equivalent directory-fsync durability. Storage
ancestors must be trusted; reparse points fail closed and hard links are required.

First raw bytes remain unchanged. At most seven additional JSON variants are
preserved by scope/bundle/raw SHA; variants and first raws share a 20 MB scope cap
and at most 100 bundles. New receipts commit to preserved raw bytes. Old receipts
are not rewritten. Approvals have their own 100-bundle/20 MB per-scope ceiling.
Backup includes variants, approvals, reservations, databases, policy and received
objects; restore validates before its completion marker into a new destination.
No operational activation or automatic orphan deletion. Filesystem and SQLite are
not one transaction: failed imports can leave staging/orphans. Fault injection
is not physical power-loss certification.

## Interfaces and provenance

CLI: approve (administrator), import, query, entity, artifact, evidence, artifacts,
lineage, historian, verify, rebuild, materialize, receipts, orphans (administrator).
HTTP exposes query/details/lineage/Historian/explain, without arbitrary file paths.
Evidence detail identifies exact bundle/id; metadata pages stay bounded. Historian
includes authorized evidence without reading object bytes, caps factual context at
100 KB and generation at 20 KB input/6 KB output, checks exact quotes and reauthorizes
all input after inference. Synthesis is ephemeral DERIVED and uncertified.

Producers supply origin and restrictions. exporter_revision fingerprints retrievable
exporter-provenance/1 evidence with actual producer/shared code/schema hashes,
package versions and Python version. Entity evidence stores source and payload
hashes without duplicating full payload. New provenance can change representation
revision hashes without changing domain states. Existing Snapshot and raw bytes stay.

## Current limits

Historical Linux CI covers prior feature commits, not this remediation. No push,
release or production installation here. Crypto sources remain admitted charter,
trials and attestations. Brasileirão replay remains retrospective/contaminated,
without invented prediction, settlement or PIT certification. Stocks optionally
uses existing bounded DatasetSelection on a verified scratch copy; no simulation
runs and no prices transfer while licensing is UNKNOWN. No scientific campaign,
protected cohort or economic validation is repeated. Final evidence is recorded in
the remediation report before any stabilization discussion.