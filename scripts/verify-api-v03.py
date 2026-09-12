"""Bounded real-provider verification; synthetic data in a separate local database."""
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
import tempfile

from fastapi.testclient import TestClient
from cain.api import create_app

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=ROOT / 'evaluation/results/api-v03-replay')
OUT = parser.parse_args().output
OUT.mkdir(parents=True, exist_ok=False)
records, checks = [], {}

def save():
    (OUT / 'verification.json').write_text(json.dumps({
        'synthetic_data': True, 'real_llm': True, 'ui_browser_tested': False,
        'scientific_result': False, 'created_at': datetime.now(timezone.utc).isoformat(),
        'config_toml': (ROOT / 'cain.toml').read_text(encoding='utf-8'),
        'backend_sha256': {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in (
            'src/cain/identity/__init__.py', 'src/cain/agents/__init__.py',
            'src/cain/llm/__init__.py', 'src/cain/api.py')},
        'checks': checks, 'records': records,
    }, ensure_ascii=False, indent=2), encoding='utf-8')

try:
    with tempfile.TemporaryDirectory(prefix='cain-api-v03-') as temporary:
        database = Path(temporary) / 'cain.db'
        with TestClient(create_app(db_path=database, config_path=ROOT / 'cain.toml')) as client:
            def call(method, path, **kwargs):
                response = client.request(method, path, **kwargs)
                data = response.json()
                if response.status_code != 200:
                    records.append({'method': method, 'path': path, 'status': response.status_code, 'data': data})
                    save()
                assert response.status_code == 200, (path, response.status_code, data)
                return data
            user = 'verification-v03-synthetic'
            project = call('POST', f'/projects/{user}', json={'name': 'Verificação sintética'})['id']
            doc_text = 'Projeto Íris: a chave de teste é IRIS731. A entrega ocorreu na sexta-feira. O preço não está informado.'
            document = call('POST', f'/projects/{user}/{project}/documents', json={'title': 'iris.md', 'content': doc_text})
            session = call('POST', f'/sessions/{user}', json={'project_id': project})['id']
            other_session = call('POST', f'/sessions/{user}', json={'project_id': project})['id']
            for scope, value in [('user', 'paragraph'), ('project', 'steps'), ('session', 'bullets')]:
                call('PUT', f'/profile/{user}/preferences/format', json={
                    'value': value, 'scope': scope, 'project_id': project, 'session_id': session,
                })
            for key, value in [('language', 'pt'), ('verbosity', 'short')]:
                call('PUT', f'/profile/{user}/preferences/{key}', json={'value': value, 'scope': 'user'})
            def run(payload, sid=session, pid=project):
                result = call('POST', '/run', json={'user_id': user, 'session_id': sid, 'project_id': pid, 'payload': payload})
                records.append({'payload': payload, 'result': result})
                save()
                return result
            turn = run('Só nesta resposta, prefiro um parágrafo. Resuma: A versão Íris passou por testes internos; a produção continua não autorizada.')
            checks['turn_overrides_session'] = turn['preferences_used']['format'] == 'paragraph'
            after = run('Resuma: A revisão ocorrerá na sexta-feira. O lançamento ainda não tem data.')
            checks['turn_does_not_persist'] = after['preferences_used']['format'] == 'bullets'
            code = run('Escreva código Python para somar dois números.', sid=other_session)
            checks['project_used_in_new_session'] = code['preferences_used']['format'] == 'steps'
            answer = run('Busque nos documentos a chave de teste IRIS731.', sid=other_session)
            checks['source_returned'] = bool(answer['sources'])
            checks['document_fact_visible_literally'] = doc_text in answer['response']
            checks['search_has_no_free_generation'] = not answer['generation']
            checks['document_search_excludes_history'] = all(s['metadata'].get('retrieval_mode') != 'user_history' for s in answer['sources'])
            checks['source_hash'] = any(s['document_hash'] == document['content_hash'] for s in answer['sources'])
            checks['source_excerpt_reproducible'] = all(
                doc_text[s['start_offset']:s['end_offset']] == s['excerpt']
                and sha256(s['excerpt'].encode()).hexdigest() == s['excerpt_hash']
                for s in answer['sources'] if s['document_hash'] == document['content_hash'])
            checks['real_embedding_metadata'] = any(s['metadata'].get('embedding_model') == 'qwen3-embedding:0.6b' for s in answer['sources'])
            inspect = run('Qual é minha preferência atual de formato?', sid=other_session)
            checks['profile_answer_authoritative'] = inspect['route_reason'] == 'profile_inspection' and not inspect['generation']
            call('DELETE', f'/profile/{user}/preferences/format', params={
                'scope': 'session', 'project_id': project, 'session_id': session,
            })
            profile = call('GET', f'/profile/{user}', params={'project_id': project, 'session_id': session})
            checks['remove_session_reveals_project'] = profile['effective_preferences']['format'] == 'steps'
            call('DELETE', f'/profile/{user}/preferences/format', params={
                'scope': 'project', 'project_id': project, 'session_id': session,
            })
            profile = call('GET', f'/profile/{user}', params={'project_id': project, 'session_id': session})
            checks['remove_project_reveals_global'] = profile['effective_preferences']['format'] == 'paragraph'
            feedback = call('POST', f"/feedback/{answer['turn_id']}", json={'user_id': user, 'reason': 'useful'})
            checks['feedback_saved'] = feedback['saved'] is True
            history = call('GET', f'/sessions/{user}/{other_session}', params={'project_id': project})
            checks['history_turn_ids_consistent'] = all(item['id'] == item['result']['decision_id'] == item['result']['turn_id'] for item in history)
            checks['models_complete'] = all(record['result']['generation'].get('done_reason') == 'stop' for record in records if record['result']['generation'])
        with TestClient(create_app(db_path=database, config_path=ROOT / 'cain.toml')) as reopened:
            restored = reopened.get(f'/profile/{user}').json()
            checks['profile_survives_reopen'] = restored['effective_preferences']['format'] == 'paragraph'
    save()
    print(json.dumps(checks, indent=2))
    assert all(checks.values()), 'Some mechanical checks failed; inspect verification.json'
finally:
    save()

