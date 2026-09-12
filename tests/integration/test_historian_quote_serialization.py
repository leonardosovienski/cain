"""Replay observed local-model failures; containment tests, not inference tests."""
import json

import pytest

from cain.research.historian import explain
from tests.integration.test_research_l0 import publication, setup as research_setup


@pytest.fixture
def setup(tmp_path):
    return research_setup.__wrapped__(tmp_path)


@pytest.mark.parametrize('mode', ['literal', 'extra_quotes', 'omitted_field'])
def test_serialization_does_not_repair_or_rewrite_source_quotes(setup, mode):
    service, scope, ingest, _, _ = setup
    reason = 'A aprovação não foi concedida; reavaliar somente após 30 dias.'
    document = {'A72': {'state': 'WAIT', 'reason': reason, 'sample': '24 observações'},
                'A720': {'reason': 'A aprovação foi concedida.'}}
    text = json.dumps(document, ensure_ascii=False)
    ingest(publication(('A72', 'A720'), text=text))
    quote = json.dumps(reason, ensure_ascii=False)
    if mode == 'extra_quotes':
        quote += '""'
    elif mode == 'omitted_field':
        quote = json.dumps({'A72': {'state': 'WAIT', 'reason': reason}}, ensure_ascii=False)

    class Replay:
        def generate_json(self, prompt, context, schema):
            payload = json.loads(prompt)
            assert payload['evidence'][0]['text'] == text
            return json.dumps({'claims': [{'evidence_id': 'e1', 'quote': quote}],
                               'synthesis': ''})

    result = explain(service, scope, 'Explique a justificativa documentada de A72.',
                     Replay(), source_id='A72')
    if mode == 'literal':
        assert result['status'] == 'generated'
        claim = result['explanation']['source_quotes'][0]
        assert claim['quote'] == quote
        assert claim['support']['text'] == text
        assert result['explanation']['semantic_support'] == 'not_certified'
    else:
        assert result['status'] == 'generation_failed'
        assert result['error_code'] == 'UNSUPPORTED_QUOTE'
        assert result['explanation'] is None
