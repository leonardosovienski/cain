"""The only place with OpenTelemetry attribute names.

The GenAI semantic conventions (``gen_ai.*``) are still in "Development" status and may be renamed;
everything else imports the names from here, so a rename is a one-file change. Checked against the
OpenTelemetry GenAI semantic conventions on 2026-09-24.
"""

# gen_ai.* (Development)
OPERATION_NAME = "gen_ai.operation.name"          # "text_completion", "chat", "execute_tool"
PROVIDER_NAME = "gen_ai.provider.name"            # e.g. "ollama", "llama.cpp"
REQUEST_MODEL = "gen_ai.request.model"
REQUEST_TEMPERATURE = "gen_ai.request.temperature"
REQUEST_SEED = "gen_ai.request.seed"
REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
RESPONSE_MODEL = "gen_ai.response.model"
RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"
USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
TOOL_NAME = "gen_ai.tool.name"
TOOL_CALL_ID = "gen_ai.tool.call.id"

OPERATION_TEXT_COMPLETION = "text_completion"
OPERATION_CHAT = "chat"
OPERATION_EXECUTE_TOOL = "execute_tool"

# cain.* (ours; stable)
CAIN_CALL_ID = "cain.inference.call_id"
CAIN_CACHE_KEY = "cain.inference.cache_key"
CAIN_CACHE_HIT = "cain.inference.cache_hit"
CAIN_INFERENCE_MODE = "cain.inference.mode"
CAIN_MODEL_SHA256 = "cain.model.gguf_sha256"
CAIN_LOOP_ID = "cain.loop.id"
CAIN_LOOP_ATTEMPT = "cain.loop.attempt"
CAIN_OUTCOME = "cain.outcome"
