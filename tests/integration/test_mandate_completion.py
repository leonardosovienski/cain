"""Completion regressions: actual Historian route and false success on resume."""
import json
from fastapi.testclient import TestClient
from cain.api import create_app
import test_research_l0 as cases
from test_selection_procedure import command

setup = cases.setup


def test_historian_route_covers_explicit_fields_without_inference(setup, tmp_path):
    service, scope, ingest, _, path = setup
    ingest(cases.publication(('R17',),text='{"R17":{"state":"WAIT","trial":"beta"}}'))
    with TestClient(create_app(tmp_path/'workspace.db',llm=cases.ExplodingProvider(),
                              research_db=service.path,research_policy=path)) as client:
        response=client.post('/research/explain',json={'source_id':'R17','question':'Qual estado e trial de R17? O recorte informa motivo e tamanho da amostra?'})
        assert response.status_code == 200, response.text
        result=response.json()
        assert result['status']=='literal_fields'
        assert 'beta' in result['explanation']['proposed_synthesis']
        assert result['generation']['called'] is False
        assert result['response_id']
        # Snapshot authorization must not grant Bundle access in the integrated app.
        metadata=client.post('/research/bundles/historian',json={'entity_id':'R17'})
        assert metadata.status_code == 200, metadata.text
        assert metadata.json()['bundles']['entities'] == []
        assert metadata.json()['artifact_content_included'] is False


def test_procedure_failed_verification_never_becomes_success_on_resume(setup,tmp_path):
    service, scope, ingest, _, path=setup
    text=json.dumps({'R17':{'reason':'x'*3000}})
    ingest(cases.publication(('R17',),text=text))
    out=tmp_path/'failed-receipt'
    assert command('start','--output',out,'--database',service.path,'--policy',path,'--identity','R17','--pointer','/R17/reason').returncode == 0
    assert command('resume','--output',out).returncode != 0
    assert json.loads((out/'verification.json').read_bytes())['verified'] is False
    assert command('resume','--output',out).returncode != 0


def test_procedure_detects_edited_success_receipt(setup,tmp_path):
    service,scope,ingest,_,path=setup
    ingest(cases.publication(('R17',),text='{"R17":{"state":"WAIT"}}'))
    out=tmp_path/'tampered'
    assert command('start','--output',out,'--database',service.path,'--policy',path,'--identity','R17','--pointer','/R17/state').returncode == 0
    assert command('resume','--output',out).returncode == 0
    report=json.loads((out/'verification.json').read_bytes())
    report['expected_fields']=999
    (out/'verification.json').write_text(json.dumps(report))
    assert command('resume','--output',out).returncode != 0


def test_procedure_rechecks_current_policy_on_resume(setup,tmp_path):
    service,scope,ingest,policy,path=setup
    ingest(cases.publication(('R17',),text='{"R17":{"state":"WAIT"}}'))
    out=tmp_path/'revoked'
    assert command('start','--output',out,'--database',service.path,'--policy',path,'--identity','R17','--pointer','/R17/state').returncode == 0
    policy['grants']=[]
    path.write_text(json.dumps(policy))
    assert command('resume','--output',out).returncode != 0
    assert not (out/'verification.json').exists()


def test_procedure_rejects_literal_quote_with_wrong_pointer(setup,tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    service,scope,ingest,_,path=setup
    ingest(cases.publication(('R17',),text='{"R17":{"state":"WAIT","trial":"beta"}}'))
    out=tmp_path/'wrong-pointer'
    assert command('start','--output',out,'--database',service.path,'--policy',path,'--identity','R17','--pointer','/R17/state').returncode == 0
    script=Path(__file__).parents[2]/'scripts'
    code='''import argparse,sys
import verify_evidence_selection as module
original=module.cards
def wrong(*args,**kwargs):
    chosen,coverage=original(*args,**kwargs)
    row=next(r for r in chosen.values() if r['json_pointer'].endswith('/trial'))
    return {'S1':dict(row,json_pointer='/R17/state')},coverage
module.cards=wrong
module.run(argparse.Namespace(phase='resume',output=sys.argv[1]))
'''
    env=dict(os.environ,PYTHONPATH=str(script)+os.pathsep+str(script.parent/'src'))
    result=subprocess.run([sys.executable,'-c',code,str(out)],env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode != 0 and 'independent JSON pointer lookup' in result.stderr
    assert not (out/'verification.json').exists()
