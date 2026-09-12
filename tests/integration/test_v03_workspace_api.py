"""Local API contracts with injected doubles; these tests perform no model inference."""

from hashlib import sha256
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient
import pytest

from cain.api import create_app


class CaptureModel:
    def __init__(self):
        self.calls = []

    def generate(self, prompt, context=""):
        self.calls.append((prompt, context))
        return "Resposta simulada para teste de integração."


@pytest.fixture
def api(tmp_path):
    config = tmp_path / "test.toml"
    config.write_text(
        '[search]\npaths=[]\nallow_public_urls=false\n'
        '[orchestration]\nllm_routing=false\n', encoding="utf-8",
    )
    database = tmp_path / "workspace.db"
    model = CaptureModel()
    with TestClient(create_app(database, model, config)) as client:
        yield client, model, database, config


def create_project(client, name, user="alice"):
    response = client.post(f"/projects/{user}", json={"name": name})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_project_documents_persist_deduplicate_and_do_not_use_supplied_path(api):
    client, model, database, config = api
    project = create_project(client, " Atlas ")
    content = "Atlas: a licença vence em agosto."
    endpoint = f"/projects/alice/{project}/documents"
    response = client.post(endpoint, json={"title": "../../outside.md", "content": content})
    assert response.status_code == 200, response.text
    document = response.json()
    path = Path(document["path"]).resolve()
    assert path.is_relative_to((database.parent / "knowledge" / project).resolve())
    assert path.name != "outside.md"
    assert path.read_text(encoding="utf-8") == content
    assert document["content_hash"] == sha256(content.encode("utf-8")).hexdigest()
    duplicate = client.post(endpoint, json={"title": "renamed.txt", "content": content})
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["id"] == document["id"]
    assert len(list(path.parent.iterdir())) == 1

    with TestClient(create_app(database, model, config)) as reopened:
        assert reopened.get("/projects/alice").json()[0]["name"] == "Atlas"
        assert reopened.get(endpoint).json()[0]["id"] == document["id"]
        assert reopened.get("/projects/bob").json() == []
        forbidden = f"/projects/bob/{project}/documents"
        assert reopened.get(forbidden).status_code == 400
        assert reopened.post(forbidden, json={"title": "x.md", "content": "x"}).status_code == 400
    assert model.calls == []


@pytest.mark.parametrize("title,content", [
    ("program.py", "print('untrusted')"),
    ("empty.txt", "   "),
    ("large.md", "é" * 131073),  # Under the character limit, over the UTF-8 byte limit.
], ids=["unsupported-extension", "blank-document", "utf8-byte-limit"])
def test_rejected_document_does_not_enter_catalog_or_create_file(api, title, content):
    client, _, database, _ = api
    project = create_project(client, "Documents")
    endpoint = f"/projects/alice/{project}/documents"
    response = client.post(endpoint, json={"title": title, "content": content})
    assert response.status_code == 400, response.text
    assert client.get(endpoint).json() == []
    assert list((database.parent / "knowledge").rglob("*.*")) == []


def test_search_uses_only_the_selected_projects_uploaded_evidence(api):
    client, model, _, _ = api
    projects = [create_project(client, name) for name in ("Atlas", "Boreal")]
    facts = ["Sentinela: o código exclusivo é ATLAS731.",
             "Sentinela: o código exclusivo é BOREAL942."]
    documents = []
    for project, fact in zip(projects, facts, strict=True):
        response = client.post(f"/projects/alice/{project}/documents",
                               json={"title": "sentinela.md", "content": fact})
        assert response.status_code == 200, response.text
        documents.append(response.json())

    for index, project in enumerate(projects):
        response = client.post("/run", json={
            "user_id": "alice", "session_id": f"session-{index}", "project_id": project,
            "payload": "Busque o código exclusivo Sentinela.", "intent": "busca",
        })
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["selected_agent"] == "busca"
        assert len(result["sources"]) == 1
        source = result["sources"][0]
        assert source["citation"] == "S1"
        assert source["excerpt"] == facts[index]
        assert source["document_hash"] == documents[index]["content_hash"]
        assert Path(source["source"]).name == Path(documents[index]["path"]).name
        assert "[S1]" in result["response"]
        assert facts[index] in result["response"]
        assert facts[1 - index] not in result["response"]
    assert model.calls == []  # Search returns literal evidence, without model synthesis.


def test_feedback_requires_owned_response_and_does_not_update_preferences(api):
    client, model, database, _ = api
    preference = client.put("/profile/alice/preferences/format", json={"value": "steps"})
    assert preference.status_code == 200, preference.text
    generated = client.post("/run", json={
        "user_id": "alice", "session_id": "feedback-session",
        "payload": "Resuma: O contrato possui entradas.", "intent": "resumo",
    })
    assert generated.status_code == 200, generated.text
    turn_id = generated.json()["turn_id"]
    before = client.get("/profile/alice").json()
    assert client.post(f"/feedback/{turn_id}", json={
        "user_id": "bob", "reason": "format", "note": "Prefiro um parágrafo.",
    }).status_code == 400
    assert client.post(f"/feedback/{turn_id}", json={
        "user_id": "alice", "reason": "invented-category",
    }).status_code == 422
    saved = client.post(f"/feedback/{turn_id}", json={
        "user_id": "alice", "reason": "format", "note": "Prefiro um parágrafo.",
    })
    assert saved.status_code == 200 and saved.json()["saved"] is True
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT user_id,turn_id,reason,note FROM response_feedback").fetchall() == [
            ("alice", turn_id, "format", "Prefiro um parágrafo."),
        ]
    after = client.get("/profile/alice").json()
    assert after["effective_preferences"] == before["effective_preferences"] == {"format": "steps"}
    assert after["revision"] == before["revision"]
    assert len(model.calls) == 1


def test_profile_answer_uses_effective_state_without_calling_the_model(api):
    client, model, _, _ = api
    project = create_project(client, "Scoped profile")
    assert client.put("/profile/alice/preferences/format", json={"value": "steps"}).status_code == 200
    assert client.put("/profile/alice/preferences/format", json={
        "value": "paragraph", "scope": "project", "project_id": project,
    }).status_code == 200

    def ask(user, session, project_id=None):
        response = client.post("/run", json={
            "user_id": user, "session_id": session, "project_id": project_id,
            "payload": "Quais são minhas preferências atuais?",
        })
        assert response.status_code == 200, response.text
        assert response.json()["route_reason"] == "profile_inspection"
        return response.json()

    scoped = ask("alice", "project-session", project)
    assert scoped["preferences_used"] == scoped["profile"]["effective_preferences"] == {
        "format": "paragraph",
    }
    assert "parágrafo" in scoped["response"] and "passos" not in scoped["response"]
    assert client.delete("/profile/alice/preferences/format", params={
        "scope": "project", "project_id": project,
    }).status_code == 200
    restored = ask("alice", "project-session", project)
    assert restored["preferences_used"] == {"format": "steps"}
    assert "passos numerados" in restored["response"]
    stranger = ask("bob", "other-user-session")
    assert stranger["preferences_used"] == {}
    assert "Não há preferência ativa" in stranger["response"]
    assert model.calls == []


@pytest.mark.parametrize("origin", [
    "https://attacker.example", "http://testserver:9090", "https://testserver", "null",
    "https://testserver:443", "http://user@testserver", "http://testserver/path",
    "http://testserver?query=x", "http://testserver#fragment", "http://testserver:invalid",
])
def test_cross_origin_mutations_are_rejected_before_persistence(api, origin):
    client, model, _, _ = api
    response = client.post("/projects/alice", json={"name": "Injected project"},
                           headers={"Origin": origin})
    assert response.status_code == 403, response.text
    assert client.get("/projects/alice").json() == []
    assert model.calls == []


@pytest.mark.parametrize("headers", [
    {}, {"Origin": "http://testserver"}, {"Origin": "http://testserver:80"},
])
def test_same_origin_browser_and_originless_local_client_are_allowed(api, headers):
    client, _, _, _ = api
    response = client.post("/projects/alice", json={"name": "Local project"}, headers=headers)
    assert response.status_code == 200, response.text
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_untrusted_host_header_is_rejected(api):
    client, _, _, _ = api
    response = client.get("/health", headers={"Host": "attacker.example"})
    assert response.status_code == 400
