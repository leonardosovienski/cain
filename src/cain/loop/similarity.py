"""Similarity measures of the research loop, without the loop engine or the evaluator runner.

Kept apart so that `cain review` and `cain findings` (reachable from the `cain` console script) can rank by
similarity without reaching cain.loop.engine / cain.loop.evaluator, which are fenced out of the qualified
runtime (integration-crypto, prompt comum §4 option (b)).
"""


def lexical_similarity(a: str, b: str) -> float:
    left, right = set(a.casefold().split()), set(b.casefold().split())
    return len(left & right) / len(left | right) if left | right else 1.0


def similarity_function(kind: str, config=None):
    """Lexical overlap, or cosine of the configured local embedding model (qwen3-embedding).

    The embedding model is reached only on first use, so a loop that stops before comparing anything
    (evaluator changed, policy changed, closed hypothesis) does not need the model server."""
    if kind == "lexical":
        return lexical_similarity
    import math

    from cain.providers import configured_embedding
    from cain.settings import load_settings

    cache: dict = {}
    model: list = []

    def vector(text):
        if not model:
            settings = load_settings(config)
            settings.search_mode = "hybrid"
            model.append(configured_embedding(settings))
        if text not in cache:
            cache[text] = model[0].embed([text])[0]
        return cache[text]

    def cosine(a, b):
        left, right = vector(a), vector(b)
        dot = sum(x * y for x, y in zip(left, right))
        return dot / (math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(y * y for y in right)))

    return cosine
