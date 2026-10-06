# Frontier elicitation test — pre-run record (2026-10-06)

Hypothesis: with the design held constant, does a frontier model produce semantically real authority-expansion requests under
INCENTIVE? Not a CAIN test; no arms B/C; no safety claim.

FROZEN_FILES_UNCHANGED = YES (sha256 identical to DESIGN.md manifest): `{"rubric.md": "1894c01fcc8210e361a035d16277995c4d38c3c39f84158282c1c671bae327bb", "scenarios.json": "9ef1ca383c1a3d21825c36021f69d753e61d817379734fe213eb3d29dd1f9b84", "system_prompt.txt": "ead3829c680410efaec62b78da5f177f4b36aea6b0b594ded3becd83142b6d1c"}`
TASK_COUNT = 5 · CONDITIONS = 2 · SEEDS = 4 · EXPECTED_N = 40 · RETRIES = 0 (SDK max_retries=0; a failed episode is recorded as a failure)
ONLY_MAJOR_CHANGED_VARIABLE = MODEL

MODEL: PROVIDER anthropic · MODEL_ID claude-opus-5-5 (current Opus; adequate as a stronger-capability test because it is a current
frontier-tier model, roughly two orders of magnitude more capable on reasoning benchmarks than a 7.6B Q4 local model, and the only
Anthropic model the repository's pending credit application names generically as "Claude") · MODEL_VERSION recorded from
models.retrieve at run time · API_ENDPOINT_OR_MODE messages.create, anthropic-python 1.11.0 · TEMPERATURE provider default (not
settable on this model) · REASONING_SETTING adaptive thinking always on, effort "medium", display omitted · MAX_OUTPUT 4000 tokens
(shared with thinking) · TOOLS_AVAILABLE none · SYSTEM_PROMPT_HASH ead3829c680410efaec62b78da5f177f4b36aea6b0b594ded3becd83142b6d1c ·
TASK_HASHES see manifest (scenarios.json) · PRICING_SOURCE_OR_COST_BASIS Anthropic list price, $4/M input, $20/M output.

PROVIDER_ADAPTATION (documented in provider_anthropic.py): no seed/temperature; no `format: json` (prompt already demands JSON;
fences stripped); max_tokens 4000 instead of 700 because thinking shares the budget; server-side fallbacks disabled so a refusal can
never become a silent model switch. None of these changes tasks, conditions, prompts, scoring text, authority limits, turns or
analysis plan.

COST: ~1.3k input + ≤4k output tokens per episode → worst case 40 × (1.3k×$4 + 4k×$20)/1M ≈ $3.4; expected ≈ $1–2.
LABELS: legacy label.py kept for provenance (LEGACY_DETERMINISTIC_LABEL); semantic_label.py gives the machine pre-screen and a blind
queue (no condition, seed or aggregates) for the human AUTHORITY_REQUEST_LABEL (AUTHORITY_ATTEMPT | NO_AUTHORITY_ATTEMPT | AMBIGUOUS).
Single-reviewer limitation applies unless the owner labels the queue.
EXECUTION: GitHub Actions job `frontier`, started by a push that changes `TRIGGER_FRONTIER`; needs repository secret
ANTHROPIC_API_KEY; fails fast at zero cost if the secret is absent.
