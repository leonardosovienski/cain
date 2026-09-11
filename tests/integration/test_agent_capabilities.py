"""Adversarial local workflow fixtures. Real inference is separately recorded."""

from concurrent.futures import ThreadPoolExecutor
import json
from threading import Event
from pathlib import Path
import os
import subprocess
import sys
from time import time

from fastapi.testclient import TestClient
import pytest
from research_snapshot import canonical

from cain.api import create_app
from cain.mcp import Server
from cain.research import ResearchService
from cain.research.analysis import entities, search
from cain.research.workflows import Workflows
import test_research_l0 as cases

setup = cases.setup


class FixtureModel:
    base_url = "http://127.0.0.1:11434"
    model = "fixture-not-real"
    calls = 0
    last_metadata = {"test_fixture":True}

    def generate_json(self, prompt, context, schema):
        self.calls += 1
        payload = json.loads(prompt)
        if "relations" in schema["properties"]:
            ref, text = next(iter(payload["evidence"].items()))
            return json.dumps({"relations":[{"subject":"Alice", "predicate":"reviewed", "object":"Report A",
                                             "reference":ref,"quote":text}]})
        if "excerpts" in payload:
            return json.dumps({"citations":[next(iter(payload["excerpts"]))],
                               "analysis":"Tentative interpretation; uncertainty remains."})
        evidence=payload["evidence"][0]
        return json.dumps({"claims":[{"evidence_id":evidence["reference_id"],"quote":evidence["text"]}],
                           "synthesis":"Tentative interpretation; uncertainty remains."})


def test_workflow_resume_no_repeated_steps_and_backup(setup,tmp_path):
    service, scope, ingest, _, path = setup
    ingest(cases.publication(("A",), text="Alice reviewed Report A."))
    model=FixtureModel()
    jobs=Workflows(service)
    job=jobs.create(scope,"What does A support?",model,source_id="A",run_id="same")
    assert jobs.create(scope,"What does A support?",model,source_id="A",run_id="same")["id"] == "same"
    for _ in range(2):
        job=Workflows(service).advance(scope,job["id"],model)
    assert jobs.advance(scope,job["id"],model)["status"] == "awaiting_generation_approval"
    assert model.calls == 0
    for _ in range(4):
        job=Workflows(service).advance(scope,job["id"],model,approve_generation=True)
    assert job["status"] == "completed"
    assert model.calls == 4
    assert len(job["attempts"]) == 6
    trace = jobs.trace(scope, job["id"])
    spans = trace["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert len(spans) == 6 and len(spans[0]["traceId"]) == 32
    assert int(spans[0]["endTimeUnixNano"]) >= int(spans[0]["startTimeUnixNano"])
    assert "Alice" not in json.dumps(trace) and "What does" not in json.dumps(trace)
    assert jobs.advance(scope,job["id"],model,approve_generation=True)["status"] == "completed"
    assert model.calls == 4
    service.backup(tmp_path/"backup.db")
    restored=ResearchService(tmp_path/"backup.db",path)
    assert Workflows(restored).get(scope,"same")["steps"] == job["steps"]
    with pytest.raises(ValueError):
        jobs.get(service.scope(user="other"),"same")
    with pytest.raises(ValueError,match="another request"):
        jobs.create(scope,"Different",model,run_id="same")


def test_workflow_rejects_changed_prompt_protocol(setup, monkeypatch):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(("A",), text="Alice reviewed Report A."))
    jobs, model = Workflows(service), FixtureModel()
    job = jobs.create(scope, "What does A report?", model, source_id="A")
    monkeypatch.setattr("cain.research.workflows.PROTOCOL", "future-protocol")
    with pytest.raises(ValueError, match="prompt protocol changed"):
        jobs.advance(scope, job["id"], model)
    assert jobs.get(scope, job["id"])["steps"] == [] and model.calls == 0


def test_explicit_abstention_preserves_failure_and_allows_continuation(setup):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(("A",), text="Alice reviewed Report A."))
    class InvalidModel(FixtureModel):
        def generate_json(self, *args):
            self.calls += 1
            return '{"claims":[],"synthesis":"Unsupported interpretation"}'
    model, jobs = InvalidModel(), Workflows(service)
    job = jobs.create(scope, "What is supported?", model, source_id="A", steps=["challenge", "inspect"])
    with pytest.raises(ValueError, match="Only a failed"):
        jobs.abstain(scope, job["id"], "Cannot skip an unexecuted stage")
    with pytest.raises(ValueError, match="Review failed"):
        jobs.advance(scope, job["id"], model, approve_generation=True)
    job = jobs.abstain(scope, job["id"], "Rejected proposal; proceed without accepting it")
    assert job["steps"][0]["result"]["accepted_model_output"] is False
    assert job["attempts"][0]["status"] == "failed"
    assert job["next_step"] == "inspect" and model.calls == 1
    with pytest.raises(ValueError):
        jobs.abstain(scope, job["id"], "Duplicate abstention")
    assert jobs.advance(scope, job["id"], model)["status"] == "completed"


def test_revocation_blocks_results_and_entity_output(setup):
    service,scope,ingest,policy,path=setup
    ingest(cases.publication(("A",),text="Alice reviewed Report A."))
    model=FixtureModel()
    jobs=Workflows(service)
    job=jobs.create(scope,"A?",model,steps=["inspect"])
    jobs.advance(scope,job["id"],model)
    policy["grants"]=[]
    path.write_bytes(canonical(policy))
    assert jobs.list(scope) == []
    with pytest.raises(ValueError,match="changed"):
        jobs.get(scope,job["id"])
    assert entities(service,scope,"A?",model)["status"] == "abstained"
    assert model.calls == 0


def test_invalid_relations_never_promoted(setup):
    service,scope,ingest,_,_=setup
    ingest(cases.publication(("A",),text="No names appear here."))
    with pytest.raises(ValueError,match="source support"):
        entities(service,scope,"Entities?",FixtureModel())


def test_cancel_running_generation_discards_result_and_records_failure(setup):
    service,scope,ingest,_,_=setup
    ingest(cases.publication(("A",),text="Alice reviewed Report A."))
    entered,released=Event(),Event()
    class WaitingModel(FixtureModel):
        def generate_json(self,*args):
            entered.set()
            assert released.wait(10)
            return super().generate_json(*args)
    model=WaitingModel()
    jobs=Workflows(service)
    job=jobs.create(scope,"A?",model,steps=["entities"])
    with ThreadPoolExecutor() as pool:
        future=pool.submit(jobs.advance,scope,job["id"],model,approve_generation=True)
        assert entered.wait(10)
        with pytest.raises(ValueError,match="running"):
            jobs.advance(scope,job["id"],model,approve_generation=True)
        jobs.cancel(scope,job["id"])
        released.set()
        with pytest.raises(ValueError,match="cancelled"):
            future.result()
    stored=jobs.get(scope,job["id"])
    assert stored["status"] == "cancelled" and stored["steps"] == []
    assert stored["attempts"][0]["status"] == "failed"


@pytest.mark.parametrize("question", ["Qual ÃƒÂ© o estado A?", "What is the status of A?"])
def test_relevance_identifier_baseline_pt_en(setup, question):
    service,scope,ingest,_,_=setup
    ingest(cases.publication(("A","B")))
    result=search(service,scope,question)
    assert result["results"][0]["record"]["source_id"] == "A"
    assert result["results"][0]["exact_identity"] is True
    assert search(service,service.scope(collection="other"),question)["results"] == []


def test_mcp_lifecycle_allowlist_and_scope_injection(setup):
    service,scope,ingest,_,_=setup
    ingest(cases.publication())
    server=Server(service,scope)
    def call(method,params=None):
        return server.dispatch({"jsonrpc":"2.0","id":1,"method":method,"params":params or {}})
    assert "error" in call("tools/list")
    assert call("initialize")["result"]["protocolVersion"] == "2025-06-18"
    assert server.dispatch({"jsonrpc":"2.0","method":"notifications/initialized"}) is None
    assert len(call("tools/list")["result"]["tools"]) == 4
    good=call("tools/call",{"name":"research_query","arguments":{"source_id":"A"}})
    assert not good["result"]["isError"]
    assert "error" in call("tools/call",{"name":"exec","arguments":{}})
    assert "error" in call("tools/call",{"name":"research_query","arguments":{"user":"other"}})
    assert "error" in server.dispatch([])


def test_api_tool_and_workflow_shared_services(setup,tmp_path):
    service,scope,ingest,_,path=setup
    ingest(cases.publication(("A",),text="Alice reviewed Report A."))
    with TestClient(create_app(tmp_path/"workspace.db",llm=FixtureModel(),research_policy=path,research_db=service.path)) as client:
        assert client.post("/research/search",json={"question":"A?"}).json()["matches"] == 1
        assert client.post("/research/entities",json={"question":"A?"}).json()["status"] == "proposed"
        job=client.post("/research/jobs",json={"question":"A?","steps":["inspect"]}).json()
        result=client.post(f"/research/jobs/{job['id']}/advance",json={}).json()
        assert result["status"] == "completed"
        assert client.post(f"/research/jobs/{job['id']}/read",json={"user_id":"other"}).status_code == 400
        assert client.post("/research/jobs",json={"question":"A?","steps":["exec"]}).status_code == 400


def test_generation_revoked_during_extraction_is_not_returned(setup):
    service,scope,ingest,policy,path=setup
    ingest(cases.publication(("A",),text="Alice reviewed Report A."))
    class RevokingModel(FixtureModel):
        def generate_json(self,*args):
            value=super().generate_json(*args)
            for grant in policy["grants"]:
                grant["generate"]=False
            path.write_bytes(canonical(policy))
            return value
    with pytest.raises(ValueError,match="changed"):
        entities(service,scope,"A?",RevokingModel())


def test_hybrid_never_embeds_generation_denied_evidence(setup):
    service,scope,ingest,policy,path=setup
    ingest(cases.publication(("A",),text="Alice reviewed Report A."))
    class Encoder:
        base_url="http://127.0.0.1:11434"
        model="fixture"
        model_digest="fixture"
        calls=[]
        def embed(self,texts):
            self.calls.append(texts)
            return [[1,0] for _ in texts]
    encoder=Encoder()
    result=search(service,scope,"A?",embedding=encoder)
    assert result["embedded_records"] == 1
    assert len(encoder.calls) == 1
    for grant in policy["grants"]:
        grant["generate"]=False
    path.write_bytes(canonical(policy))
    denied=search(service,scope,"A?",embedding=encoder)
    assert denied["embedded_records"] == 0 and denied["semantic_skipped_records"] == 1
    assert len(encoder.calls) == 1


def test_expired_lease_requires_explicit_recovery(setup):
    service,scope,ingest,_,_=setup
    ingest(cases.publication())
    model=FixtureModel()
    jobs=Workflows(service)
    job=jobs.create(scope,"A?",model,steps=["inspect"])
    with service.connection() as db:
        db.execute("UPDATE agent_jobs SET status='running',claimed_at=? WHERE id=?",(time()-601,job["id"]))
    with pytest.raises(ValueError,match="running"):
        jobs.advance(scope,job["id"],model)
    assert jobs.advance(scope,job["id"],model,recover=True)["status"] == "completed"


def test_mcp_stdio_subprocess(setup,tmp_path):
    service,_,ingest,_,policy=setup
    ingest(cases.publication(("A",)))
    messages=[{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}},
              {"jsonrpc":"2.0","method":"notifications/initialized"},
              {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"research_query","arguments":{"source_id":"A"}}}]
    environment={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parents[2]/"src")}
    result=subprocess.run([sys.executable,"-m","cain.mcp","--db",str(service.path),"--policy",str(policy),
                           "--collection","crypto","--trusted-local-client"],input="\n".join(json.dumps(m) for m in messages)+"\n",
                          text=True,encoding="utf-8",capture_output=True,timeout=20,cwd=tmp_path,env=environment)
    assert result.returncode == 0, result.stderr
    responses=[json.loads(line) for line in result.stdout.splitlines()]
    assert len(responses) == 2
    assert json.loads(responses[1]["result"]["content"][0]["text"])["records"][0]["source_id"] == "A"


def test_api_stream_has_incremental_tokens_and_terminal_event(setup,tmp_path,monkeypatch):
    from io import BytesIO
    from cain.llm import OllamaLLM
    import cain.llm.streaming as transport
    service,_,_,_,policy=setup
    monkeypatch.setattr(transport,"urlopen",lambda *a,**k:BytesIO(b'{"response":"one","done":false}\n{"response":" two","done":true}\n'))
    with TestClient(create_app(tmp_path/"workspace.db",llm=OllamaLLM(),research_policy=policy,research_db=service.path)) as client:
        response=client.post("/assistant/stream",json={"prompt":"Say two words"})
        events=[json.loads(line) for line in response.text.splitlines()]
        assert [e["type"] for e in events] == ["started","token","token","done"]
        assert events[-1]["text"] == "one two"
