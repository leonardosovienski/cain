from dataclasses import asdict

from cain.evaluation.harness import EvaluationConfig, _model


def test_worker_round_trip_preserves_explicit_generation_controls():
    config = EvaluationConfig(mode='functional', provider='ollama', model='qwen3.5:0.8b',
                              think=False, num_ctx=4096, num_predict=512, max_input_bytes=3000,
                              request_timeout=240)
    worker_config = EvaluationConfig(**asdict(config))
    provider = _model(worker_config)
    assert provider.think is False
    assert (provider.num_ctx, provider.num_predict, provider.max_input_bytes) == (4096, 512, 3000)
    assert provider.timeout == 240
