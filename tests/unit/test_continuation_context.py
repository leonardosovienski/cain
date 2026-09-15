import json

from cain.common import Signal
from cain.runtime import build_cain
from cain.research.grounding import cards


def episode(runtime, text, response='Entendido.', *, user='qa', project=None, session='s'):
    metadata={'session_id':session,'project_id':project,'decision_id':text}
    runtime.identity.observe(user,text,metadata)
    runtime.identity.update(user,Signal(f'Usuário: {text}\nCain: {response}',
        metadata={**metadata,'user_input':text,'preference_observed':True}))


def test_relevant_old_declaration_survives_recent_distractors(tmp_path):
    with build_cain(tmp_path/'qa.db') as runtime:
        episode(runtime,'O identificador do experimento é PONTE-916.')
        for word in ['vidro','papel','cedro','metal','nuvem']:
            episode(runtime,'Responda apenas: '+word)
        context=runtime.identity.context_for('qa','Qual é o identificador do experimento?',session_id='s')
        assert 'PONTE-916' in context
        for document in runtime.store.iter_documents():
            assert document.doc_id not in context


def test_chronology_and_speaker_are_not_flattened(tmp_path):
    with build_cain(tmp_path/'qa.db') as runtime:
        episode(runtime,'O estoque do armazém Cedro começa em 12 caixas.')
        episode(runtime,'Atualização do armazém Cedro: agora são 19 caixas.','O estoque inicial é 19.')
        episode(runtime,'Nova atualização do armazém Cedro: agora são 27 caixas.')
        episode(runtime,'O depósito Ipê tem 88 caixas.')
        context=runtime.identity.context_for('qa','Qual era o estoque inicial e qual é o atual do armazém Cedro?',session_id='s')
        assert all(t in context for t in ['12 caixas','19 caixas','27 caixas'])
        assert context.index('12 caixas') < context.index('19 caixas') < context.index('27 caixas')
        # A model's mistaken answer must not be indistinguishable from a user assertion.
        assert '"user"' in context and '"assistant"' not in context
        assert 'O estoque inicial é 19.' not in context
        editing=runtime.identity.context_for('qa','Revise a resposta sobre o armazém Cedro.',session_id='s')
        assert '"assistant"' in editing


def test_memory_scope_and_rebuild_preserve_relevance(tmp_path):
    path=tmp_path/'qa.db'
    with build_cain(path) as runtime:
        episode(runtime,'O identificador do experimento é TESTE-539.',project='a')
    with build_cain(path) as runtime:
        assert 'TESTE-539' in runtime.identity.context_for('qa','identificador experimento',project_id='a',session_id='new')
        assert 'TESTE-539' not in runtime.identity.context_for('qa','identificador experimento',project_id='b',session_id='s')
        assert 'TESTE-539' not in runtime.identity.context_for('other','identificador experimento',project_id='a',session_id='s')


def test_question_metadata_is_not_an_identifier_fact(tmp_path):
    with build_cain(tmp_path/'qa.db') as runtime:
        runtime.identity.observe('qa','Qual é o identificador do experimento?',{'session_id':'s','decision_id':'technical-only'})
        context=runtime.identity.context_for('qa','identificador experimento',session_id='s')
        assert 'doc_id' not in context and 'technical-only' not in context


def test_shorthand_claims_cover_each_requested_section():
    text='\n\n'.join(f'## CLAIM-DEMO-00{i}\n\nEstado: bloqueada.\n\nHorizonte: {h}.\n\nNão houve comparação.' for i,h in [(1,'24h'),(2,'6h'),(3,'1h')])
    evidence={'doc':{'text':text,'source':'registry.md'}}
    selected,coverage=cards(evidence,'Compare CLAIM-DEMO-001, 002 e 003: estado e horizonte.')
    rendered=json.dumps(selected,ensure_ascii=False)
    assert all('CLAIM-DEMO-00'+str(i) in rendered for i in [1,2,3])
    assert all(h in rendered for h in ['24h','6h','1h'])
    assert set(coverage['question_identifiers'])=={'CLAIM-DEMO-001','CLAIM-DEMO-002','CLAIM-DEMO-003'}


def test_absent_identifier_remains_explicit():
    selected,coverage=cards({'doc':{'text':'## CLAIM-DEMO-001\n\nEstado: bloqueada.','source':'r.md'}},
        'Compare CLAIM-DEMO-001 e CLAIM-DEMO-099.')
    assert selected
    missing=next(r for r in coverage['identity_coverage'] if r['identity']=='CLAIM-DEMO-099')
    assert not missing['accessible'] and not missing['selected_ids']


def test_results_take_precedence_over_registration_procedure():
    evidence = {
        'r': {'source': 'register.md', 'text': '# H42\n\nZERO vereditos. Antes de executar: registrar tudo.\n\n'
              'O resultado corrigido é INCONCLUSIVE_DATA_QUALITY: 7 de 900 sem retorno. Não é P&L executável.'},
        'o': {'source': 'observed.md', 'text': '# H42\n\nPrimeiro resultado: INCONCLUSIVE_DATA_QUALITY; 11 de 900 sem retorno.'},
        'b': {'source': 'runbook.md', 'text': '# Auditoria\n\nEm 2025, exit code 9 indica falha; não demonstra prontidão.'},
    }
    selected, _ = cards(evidence, 'Reconcilie o resultado de H42 e interprete exit code 9.')
    quotes = [v['quote'] for v in selected.values()]
    assert any('7 de 900' in q for q in quotes)
    assert any('11 de 900' in q for q in quotes)
    assert any('exit code 9 indica falha' in q for q in quotes)


def test_reordered_claims_and_ambiguous_suffix_do_not_merge_domains():
    evidence = {'a': {'source': 'a.md', 'text': '## CLAIM-AA-002\n\nHorizonte: 4h.\n\n## CLAIM-AA-003\n\nHorizonte: 8h.'},
                'b': {'source': 'b.md', 'text': '## CLAIM-BB-002\n\nHorizonte: 16h.'}}
    _, coverage = cards(evidence, 'Compare CLAIM-AA-003 e CLAIM-AA-002.')
    assert all(r['selected_ids'] for r in coverage['identity_coverage'])
    _, ambiguous = cards(evidence, 'Compare claims 002 e 003.')
    assert 'CLAIM-AA-002' not in ambiguous['question_identifiers']
    assert 'CLAIM-BB-002' not in ambiguous['question_identifiers']
