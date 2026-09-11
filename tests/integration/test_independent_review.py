"""Independent regressions for the individual-model delivery, not model quality scores."""

import json

import pytest

from cain.research.grounding import cards, structured
from cain.research.workflows import Workflows
from cain.research.analysis import review
import test_research_l0 as cases
from test_grounded_analysis import PointerModel

setup = cases.setup


@pytest.mark.parametrize('ending', ['\n', '\r\n', '\r'])
def test_table_line_endings_preserve_literal_offsets(ending):
    text = 'Introdução Ω' + ending + '| H1 | NO | other |' + ending + '| H6 | WAIT | motivo 🧪 |' + ending
    result = structured({'ref': text}, 'H6')
    assert [r['object'] for r in result['relations']] == ['WAIT', 'motivo 🧪']
    excerpts, _ = cards({'ref': {'text': text}}, 'H6?', 'H6')
    assert len(excerpts) == 1
    for row in [*result['relations'], *excerpts.values()]:
        assert row['quote'] == text[row['start']:row['end']]
        assert 'H1' not in row['quote']


def test_object_identity_is_focused_by_exact_json_path():
    text = json.dumps({'H1': {'status': 'NO'}, 'H6': {'status': 'WAIT', 'trial': 'six'},
                       'H60': {'status': 'ACTIVE'}})
    result = structured({'ref': text}, 'H6')
    assert {r['json_pointer'] for r in result['relations']} == {'/H6/status', '/H6/trial'}
    excerpts, _ = cards({'ref': {'text': text}}, 'H6?', 'H6')
    assert {r['json_pointer'] for r in excerpts.values()} == {'/H6/status', '/H6/trial'}


@pytest.mark.parametrize('text', ['{"H1":"NO","H60":"ACTIVE"}', '| H1 | NO | other |\n'])
def test_missing_identity_does_not_fall_back_to_other_identities(text):
    assert not structured({'ref': text}, 'H6')['relations']
    excerpts, coverage = cards({'ref': {'text': text}}, 'H6?', 'H6')
    assert not excerpts and coverage['structured_issues']


def test_table_inline_code_without_pipe_is_literal_and_header_is_not_data():
    text = '| identity | state | reason |\n| --- | --- | --- |\n| H6 | `WAIT` | pending |\n'
    result = structured({'ref': text})
    assert [r['object'] for r in result['relations']] == ['`WAIT`', 'pending']


def test_ambiguous_pipe_does_not_fall_back_to_other_rows():
    text = '| H1 | NO | other |\n| H6 | WAIT | reason with \\| pipe |\n'
    assert not structured({'ref': text}, 'H6')['relations']
    excerpts, coverage = cards({'ref': {'text': text}}, 'H6?', 'H6')
    assert not excerpts and coverage['structured_issues']


def test_escaped_identity_path_is_not_substring_match():
    text = '{"H/6":{"state":"WAIT"},"H/60":{"state":"ACTIVE"}}'
    result = structured({'ref': text}, 'H/6')
    assert [r['json_pointer'] for r in result['relations']] == ['/H~16/state']


@pytest.mark.parametrize('ending', ['\n', '\r\n', '\r\r\n'])
def test_continuation_keeps_negation_with_claim(ending):
    text = ending.join(['## DPL', '', '- decision: nenhum segundo',
                        '  consumidor real foi confirmado fora do repositório.', '',
                        '- state: não é', '  REFUTED nem VALIDATED.'])
    excerpts, _ = cards({'ref': {'text': text}}, 'consumidor real confirmado REFUTED?', 'DPL')
    quotes = [e['quote'] for e in excerpts.values()]
    assert any('nenhum segundo' in q and 'consumidor real' in q for q in quotes)
    assert all('nenhum segundo' in q for q in quotes if 'consumidor real' in q)
    assert all('não é' in q for q in quotes if 'REFUTED' in q)
    for row in excerpts.values():
        assert text[row['start']:row['end']] == row['quote']


def test_shared_markdown_heading_focus_excludes_other_sections():
    text = '## H1\n\nH1 is CLOSED.\n\n## H6\n\nH6 is WAITING.\n\n## H60\n\nH60 is ACTIVE.'
    excerpts, _ = cards({'ref': {'text': text}}, 'What is H6?', 'H6')
    assert excerpts
    assert all('H1' not in e['quote'] and 'H60' not in e['quote'] for e in excerpts.values())


@pytest.mark.parametrize('old_protocol', ['research-workflow/4', 'research-workflow/5'])
def test_old_workflow_remains_readable_cancellable_and_completed_is_idempotent(setup, monkeypatch, old_protocol):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('A',), text='A reports a limitation.'))
    jobs, model = Workflows(service), PointerModel()
    monkeypatch.setattr('cain.research.workflows.PROTOCOL', old_protocol)
    old = jobs.create(scope, 'A?', model, source_id='A', steps=['inspect'])
    done = jobs.create(scope, 'A?', model, source_id='A', steps=['inspect'])
    jobs.advance(scope, done['id'], model)
    monkeypatch.setattr('cain.research.workflows.PROTOCOL', 'research-workflow/6')
    with pytest.raises(ValueError, match='protocol changed'):
        jobs.advance(scope, old['id'], model)
    assert jobs.get(scope, old['id'])['steps'] == []
    assert jobs.cancel(scope, old['id'])['status'] == 'cancelled'
    assert jobs.advance(scope, done['id'], model)['status'] == 'completed'
    assert model.calls == 0


def test_omitted_oversize_block_is_not_reported_as_absent_source(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('A',), text='no evidence of benefit ' * 150))
    model = PointerModel()
    result = review(service, scope, 'What does A report?', model, role='support', source_id='A')
    assert result['status'] == 'abstained_context_budget' and model.calls == 0
    assert result['facts']['records'] and result['coverage']['omitted_excerpts'] == 1
