import json
from pathlib import Path

import pytest

from cain.research.analysis import entities, review
from cain.research.grounding import cards, structured
from cain.llm import FakeLLM
import test_research_l0 as cases

setup = cases.setup
PLAN = json.loads((Path(__file__).parents[2] / "evaluation/grounded-analysis-20260911.json").read_bytes())


@pytest.mark.parametrize("case", PLAN["cases"][:4], ids=lambda case: case["id"])
def test_frozen_structured_cases(case):
    result = structured({"ref": case["text"]}, case["source_id"])
    if "expected_pairs" in case:
        assert [[r["subject"], r["object"]] for r in result["relations"]] == case["expected_pairs"]
        for relation in result["relations"]:
            assert case["text"][relation["start"]:relation["end"]] == relation["quote"]
    else:
        assert result["status"] == case["expected_structural_status"]
        assert result["relations"] == []


def test_escaped_json_uses_received_lexemes_not_invented_quotes():
    text = json.dumps({"Á": "linha\nseguinte"}, ensure_ascii=True)
    row = structured({"ref": text}, "Á")["relations"][0]
    assert row["decoded_subject"] == "Á" and row["decoded_object"] == "linha\nseguinte"
    assert row["subject"] in row["quote"] and row["object"] in row["quote"]
    assert row["quote"] == text[row["start"]:row["end"]]


def test_literal_extraction_works_without_model_or_generation_permission(setup):
    service, scope, ingest, policy, path = setup
    ingest(cases.publication(("K17",), text='{"states":{"K17":"INSUFFICIENT_DATA"}}'))
    for grant in policy["grants"]:
        grant["generate"] = False
    path.write_text(json.dumps(policy))
    result = entities(service, scope, "What is reported?", FakeLLM(), source_id="K17")
    assert result["model_calls"] == 0 and result["status"] == "literal"
    assert result["relations"][0]["object"] == "INSUFFICIENT_DATA"


class PointerModel:
    base_url = "http://127.0.0.1:11434"
    calls = 0
    def generate_json(self, prompt, context, schema):
        self.calls += 1
        return json.dumps({"citations": [next(iter(json.loads(prompt)["excerpts"]))],
                           "analysis": "The report does not establish a cause."})


def test_review_resolves_offsets_and_no_evidence_has_zero_calls(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(("D4",), text=PLAN["cases"][4]["text"]))
    model = PointerModel()
    result = review(service, scope, "What reason?", model, role="challenge", source_id="D4")
    quote = result["explanation"]["source_quotes"][0]
    assert result["status"] == "generated"
    assert quote["support"]["text"][quote["start"]:quote["end"]] == quote["quote"]
    result = review(service, scope, "What reason?", model, role="support", source_id="missing")
    assert not result["generation"]["called"] and model.calls == 1


def test_unknown_pointer_is_rejected(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(("D4",), text=PLAN["cases"][4]["text"]))
    model = PointerModel()
    model.generate_json = lambda *args: '{"citations":["invented"],"analysis":"x"}'
    result = review(service, scope, "What reason?", model, role="support", source_id="D4")
    assert result["status"] == "generation_failed" and result["explanation"] is None


def test_individual_hypothesis_excerpts_exclude_other_identities_and_keep_paths():
    text = json.dumps({'hypotheses': {'H1': 'CLOSED_NO_GO', 'H6': 'INSUFFICIENT', 'H60': 'ACTIVE'},
                       'hypothesis_trials': {'H1': 'other', 'H6': 'trial-six'},
                       'notes': 'H1 has an unrelated historical explanation.'})
    excerpts, coverage = cards({'ref': {'text': text}}, 'O que a fonte informa sobre H6?', 'H6')
    assert {e['json_pointer'] for e in excerpts.values()} == {'/hypotheses/H6', '/hypothesis_trials/H6'}
    assert len(excerpts) == 2
    for entry in excerpts.values():
        assert entry['quote'] == text[entry['start']:entry['end']]
        assert 'H1' not in entry['quote'] and 'H60' not in entry['quote']
    assert coverage['whole_source_read_claim'] is False


def test_duplicate_json_cannot_bypass_structured_ambiguity_via_review(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('K17',), text='{"K17":"INSUFFICIENT","K17":"VALIDATED"}'))
    model = PointerModel()
    result = review(service, scope, 'What status?', model, role='synthesis', source_id='K17')
    assert result['status'] == 'abstained_ambiguous_evidence'
    assert result['coverage']['structured_issues'][0]['status'] == 'ambiguous_or_invalid_json'
    assert model.calls == 0


def test_review_payload_retains_exact_key_paths(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('H6',), text='{"hypotheses":{"H1":"NO","H6":"WAIT"},"trials":{"H6":"six"}}'))
    model = PointerModel()
    def capture(prompt, context, schema):
        payload = json.loads(prompt)
        assert payload['source_id'] == 'H6'
        assert payload['reported_records_untrusted'][0]['source_id'] == 'H6'
        assert {e['json_pointer'] for e in payload['excerpts'].values()} == {'/hypotheses/H6', '/trials/H6'}
        assert all('H1' not in e['text'] for e in payload['excerpts'].values())
        return json.dumps({'citations': ['S1'], 'analysis': 'WAIT'})
    model.generate_json = capture
    result = review(service, scope, 'What status?', model, role='synthesis', source_id='H6')
    assert result['status'] == 'generated'
    assert result['generation']['prompt_version'] == 'addressable-review/14'


def test_multicolumn_claim_row_is_literal_without_invented_column_meanings(setup):
    service, scope, ingest, _, _ = setup
    text = '| CLAIM-BR-001 | Incremental information | BLOCKED | No comparison executed |\n'
    ingest(cases.publication(('CLAIM-BR-001',), text=text))
    result = entities(service, scope, 'What does this report say?', FakeLLM(), source_id='CLAIM-BR-001')
    assert result['model_calls'] == 0 and result['status'] == 'literal'
    assert [(r['predicate'], r['object']) for r in result['relations']] == [
        ('reported_table_column_2', 'Incremental information'),
        ('reported_table_column_3', 'BLOCKED'),
        ('reported_table_column_4', 'No comparison executed')]
    excerpts, _ = cards({'ref': {'text': text}}, 'What is reported?', 'CLAIM-BR-001')
    assert len(excerpts) == 1
    assert excerpts['S1']['quote'] == text[:-1]


def test_review_passes_scientific_clocks_and_slice_boundaries(setup):
    service, scope, ingest, _, _ = setup
    text = 'Q-73: no experiment run; no conclusion on precision.'
    ingest(cases.publication(('Q-73',), revision='historical-3', text=text))
    model = PointerModel()
    def capture(prompt, instruction, schema):
        payload = json.loads(prompt)
        record = payload['reported_records_untrusted'][0]
        assert record['revision'] == 'historical-3'
        assert all(record[k] is None for k in ('event_at', 'recorded_at', 'available_at'))
        assert 'evidence_scope' not in payload
        excerpt = payload['excerpts']['S1']
        assert excerpt['text'] == text
        assert excerpt['source'] == 'report.md'
        assert 'table_column_labels' not in excerpt
        assert 'blocked or unexecuted comparison' in instruction
        assert 'exclusive explanation' in instruction
        return json.dumps({'citations': ['S1'], 'analysis': 'No experiment is reported.'})
    model.generate_json = capture
    result = review(service, scope, 'What can the report conclude?', model, role='support', source_id='Q-73')
    assert result['status'] == 'generated'
    assert result['explanation']['semantic_support'] == 'not_certified'
    assert result['evidence_scope']['current_source_verified'] is False


@pytest.mark.parametrize('role', ['support', 'challenge', 'synthesis'])
@pytest.mark.parametrize('text', [
    '| Q-73 | Candidate improves precision | WAITING | No experiment run |',
    '| Operational readiness | Unknown: costs and observations incomplete |',
])
def test_unlabelled_rows_abstain_without_free_generation(setup, role, text):
    service, scope, ingest, _, _ = setup
    identity = text.split('|')[1].strip()
    ingest(cases.publication((identity,), text=text))
    model = PointerModel()
    result = review(service, scope, 'What can be concluded?', model, role=role, source_id=identity)
    assert result['status'] == 'abstained_unlabelled_table'
    assert model.calls == 0 and result['model_calls'] == 0
    assert result['facts']['records'][0]['source_id'] == identity
    explanation = result['explanation']
    assert explanation['answer_mode'] == 'source_excerpts'
    assert explanation['semantic_support'] == 'not_certified'
    assert explanation['verification']['interpretation_verified'] is False
    assert explanation['source_quotes'][0]['quote'] == text


def test_workflow_keeps_abstention_visible_and_does_not_mix_protocols(setup):
    from cain.research.workflows import Workflows
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('Q-73',), text='| Q-73 | Untested claim | WAIT |'))
    workflow = Workflows(service)
    model = PointerModel()
    job = workflow.create(scope, 'What is supported?', model, source_id='Q-73',
                          steps=['support', 'challenge', 'synthesis'])
    for _ in range(3):
        job = workflow.advance(scope, job['id'], model, approve_generation=True)
    assert job['status'] == 'completed' and job['model_calls'] == 0
    assert all(s['result']['status'] == 'abstained_unlabelled_table' for s in job['steps'])
    old = workflow.create(scope, 'What is supported?', model, source_id='Q-73', steps=['support'])
    with service.connection() as db:
        request = {**old['request'], 'protocol': 'research-workflow/8'}
        db.execute('UPDATE agent_jobs SET request=? WHERE scope=? AND id=?',
                   (json.dumps(request), scope, old['id']))
    with pytest.raises(ValueError, match='protocol changed'):
        workflow.advance(scope, old['id'], model, approve_generation=True)
    assert workflow.get(scope, old['id'])['request']['protocol'] == 'research-workflow/8'


def test_review_budgets_provenance_and_keeps_whole_excerpts(setup):
    service, scope, ingest, _, _ = setup
    for i in range(8):
        identity = f'case-{i}-' + 'x' * 160
        text = json.dumps({'status': f'Case {i}: hypothesis remains unexecuted.'})
        ingest(cases.publication((identity,), revision='r' * 200, text=text))
    model = PointerModel()
    captured = []
    def capture(prompt, instruction, schema):
        captured.append(json.loads(prompt))
        assert len((prompt + instruction).encode()) <= 5000
        assert set(schema['properties']['citations']['items']['enum']) == set(captured[-1]['excerpts'])
        return json.dumps({'citations': [next(iter(captured[-1]['excerpts']))],
                           'analysis': 'Unexecuted as reported.'})
    model.generate_json = capture
    result = review(service, scope, 'What status?', model, role='synthesis')
    assert result['status'] == 'generated'
    assert result['coverage']['context_budget_omissions']
    assert result['coverage']['serialized_context_bytes'] <= 5000
    for entry in captured[0]['excerpts'].values():
        assert entry['text'].endswith('unexecuted."')


def test_question_identifier_outranks_unrelated_structured_notes():
    evidence = {'a': {'text': json.dumps({'notes': 'report conclusion limitations cause for Z92'})},
                'b': {'text': 'Z17 has not been executed; no measured improvement.'}}
    selected, coverage = cards(evidence, 'What report conclusion and limitations for Z17?', max_cards=1)
    assert selected['S1']['reference'] == 'b'
    assert coverage['question_identifiers'] == ['Z17']


def test_table_header_is_literal_and_does_not_cross_another_table():
    text = ('| Claim | State |\n|---|---|\n| Z17 | NOT_RUN |\n\n'
            '| Z18 | Ambiguous row |')
    selected, _ = cards({'ref': {'text': text}}, 'What state for Z17?', 'Z17')
    assert selected['S1']['quote'] == '| Z17 | NOT_RUN |'
    assert selected['S1']['source_context'][0]['quote'] == '| Claim | State |\n|---|---|'
    assert text[selected['S1']['start']:selected['S1']['end']] == selected['S1']['quote']
    selected, _ = cards({'ref': {'text': text}}, 'What state for Z18?', 'Z18')
    assert selected['S1']['quote'] == '| Z18 | Ambiguous row |'


def test_mixed_markdown_does_not_hide_relevant_prose_behind_table():
    text = '| X | State |\n|---|---|\n| Z92 | CLOSED |\n\nZ17 is not executed. No effect measured.'
    selected, _ = cards({'ref': {'text': text}}, 'What can Z17 establish?', max_cards=1)
    assert selected['S1']['quote'] == 'Z17 is not executed. No effect measured.'


def test_question_phrase_beats_unrelated_historical_state_label():
    old = '- Estado de dados real: zero linhas em um recorte histórico.'
    current = '| Uso | Limite |\n|---|---|\n| Operação real | Não apta; custos insuficientes |'
    selected, _ = cards({'old': {'text': old}, 'current': {'text': current}},
                         'O que o relatório permite concluir sobre operação real?', max_cards=1)
    assert selected['S1']['reference'] == 'current'
    assert selected['S1']['quote'] == current.splitlines()[-1]


def test_multiple_unlabelled_rows_do_not_enable_generation(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('X',), text='| X | Unknown |\n| Y | NOT_RUN |'))
    model = PointerModel()
    result = review(service, scope, 'What does X establish?', model, role='support')
    assert result['status'] == 'abstained_unlabelled_table'
    assert model.calls == 0


def test_row_context_excludes_other_subjects_and_resolves_labels(setup):
    service, scope, ingest, _, _ = setup
    text = ('# Historical register 2024-02-03\n\n| ID | State |\n|---|---|\n'
            '| Z91 | Cause missing |\n| Z17 | NOT_RUN |')
    ingest(cases.publication(('register',), text=text))
    model = PointerModel()
    def capture(prompt, instruction, schema):
        payload = json.loads(prompt)
        assert 'Z91' not in prompt and 'Cause missing' not in prompt
        assert 'omitted_excerpts' not in prompt and 'candidate_search_partial' not in prompt
        entry = payload['excerpts']['S1']
        assert entry['text'] == '| Z17 | NOT_RUN |'
        assert any(p['kind'] == 'table_header' and 'State' in p['text'] for p in entry['source_context'])
        assert any('2024-02-03' in p['text'] for p in entry['source_context'])
        assert 'maxLength' not in schema['properties']['analysis']
        return json.dumps({'citations': ['S1'], 'analysis': 'As recorded in 2024, Z17 was not run.'})
    model.generate_json = capture
    result = review(service, scope, 'What is reported about Z17?', model, role='support')
    assert result['status'] == 'generated'
    quotes = result['explanation']['source_quotes']
    assert quotes[0]['excerpt_id'] == 'S1'
    assert any(q.get('context_kind') == 'table_header' for q in quotes)
    assert all(text[q['start']:q['end']] == q['quote'] for q in quotes)


def test_other_hypothesis_section_does_not_override_question_subject():
    text = ('## Z17\n\nZ17: interrupted, no conclusion.\n\n'
            '## Z91\n\nZ17 is mentioned for comparison; cause failed, significant negative result.')
    selected, coverage = cards({'r': {'text': text}}, 'What conclusion for Z17?')
    assert all('significant negative' not in e['quote'] for e in selected.values())
    assert any(d['decision'] == 'different_section_identity' for d in coverage['decisions'])


@pytest.mark.parametrize('heading', ['#', '##', '###'])
def test_document_preamble_qualifies_later_top_level_historical_heading(heading):
    preamble = (heading + ' Historical document\n\n'
                'Z17 was later observed; the instructions below describe an earlier date.\n\n')
    text = preamble + heading + ' Original runbook\n\nZ17 has never run.\n# Older root\n\nLegacy appendix.'
    selected, _ = cards({'r': {'text': text}}, 'Has Z17 run?')
    old = [entry for entry in selected.values() if entry['quote'] == 'Z17 has never run.']
    assert old
    assert any('later observed' in part['quote'] for part in old[0].get('source_context', []))
    assert all(text[p['start']:p['end']] == p['quote'] for p in old[0]['source_context'])


def test_leading_sibling_hypothesis_is_not_another_hypothesis_preamble():
    text = '## Z91\n\nZ91 failed.\n\n## Z17\n\nZ17 not run.'
    selected, _ = cards({'r': {'text': text}}, 'What is reported about Z17?')
    assert selected
    assert all('Z91' not in p['quote'] for e in selected.values()
               for p in e.get('source_context', []))


def test_specific_question_does_not_fill_budget_with_one_generic_word():
    evidence = {'current': {'text': 'Real operation remains unavailable; limitations persist.'},
                'old': {'text': 'A real diagnostic remains in the earlier study.'}}
    selected, coverage = cards(evidence, 'What remains reported about real operation and limitations?')
    assert selected and all(e['reference'] == 'current' for e in selected.values())
    assert any(d['decision'] == 'weak_query_overlap' for d in coverage['decisions'])


def test_explicit_document_path_keeps_revisions_and_excludes_other_sources():
    evidence = {'old': {'text': '{"revision":1,"exit_code":2}', 'source': 'reports/decision.json'},
                'new': {'text': '{"revision":2,"exit_code":2}', 'source': 'reports/decision.json'},
                'other': {'text': '{"exit_code":0}', 'source': 'other/decision.json'}}
    selected, coverage = cards(evidence, 'In reports/decision.json what is exit_code?')
    assert {e['reference'] for e in selected.values()} == {'old', 'new'}
    assert any(d['decision'] == 'explicit_source_mismatch' for d in coverage['decisions'])


@pytest.mark.parametrize('values', ['[2, 2]', '[]', '[null, false, "UNKNOWN"]'])
def test_flat_json_array_remains_a_literal_named_value(values):
    text = '{"exit_codes": ' + values + ', "full_history_executed": false}'
    selected, _ = cards({'r': {'text': text}}, 'What are exit_codes?')
    arrays = [e for e in selected.values() if e.get('json_pointer') == '/exit_codes']
    assert len(arrays) == 1
    assert arrays[0]['quote'] == '"exit_codes": ' + values
    assert text[arrays[0]['start']:arrays[0]['end']] == arrays[0]['quote']


def test_document_preamble_is_not_silently_dropped_when_over_budget():
    text = '# Scope\n\n' + ('Temporal qualification. ' * 130) + '\n\n# Old\n\nZ17 has never run.'
    selected, coverage = cards({'r': {'text': text}}, 'Has Z17 run?')
    assert all(entry['quote'] != 'Z17 has never run.' for entry in selected.values())
    assert any(row['decision'] == 'byte_budget' for row in coverage['decisions'])


def test_json_observation_fields_keep_root_identity_and_revision():
    text = '{"family":"Z17","observation_revision":2,"observed_at_utc":"2024-02-03T12:00:00Z","summary":{"complete_months":59}}'
    selected, _ = cards({'r': {'text': text}}, 'Z17 complete_months', 'Z17')
    metric = [e for e in selected.values() if '"complete_months":59' == e['quote']]
    assert metric
    context = metric[0]['source_context']
    assert any('"family":"Z17"' == c['quote'] for c in context)
    assert any('"observation_revision":2' == c['quote'] for c in context)
    assert all(text[c['start']:c['end']] == c['quote'] for c in context)


def test_json_root_identity_does_not_leak_another_record():
    text = '{"family":"Z91","status":"NOT_RUN"}'
    selected, _ = cards({'r': {'text': text}}, 'Z17 status', 'Z17')
    assert selected == {}


def test_section_owner_survives_contiguous_chunks_but_not_another_publication():
    first = '## Z91\n\n'
    second = 'Z17 mentioned inside a different hypothesis, not its own result.'
    def part(text, start):
        return dict(text=text, start=start, end=start+len(text), source='hypotheses.md',
                    offset_unit='unicode_codepoints')
    evidence = {'pub:a': part(first, 0), 'pub:b': part(second, len(first)),
                'other:c': {'text': '## Z17\n\nZ17 not run.'}}
    selected, coverage = cards(evidence, 'What is reported about Z17?')
    assert all(e['reference'] != 'pub:b' for e in selected.values())
    assert any(d['decision'] == 'different_section_identity' for d in coverage['decisions'])
    from cain.research.grounding import document_contexts
    evidence['other:b'] = evidence.pop('pub:b')
    assert document_contexts(evidence)['other:b'][1] == 0


def test_explicit_table_subject_wins_over_group_heading_and_header_can_be_in_previous_part():
    first = '## Z10-Z20 overview\n\n| ID | State |\n|---|---|\n| Z11 | OTHER |\n'
    second = '| Z17 | NOT_RUN |'
    evidence = {'pub:a': dict(text=first, start=0, end=len(first), source='r.md', offset_unit='unicode_codepoints'),
                'pub:b': dict(text=second, start=len(first), end=len(first+second), source='r.md', offset_unit='unicode_codepoints')}
    selected, _ = cards(evidence, 'What is reported about Z17?')
    entry = selected['S1']
    assert entry['quote'] == second
    header = next(p for p in entry['source_context'] if p['kind'] == 'table_header')
    assert header['reference'] == 'pub:a'
    assert first[header['start']:header['end']] == '| ID | State |\n|---|---|'
    assert all('OTHER' not in p['quote'] for p in entry['source_context'])


@pytest.mark.parametrize('fence', ['```python', '~~~python', '   ````python'])
def test_code_comment_is_not_a_hypothesis_heading(fence):
    closing = fence.strip().split('python')[0]
    text = ('## Z17\n\n' + fence + '\n# Z91 example, not a section\nvalue = 1\n'
            + closing + '\n\nZ17 collection stopped; no statistical verdict.')
    selected, _ = cards({'r': {'text': text}}, 'What conclusion for Z17?')
    assert any(e['quote'] == 'Z17 collection stopped; no statistical verdict.'
               for e in selected.values())
    assert not any('Z91' in p['quote'] for e in selected.values()
                   for p in e.get('source_context', []))


def test_previous_proposal_is_whole_or_explicitly_omitted(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('Z17',), text='Z17 remains unconfirmed.'))
    prior = 'This preliminary observation is provisional. ' * 6 + 'It does NOT confirm Z17.'
    model = PointerModel()
    captured = []
    def capture(prompt, instruction, schema):
        payload = json.loads(prompt)
        captured.append(payload)
        assert payload['prior_proposals_untrusted'] in ([prior], [])
        return json.dumps({'citations': ['S1'], 'analysis': 'Z17 remains unconfirmed.'})
    model.generate_json = capture
    result = review(service, scope, 'What does Z17 establish?', model,
                    role='synthesis', previous=[prior])
    assert result['status'] == 'generated'
    assert captured


def test_context_budget_discards_prior_proposals_before_source_evidence(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('Z17',), text='Z17 remains unconfirmed.'))
    model = PointerModel()
    captured = []
    def capture(prompt, instruction, schema):
        payload = json.loads(prompt)
        captured.append(payload)
        assert payload['prior_proposals_untrusted'] == []
        assert 'Z17 remains unconfirmed.' in prompt
        return json.dumps({'citations': ['S1'], 'analysis': 'Z17 remains unconfirmed.'})
    model.generate_json = capture
    result = review(service, scope, 'What does Z17 establish?', model,
                    role='synthesis', previous=['Provisional. ' * 900])
    assert result['status'] == 'generated'
    assert result['coverage']['prior_proposals_omitted'] == 1
    assert captured


def test_oversized_review_is_rejected_instead_of_accepted_as_a_grammar_cut_fragment(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(('Z17',), text='Z17 remains unconfirmed.'))
    model = PointerModel()
    full_answer = 'A reported observation is not a confirmed hypothesis. ' * 22
    assert len(full_answer) > 1000
    def grammar_capped_provider(prompt, instruction, schema):
        cap = schema['properties']['analysis'].get('maxLength')
        answer = full_answer[:cap] if cap is not None else full_answer
        return json.dumps({'citations': ['S1'], 'analysis': answer})
    model.generate_json = grammar_capped_provider
    result = review(service, scope, 'What does Z17 establish?', model, role='synthesis')
    assert result['status'] == 'generation_failed'
    assert result['error_code'] == 'INVALID_REVIEW_OUTPUT'
    assert result['explanation'] is None
    assert result['facts']['records']
