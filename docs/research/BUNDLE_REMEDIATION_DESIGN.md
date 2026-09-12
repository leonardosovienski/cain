# Remediation design — 2026-09-12

Order mandated by the receiver owner: F03, F02/F04, F01; implement P1;
adversarial retest; F07; F05; F06; F08/F10; F09; E2E; mini-audit.
This is a local candidate, not a stabilization or release decision.

## 1. F03 — administrative publication before scoped attachment

Global namespace/entity/revision consistency remains global. Adding scope to
the conflict query or hiding its error would not solve the information leak.

Introduce an explicit local-administrator `bundle approve` operation, unavailable
over HTTP. Like backup and orphan inspection, this requires trusted local access
to the receiver database and policy. It is not a consumer permission inferred
from read grants. It validates the exact manifest, checks global signatures in
one write transaction, reserves those signatures permanently, and records the
exact canonical bundle hash approved for the destination scope. Approval does
not create readable memberships or claim that object bytes were received.

Scoped `import` accepts only that already approved hash. It does not decide global
publication conflicts. An arbitrary guessed revision or altered payload receives
NOT_AUTHORIZED regardless of other scopes. A prior read grant alone no longer
permits import. Approval failures containing CONFLICT are administrator-only.
Existing archives stay readable; importing them again requires explicit approval.
The global reservation ledger survives rebuild and backup. Conflicting reservations
cannot be created by concurrently approving packages. No automatic approval in
query, HTTP, import, or restore. Direct Python/SQLite access remains administrative;
this local application is not an OS sandbox for hostile code with database access.

## 2. F02/F04 — descriptor identity before authorization

Add profile local-research/2, keeping the ResearchBundleV1 envelope and old
local-research/1 validator/read compatibility. In profile 2, an external artifact
endpoint revision is SHA256(canonical(complete artifact descriptor)). Local
artifact endpoints remain relative to this bundle with null revision, avoiding
a bundle-hash cycle. Entity endpoints are unchanged. Same content with different
role, locator, metadata or availability is a different descriptor identity.

Relations are returned only when every artifact endpoint resolves to an authorized
descriptor in the caller's archives. External is never a permission. A profile-1
external endpoint matching a local descriptor resolves locally and uses its role;
otherwise its ambiguous identity is withheld. No raw is rewritten. Unresolved
profile-2 externals are also withheld; the receiver neither fetches nor searches
other scopes to resolve them. New producers emit profile 2.

## 3. F01 — complete-scope verification

Verify and rebuild first require all archived bundles and all their artifact roles
and reference permissions. If any are unavailable, deny the entire operation
before any CAS read or projection mutation. Empty scope verifies zero bundles.
No partial result is called verified. Administrative backup reachability remains
independent of consumer roles, so revoked objects are retained and checked there.

## Acceptance

Test hidden-scope present/absent indistinguishability, administrative global
conflicts and concurrent reservations, external/local role revocation through
query/API/CLI/Historian, and zero protected I/O on verify/rebuild denial. Preserve
old raw bytes and Snapshot behavior. Record fresh evidence separately from the
immutable retrospective audit.
