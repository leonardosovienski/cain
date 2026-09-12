# Independent re-review — final runner revision 3

Reviewed 2026-09-12. Final candidate source identity: 7da108d0172b7ccc2675404b7dbf0b8a21ad248ee814ea14f199225003d23861. Runner SHA-256: 5d665e2e80a0a729c881f0b9454edc3ce7d54186019f0443f8791cd800c7fed0.

## Result

All independently reported findings have a correction verified for the exercised paths. No unresolved reproducible finding remains from this bounded review. This is not a claim that the entire product is bug-free or that unrelated gates are closed.

- Persisted assertion corruption: rejected with CORRUPTION: diagnostic payload, reconfirmed in r3/RESULTS.json.
- Coherent corpus pagination under concurrent commit: verified in revision 2 with 60 entities, two pages, interleaved committed 61st entity; both pages stayed at 60 and a subsequent diagnostic read invalidated the old row. Diagnostics code is unchanged since that verification.
- Dependency identity: Bundle and Snapshot package bytes and distribution versions are now included; code inspection.
- Checkpoint preservation regression: retested COMPLETED checkpoint followed by oversized changed configuration. Original checkpoint content retained exactly at the JSON-value level; LAST_LIMIT.json recorded CONFIG_BYTES_CAP separately. r3/RESULTS.json shows checkpoint_preserved=true.
- Result quota: configuration itself fits at 1014 bytes under a 1024-byte configuration cap. A compact query with 425 characters of case metadata reached RESULT_AND_CHECKPOINT_CAP, returned exit 2, persisted LIMIT_REACHED with identity and zero completed results, and left only 559 bytes against quota 4096. Evidence r3/QUOTA_RESULT.json. Smaller cases completed within quota (1602 bytes for the unpadded case); early probe assertions expecting a limit for those smaller cases were test-expectation errors, not product failures.

Scripts: review_r3.py and quota_r3_boundary.py. Evidence stays inside C:/CAIN/work/supply-review-20260912. No shared candidate, active instance or producer files modified.

Full Linux and Python matrix, installed-wheel/UI acceptance, economic/scientific validation and derived-memory generalization require the integrator's separate evidence. Prior reports remain a record of superseded findings, not current blockers for these exact reviewed hashes.
