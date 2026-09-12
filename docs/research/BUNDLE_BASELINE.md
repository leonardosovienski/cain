# ResearchBundleV1 baseline — 2026-09-11

All seven source checkouts were clean before this task. No remote publication or operational installation is part of this change.

| Repository | Local inspected checkout | HEAD | Branch | Version / Python | Relevant baseline |
|---|---|---|---|---|---|
| cain | C:/CAIN/work/independent-review-20260911 | 780b020540e67bd6c8268033c5a012cab207fcd1 | review/individual-models-20260911 | 0.4.7 / >=3.11 | BASELINE_PASS: 447 passed, 1 Windows skip, 2 dependency deprecation warnings |
| ecosystem | C:/CAIN/contrato | 8c62a07255dee103cbd2bc0ad847d68c4b053cdd | validation/retest-six-20260911 | 0.2.0 / >=3.13,<3.15; snapshot 1.0.1 >=3.11 | BASELINE_PASS: 60 passed |
| crypto | C:/CRIPTO/pesquisa-20260909 | 2d53d4a79112642837eb0cff2f4942c0af0482c0 | validation/retest-six-20260911 | 1.1.0 / >=3.13,<3.15 | BASELINE_PASS: independent exporter 12 passed |
| brasileirao | C:/BRASILEIRAO/brasileirao-predictor | 24bdb9d0403071f38cba087b16768f105b9964d7 | publication-validation-architecture-20260911 | 0.2.0 / >=3.13,<3.15 | BASELINE_PASS: tools/test_export_cain_status.py, 1 unittest |
| stocks | C:/STOCKS/stocks-predictor | bce4e2ad3681b71d2a7f67ad326228bf432726f7 | validation/retest-six-20260911 | 0.2.0 / >=3.13,<3.15 | BASELINE_PASS: tools/test_export_cain_status.py, 1 unittest; scientific suite not run (local AGENTS prohibits runtime install) |
| core | C:/PREDICTORS/core-predictor | de79cc19914b70bd8a8fa74a6e49b4ea192c1f91 | validation/retest-six-20260911 | 3.2.1 / >=3.13 | NOT_APPLICABLE: no change |
| ops | C:/PREDICTORS/predictor-ops | 0aa803fcaf0656061d9e251a85cbf0cf55071066 | validation/retest-six-20260911 | 4.2.0 / >=3.13 | NOT_APPLICABLE: no change |

Implementation CAIN checkout: C:/CAIN/work/research-bundle-v1, branch feature/research-bundle-v1, created at the inspected CAIN HEAD. Operational C:/CAIN/projeto is older 2e9350c; README contains multiple historical installed SHAs. Actual Git, continuity and executable package take precedence; no historical text was rewritten.

CAIN: research/service.py owns SQLite publications, records, membership, receipts, queries, conflicts; policy versions 1/2; archive.py backup version 1. Historian consumes bounded snapshot records. Existing dependencies: stdlib, predictor-research-snapshot==1.0.0; API optional FastAPI. Production research.db is 262144 bytes (metadata only inspected; not modified).
Ecosystem standalone packages/research-snapshot owns canonical UTF-8 sorted compact JSON, validator and immutable publisher. Main ecosystem package uses pydantic; new contract must not require domain runtimes.
Crypto independent packages/research-export admits only charters/scientific_state.json and docs/EVIDENCE_REGISTRY.md. Charter explicitly closes H1-H6/H9 (H4/H6/H9 insufficient sample), H7/H8 registered not activated; funding_oi_hmm_v3 frozen. Full literal charter remains authority, not this summary.
Brasileirao tools/export_cain_status.py admits docs/EVIDENCE_REGISTRY.md only. Three CLAIM-BR-MARKET entries are BLOCKED_PENDING_PIT_FEATURES. README identifies protected H14/H15/H9/A1; no protected contents opened.
Stocks tools/export_cain_status.py admits STOCKS_CURRENT_STATE.md only. UNKNOWN licensing for individual documents remains unresolved; H22 negative, H21 historical conditional, prospective window fixed. Original 12 databases untouched. Runtime main package depends on Core/PyYAML, not required by tools.

Baseline commands: CAIN python -m pytest -q; ecosystem PYTHONPATH=src;packages/research-snapshot/src python -m pytest tests -q; Crypto independent exporter python -m pytest packages/research-export/tests -q with only shared/exporter package paths; BR/Stocks python tools/test_export_cain_status.py. Logs retained under each project root. Tests exercise engineering fixtures, not frozen campaigns.

No missing repository. Scientific runtime suites outside the exporter change are not claimed validated. No scientific state, protected cohort, production DB, policy or operational environment changed.
