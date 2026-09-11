import importlib.util
from pathlib import Path

from cain.llm import OllamaLLM
from cain.research.workflows import model_identity


def test_recording_provider_retains_real_model_identity_checks(monkeypatch):
    path = Path(__file__).parents[2] / 'tools/verify_individual_models.py'
    spec = importlib.util.spec_from_file_location('individual_evaluator', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    provider = module.RecordingProvider(OllamaLLM(model='fixture:1', think=False, num_ctx=4096,
                                               num_predict=512, max_input_bytes=3000))
    assert isinstance(provider, OllamaLLM)
    class Reply:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, limit):
            return b'{"models":[{"name":"fixture:1","digest":"real-digest"}]}'
    monkeypatch.setattr('cain.research.workflows.urlopen', lambda *a, **kw: Reply())
    identity = model_identity(provider)
    assert identity['model_digest'] == 'real-digest'
    assert identity['num_ctx'] == 4096 and identity['think'] is False
