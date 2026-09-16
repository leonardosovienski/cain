import json

from cain.research.analysis import review
import qa_br_fixture as cases

setup = cases.setup


def test_hypothesis_instruction_reaches_provider_with_literal_evidence(setup):
    service, scope, ingest, _, _ = setup
    text = ('| ID | enunciado | estado | evidência | ressalva |\n'
            '|---|---|---|---|---|\n'
            '| QA-BR-1 | Informação incremental em H-6h | BLOCKED_PENDING_PIT_FEATURES | '
            'no model comparison executed | feature availability not proven |\n')
    ingest(cases.publication(('QA-BR-1',), domain='brasileirao', text=text))

    class Capture:
        base_url = 'http://127.0.0.1:11434'
        calls = 0

        def generate_json(self, prompt, instruction, schema):
            self.calls += 1
            assert "Explicitly label" in instruction
            assert "features means model input variables, not resources" in instruction
            payload = json.loads(prompt)
            assert payload['source_id'] == 'QA-BR-1'
            assert 'BLOCKED_PENDING_PIT_FEATURES' in prompt
            assert 'feature availability not proven' in prompt
            return json.dumps({'citations': [next(iter(payload['excerpts']))],
                               'analysis': 'A hipótese está bloqueada; não há comparação executada.'})

    model = Capture()
    result = review(service, scope, 'Qual a interpretação da hipótese QA-BR-1?', model,
                    role='synthesis', source_id='QA-BR-1')
    assert result['status'] == 'generated'
    assert result['generation']['prompt_version'] == 'addressable-review/18'
    assert result['explanation']['semantic_support'] == 'not_certified'
    assert model.calls == 1


def test_absent_claim_is_not_fabricated(setup):
    service, scope, _, _, _ = setup

    class Forbidden:
        base_url = 'http://127.0.0.1:11434'
        def generate_json(self, *args):
            raise AssertionError('No inference for an absent source')

    result = review(service, scope, 'Qual a hipótese ausente?', Forbidden(),
                    role='synthesis', source_id='QA-MISSING')
    assert result['generation']['called'] is False
