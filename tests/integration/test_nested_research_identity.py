"""Nested hypothesis records retain their own identities and literal context."""
from cain.research.grounding import cards, structured, matches_identity


def test_nested_hypothesis_fields_keep_identity_without_sibling_leakage():
    text = '{"families":[{"hypothesis":"Z1","status":"WAIT","metric":7},{"hypothesis":"Z2","status":"CLOSED","metric":9}]}'
    result = structured({'r': text}, addressable=True)
    metrics = [r for r in result['relations'] if r['decoded_subject'] == 'metric']
    assert len(metrics) == 2
    for row, identity, status in zip(metrics, ['Z1', 'Z2'], ['WAIT', 'CLOSED']):
        assert matches_identity(row, identity)
        assert not matches_identity(row, 'Z2' if identity == 'Z1' else 'Z1')
        assert [p['decoded_object'] for p in row['record_context'] if p['decoded_subject'] == 'status'] == [status]
        assert all(text[p['start']:p['end']] == p['quote'] for p in row['record_context'])


def test_nested_explicit_hypothesis_id_keeps_mechanism():
    text = '{"candidate":{"hypothesis_id":"Z22","mechanism":"A fixed rule"},"other":{"hypothesis_id":"Z23","mechanism":"Another rule"}}'
    selected, _ = cards({'r': {'text': text}}, 'Z22 mechanism', 'Z22')
    assert any('A fixed rule' in e['quote'] for e in selected.values())
    assert all('Another rule' not in e['quote'] for e in selected.values())


def test_child_identity_does_not_inherit_different_parent_identity():
    text = '{"family":"Z91","candidate":{"hypothesis_id":"Z22","metric":7}}'
    result = structured({'r': text}, addressable=True)
    metric = next(r for r in result['relations'] if r['decoded_subject'] == 'metric')
    assert matches_identity(metric, 'Z22')
    assert not matches_identity(metric, 'Z91')


def test_report_number_does_not_hide_explicit_subject_in_heading():
    text = '# R5 â€” result of Z22\n\nThe fixed rule was rejected because the registered threshold was not met.'
    selected, coverage = cards({'r': {'text': text}}, 'What result and reason for Z22?')
    assert any('registered threshold' in e['quote'] for e in selected.values())
    assert not any(d['decision'] == 'different_section_identity' for d in coverage['decisions'])


def test_dated_document_path_is_not_an_invented_hypothesis_identity():
    source = 'docs/2026-09-15-z22-protocol.json'
    evidence = {'r': {'source': source, 'text': '{"success_criteria":"All cases pass","result_status":"REJECTED"}'}}
    selected, coverage = cards(evidence, f'No documento {source}, quais success_criteria e result_status?')
    assert coverage['question_identifiers'] == []
    assert {e['json_pointer'] for e in selected.values()} == {'/success_criteria', '/result_status'}


def test_different_hypothesis_heading_still_excludes_body_mentions():
    text = '## Z91\n\nZ22 is mentioned but this is the result of Z91.\n\n## Z22\n\nNo result yet.'
    selected, _ = cards({'r': {'text': text}}, 'What result for Z22?')
    assert all('result of Z91' not in e['quote'] for e in selected.values())


def test_requested_rule_outranks_short_incidental_metadata():
    text = '{"candidate":{"hypothesis_id":"Z22","ticker":"XYZ","currency":"BRL","mechanism":"A fixed rule with a prespecified signal and no tuning"}}'
    selected, _ = cards({'r': {'text': text}}, 'Qual regra da hipÃ³tese Z22?', max_cards=1)
    assert next(iter(selected.values()))['json_pointer'] == '/candidate/mechanism'


def test_dated_source_does_not_displace_requested_fields_across_revisions():
    import json
    from cain.research.field_review import native_field_reply

    source = 'docs/2026-09-07-z17-observations.jsonl'
    evidence = {str(revision): {'source': source, 'text': json.dumps({
        'family': 'Z17', 'observation_revision': revision,
        'observed_at_utc': '2026-09-07T05:33:31+00:00',
        'status': 'INCONCLUSIVE_DATA_QUALITY', 'canonical_proof_verdict': None,
        'irrelevant_metric': 12,
    })} for revision in (1, 2)}
    question = (f'No documento {source}, mostre observation_revision, status e '
                'canonical_proof_verdict, preservando as revisoes.')
    selected, _ = cards(evidence, question)
    reply = native_field_reply(selected, question, None)
    fields = {f['field']: f for f in reply['fields']}
    assert {v['value'] for v in fields['observation_revision']['values']} == {1, 2}
    assert len(fields['canonical_proof_verdict']['values']) == 2
    assert all(v['value'] is None for v in fields['canonical_proof_verdict']['values'])
    assert len(fields['status']['values']) == 2
