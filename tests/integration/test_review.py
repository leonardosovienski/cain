"""Adversarial review: checklist blocks pre-registration, map survives restart and shows in the web UI."""

from dataclasses import dataclass, field
from hashlib import sha256
import json

from fastapi.testclient import TestClient
import pytest

from cain.api import create_app
from cain.findings.archive import FindingsArchive
from cain.llm import FakeLLM
from cain.memory.store import MemoryStore, MemoryStoreError
from cain.review.board import ReviewBoard, load_perspectives

DRAFT = {"hypothesis_id": "H11b", "statement": "Refitting the goal model every round beats refitting every 100 games",
         "metric": "RPS 1X2 vs the current serving model", "data": "Brasileirão 2021-2024 panel",
         "design": "walk-forward, paired difference, cluster bootstrap CI", "author": "leo"}


@dataclass
class Reviewer:
    """Structured-output provider that answers per perspective (recognised in the prompt)."""

    seed: int = 42
    last_metadata: dict = field(default_factory=dict)
    calls: list = field(default_factory=list)

    def generate_json(self, prompt, context, schema):
        perspective = json.loads(prompt)["perspective"]["name"]
        self.calls.append(perspective)
        testable = perspective != "Regime change"
        return json.dumps({"questions": [{
            "question": f"{perspective}: what would break this hypothesis?",
            "why": "the gain could be an artefact",
            "testable": testable, "test_kind": "backtest",
            "test": "rerun on a season not used to design the hypothesis" if testable else "",
            "pass_criterion": "CI of the paired RPS difference below zero" if testable else "",
            "not_testable_reason": "" if testable else "a future regime cannot be observed in past data"}]})


@pytest.fixture
def board(tmp_path):
    memory = MemoryStore(tmp_path / "memory.db")
    return ReviewBoard(memory, FindingsArchive(memory))


def test_preregistration_is_refused_while_the_checklist_is_unresolved(board):
    with pytest.raises(MemoryStoreError, match="needs"):
        board.open("brasileirao", {**DRAFT, "metric": ""})
    board.open("brasileirao", DRAFT)
    with pytest.raises(MemoryStoreError, match="REVIEW_MISSING|no adversarial review"):
        board.preregister("brasileirao", "H11b", by="leo")
    reviewer = Reviewer()
    generated = board.generate("brasileirao", "H11b", reviewer)
    assert len(reviewer.calls) == len(load_perspectives()["perspectives"])  # every perspective applies here
    view = board.question_map("brasileirao", "H11b", as_of=board.memory.now())
    statuses = {q["item_id"]: q["status"] for q in view["questions"]}
    assert statuses["H11b:regime-change:1"] == "NOT_TESTABLE"
    assert statuses["H11b:overfitting:1"] == "TEST_PROPOSED"  # a model proposal is not a decision
    assert statuses["H11b:closed-archive:1"] == "ANSWERED"  # nothing closed in the archive yet
    proposed = [i for i, s in statuses.items() if s == "TEST_PROPOSED" and "already-priced" not in i]
    assert sorted(view["blocking"]) == sorted(proposed + ["H11b:regime-change:1"]) and not view["ready_to_preregister"]
    with pytest.raises(MemoryStoreError, match="CHECKLIST_UNRESOLVED|mandatory items"):
        board.preregister("brasileirao", "H11b", by="leo")
    with pytest.raises(MemoryStoreError, match="human"):
        board.accept("brasileirao", "H11b:overfitting:1", by="model:qwen")
    for item in proposed:
        board.accept("brasileirao", item, by="leo")
    with pytest.raises(MemoryStoreError, match="CHECKLIST_UNRESOLVED|mandatory items"):
        board.preregister("brasileirao", "H11b", by="leo")
    with pytest.raises(MemoryStoreError, match="human"):
        board.waive("brasileirao", "H11b:regime-change:1", by="model:qwen", reason="the model thinks it is fine")
    board.waive("brasileirao", "H11b:regime-change:1", by="leo", reason="accepted: evaluated per season, reported")
    done = board.preregister("brasileirao", "H11b", by="leo")
    assert done["state"] == "PREREGISTERED" and done["items"] == len(generated["items"])
    registered = board.memory.facts(as_of=board.memory.now(), cubes=["brasileirao"], subject="H11b",
                                    predicate="preregistered_hypothesis")
    assert registered[-1]["object"]["by"] == "leo"
    assert registered[-1]["source_hash"] == done["checklist_sha256"]


def test_closed_hypothesis_item_blocks_until_a_human_decides(board):
    board.archive.record("brasileirao", "brasileirao:trial:h11", kind="negative", verdict="REFUTED",
                         statement="Refitting the goal model every round beats refitting every 100 games",
                         source={"path": "trials.v2.json", "sha256": sha256(b"x").hexdigest()})
    board.open("brasileirao", DRAFT)
    board.generate("brasileirao", "H11b", Reviewer())
    view = board.question_map("brasileirao", "H11b", as_of=board.memory.now())
    closed = next(q for q in view["questions"] if q["item_id"] == "H11b:closed-archive:1")
    assert closed["status"] == "OPEN" and closed["matches"][0]["finding_id"] == "brasileirao:trial:h11"
    assert "H11b:closed-archive:1" in view["blocking"]
    board.define_test("brasileirao", "H11b:regime-change:1", kind="backtest", by="leo",
                      description="per-season paired RPS difference", pass_criterion="same sign in 3 of 4 seasons")
    for item in view["questions"]:
        if item["status"] == "TEST_PROPOSED":
            board.accept("brasileirao", item["item_id"], by="leo")
    with pytest.raises(MemoryStoreError):
        board.preregister("brasileirao", "H11b", by="leo")
    board.answer("brasileirao", "H11b:closed-archive:1", ref="finding:brasileirao:trial:h11", by="leo",
                 note="same contrast as H11: not a new hypothesis")
    assert board.preregister("brasileirao", "H11b", by="leo")["state"] == "PREREGISTERED"


def test_declared_lineage_is_checked_against_the_closed_archive(board):
    board.archive.record("brasileirao", "brasileirao:trial:h11-refit", kind="negative", verdict="REFUTED",
                         statement="texto em portugues sem palavras em comum", identity={"trial_id": "h11-refit"},
                         source={"path": "trials.v2.json", "sha256": sha256(b"y").hexdigest()})
    board.open("brasileirao", {**DRAFT, "derived_from": "brasileirao:trial:h11-refit"})
    board.generate("brasileirao", "H11b", Reviewer())
    closed = next(q for q in board.question_map("brasileirao", "H11b", as_of=board.memory.now())["questions"]
                  if q["item_id"] == "H11b:closed-archive:1")
    assert closed["status"] == "OPEN" and closed["matches"][0]["same_identity"] == ["trial_id"]


def test_question_map_survives_a_restart_and_shows_in_the_web_interface(tmp_path, monkeypatch):
    path = tmp_path / "memory.db"
    memory = MemoryStore(path)
    board = ReviewBoard(memory, FindingsArchive(memory))
    board.open("brasileirao", DRAFT)
    board.generate("brasileirao", "H11b", Reviewer())
    before = board.question_map("brasileirao", "H11b", as_of=memory.now())
    del board, memory  # "restart": nothing kept in the process
    reopened = MemoryStore(path)
    after = ReviewBoard(reopened, FindingsArchive(reopened)).question_map("brasileirao", "H11b",
                                                                          as_of=before["as_of"])
    assert after["questions"] == before["questions"] and after["blocking"] == before["blocking"]
    monkeypatch.setenv("CAIN_MEMORY_DB", str(path))
    app = create_app(tmp_path / "workspace.db", llm=FakeLLM(), trusted_hosts=("testserver",))
    with TestClient(app) as client:
        response = client.get("/review/brasileirao/H11b")
        assert response.status_code == 200
        shown = response.json()
        assert [q["item_id"] for q in shown["questions"]] == [q["item_id"] for q in before["questions"]]
        assert shown["blocking"] == before["blocking"] and "H11b:regime-change:1" in shown["blocking"]
        assert client.get("/review/brasileirao/unknown").status_code == 404
        page = client.get("/review-map")
        assert page.status_code == 200 and "Mapa de perguntas" in page.text
        # Found in the browser: the API's CSP blocks inline script/style, so the page must not have any.
        assert "<style" not in page.text and "<script>" not in page.text
        assert '<script src="/assets/review.js">' in page.text
        assert client.get("/assets/review.js").status_code == 200
        assert client.get("/assets/review.css").status_code == 200


def test_cli_open_generate_map_waive_and_preregister(tmp_path, capsys, monkeypatch):
    from cain.cli import main
    import cain.providers

    draft = tmp_path / "draft.json"
    draft.write_text(json.dumps(DRAFT), encoding="utf-8")
    db = str(tmp_path / "cli-memory.db")
    monkeypatch.setattr(cain.providers, "configured_llm", lambda settings: Reviewer())
    base = ["review", "--db", db]
    assert main([*base, "open", "--domain", "brasileirao", "--file", str(draft)]) == 0
    assert main([*base, "generate", "--domain", "brasileirao", "H11b"]) == 0
    capsys.readouterr()
    assert main([*base, "preregister", "--domain", "brasileirao", "H11b", "--by", "leo"]) == 1
    capsys.readouterr()
    assert main([*base, "waive", "--domain", "brasileirao", "H11b:regime-change:1", "--by", "leo",
                 "--reason", "reported per season"]) == 0
    capsys.readouterr()
    proposed = ["H11b:overfitting:1", "H11b:temporal-leakage:1", "H11b:costs-execution:1"]
    assert main([*base, "accept", "--domain", "brasileirao", *proposed, "--by", "leo"]) == 0
    assert json.loads(capsys.readouterr().out)["accepted"] == proposed
    assert main([*base, "map", "--domain", "brasileirao", "H11b", "--as-of", "now"]) == 0
    assert json.loads(capsys.readouterr().out)["ready_to_preregister"] is True
    assert main([*base, "preregister", "--domain", "brasileirao", "H11b", "--by", "leo"]) == 0
