"""Anthropic Messages API provider for the elicitation pilot (frontier arm). Same frozen prompts; only the model changes.

PROVIDER_ADAPTATION (recorded in RUN_META, none touches the experimental manipulation):
- sampling: Claude Opus 5.5 rejects non-default temperature/seed; the 4 seeds become 4 independent samples at default
  sampling (seed is still recorded as the episode label);
- output format: no `format: json`; the frozen system prompt already demands a JSON object; code fences are stripped
  before parsing and the raw text is kept;
- thinking: always on for this model; effort fixed at "medium" (its default) and recorded; thinking display omitted;
- max_tokens: 4000 (thinking shares the budget; 700 would truncate); stop_reason recorded;
- no server-side fallbacks: a refusal must stay a refusal of THIS model, never a silent model switch.
"""

from __future__ import annotations

import os

import anthropic

MODEL = os.environ.get("FRONTIER_MODEL", "claude-opus-5-5")
EFFORT = "medium"
MAX_TOKENS = 4000

_client = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(max_retries=0)  # RETRIES = 0 is part of the protocol
    return _client


def identity() -> dict:
    info = client().models.retrieve(MODEL)
    return {
        "provider": "anthropic",
        "model": MODEL,
        "model_display_name": info.display_name,
        "model_created_at": str(info.created_at),
        "api": "messages.create",
        "sdk": f"anthropic-python {anthropic.__version__}",
        "effort": EFFORT,
        "thinking": "adaptive (always on for this model), display omitted",
        "max_tokens": MAX_TOKENS,
        "sampling": "provider default (temperature/seed not settable on this model)",
        "fallbacks": "disabled",
        "tools": [],
        "pricing_basis": "Anthropic list price 2026-09: $4/M input, $20/M output",
    }


def chat(system: str, user: str) -> dict:
    resp = client().messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        output_config={"effort": EFFORT},
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else stripped
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]
    usage = resp.usage
    return {
        "message": {"content": stripped},
        "raw_text": text,
        "stop_reason": resp.stop_reason,
        "stop_details": resp.stop_details.model_dump() if resp.stop_reason == "refusal" and resp.stop_details else None,
        "model_served": resp.model,
        "request_id": resp._request_id,
        "usage": {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens},
        "cost_usd": round(usage.input_tokens * 4e-6 + usage.output_tokens * 20e-6, 5),
        "done_reason": resp.stop_reason,
        "total_duration": None, "eval_count": usage.output_tokens, "prompt_eval_count": usage.input_tokens,
    }
