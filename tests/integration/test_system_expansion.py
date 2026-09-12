"""Adversarial system regressions beyond the known H4/H6 field wording."""
import json
import pytest
from cain.research.historian import explain
import test_research_l0 as cases

setup = cases.setup


@pytest.mark.parametrize('text', [
    'A versão passou por testes internos; a produção continua não autorizada.',
    'Não há efeito demonstrado; a conclusão depende de novas observações.',
    'O prazo termina em 15 de outubro, salvo prorrogação formal.',
])
def test_short_summary_preserves_negation_conditions_and_dates(text):
    from cain.agents import SummaryAgent
    from cain.common import Message
    class Forbidden:
        def generate(self, *args):
            raise AssertionError('Short explicit source must remain literal')
    result = SummaryAgent(Forbidden()).handle(Message('resumo', '', 'Resuma: '+text))
    assert result.endswith(text)
    assert 'preservado literalmente' in result


class QuoteModel:
    def __init__(self, quote):
        self.quote = quote
        self.calls = 0

    def generate_json(self, prompt, instruction, schema):
        self.calls += 1
        data = json.loads(prompt)
        assert len(prompt.encode()) < 6000
        row = next(e for e in data['evidence'] if self.quote in e['text'])
        return json.dumps({'claims': [{'evidence_id': row['reference_id'], 'quote': self.quote}],
                           'synthesis': ''})


@pytest.mark.parametrize('identity', ['K71', 'Ω-53', 'Z/8'])
def test_general_historian_selects_relevant_fields_from_large_source(setup, identity):
    service, scope, ingest, _, _ = setup
    text = json.dumps({'irrelevant': {f'x{i}': 'padding ' * 40 for i in range(50)},
                       identity: {'reason': 'No effect established; conditional on new evidence.'}}, ensure_ascii=False)
    ingest(cases.publication((identity,), text=text))
    quote = 'No effect established; conditional on new evidence.'
    model = QuoteModel(quote)
    result = explain(service, scope, f'Explique a justificativa documentada de {identity}.', model, source_id=identity)
    assert result['status'] == 'generated'
    assert result['explanation']['source_quotes'][0]['quote'] == quote
    assert model.calls == 1
    assert result['coverage']['selected_excerpts'] >= 1


def test_general_historian_rechecks_policy_after_resolving_quotes(setup, monkeypatch):
    service, scope, ingest, policy, path = setup
    ingest(cases.publication(('K71',), text='K71 has not been approved.'))
    original = service.evidence
    def revoke(*args, **kwargs):
        result = original(*args, **kwargs)
        policy['grants'] = []
        path.write_text(json.dumps(policy))
        return result
    monkeypatch.setattr(service, 'evidence', revoke)
    result = explain(service, scope, 'Explique K71.', QuoteModel('K71 has not been approved.'), source_id='K71')
    assert result['status'] == 'generation_failed'
    assert result['explanation'] is None
    assert result['facts']['records'] == []


def test_oversized_indivisible_evidence_abstains_without_inference(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('K71',), text='K71 ' + 'unsplittable ' * 1000))
    model = QuoteModel('K71')
    result = explain(service, scope, 'Explique K71.', model, source_id='K71')
    assert result['status'] == 'abstained_insufficient_evidence_budget'
    assert result['generation']['called'] is False and model.calls == 0


def test_unselected_quote_from_same_large_source_is_rejected(setup):
    service, scope, ingest, _, _ = setup
    text = json.dumps({'irrelevant': 'SECRET-TEST ' * 1000, 'K71': {'reason': 'not approved'}})
    ingest(cases.publication(('K71',), text=text))
    class OutsideQuote:
        def generate_json(self, prompt, instruction, schema):
            ref = json.loads(prompt)['evidence'][0]['reference_id']
            return json.dumps({'claims': [{'evidence_id': ref, 'quote': 'SECRET-TEST'}], 'synthesis': ''})
    result = explain(service, scope, 'Explique K71.', OutsideQuote(), source_id='K71')
    assert result['status'] == 'generation_failed'
    assert result['error_code'] == 'UNSUPPORTED_QUOTE'
