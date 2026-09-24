"""Bitemporal memory: leakage, correction, tampering, rebuild, cubes and ingestion paths."""

from contextlib import closing
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import sqlite3

import pytest

from cain.cli import main
from cain.memory import MemoryStore, MemoryStoreError
from cain.memory.ingest import RESEARCH_EXTRACTOR, extract_facts, ingest_research
from cain.research import ResearchService
from research_snapshot import canonical, digest, seal

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


class Clock:
    """Controllable transaction-time clock."""

    def __init__(self, start=T0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, **delta):
        self.now = self.now + timedelta(**delta)
        return self.now


class BagOfWordsEmbedding:
    """Deterministic local stand-in for an embedding model (never a quality claim)."""

    model = "fake-bow"
    model_digest = "sha256:" + "0" * 64
    dimensions = 64

    def __init__(self):
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        vectors = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for token in text.casefold().split():
                vector[int(sha256(token.encode()).hexdigest(), 16) % self.dimensions] += 1.0
            vector[0] += 1e-6
            vectors.append(vector)
        return vectors


def iso(dt):
    return dt.isoformat()


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def memory(tmp_path, clock):
    return MemoryStore(tmp_path / "memory.db", clock=clock)


def test_future_recorded_fact_is_invisible_to_earlier_as_of_including_vector_search(tmp_path, clock):
    embedding = BagOfWordsEmbedding()
    memory = MemoryStore(tmp_path / "memory.db", clock=clock, embedding=embedding)
    memory.assert_fact("crypto", "H9", "result", "inconclusive on btc funding", status="DECLARED")
    before_future = clock.advance(days=1)
    clock.advance(days=30)  # the next fact is recorded 30 days later
    future = memory.assert_fact("crypto", "H9", "result", "LEAK edge confirmed on btc funding", status="DECLARED")
    assert future["recorded_at"] > before_future.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    as_of = iso(before_future)
    visible = memory.facts(as_of=as_of, cubes=["crypto"])
    assert [f["object"] for f in visible] == ["inconclusive on btc funding"]
    # The future fact is the best semantic and lexical match, yet search never sees it.
    result = memory.search("LEAK edge confirmed on btc funding", as_of=as_of, cubes=["crypto"])
    assert result["mode"] == "hybrid" and result["candidates"] == 1
    assert all("LEAK" not in hit["text"] for hit in result["hits"])

    def vector_ids():
        with closing(sqlite3.connect(tmp_path / "memory.db")) as db:
            return {row[0] for row in db.execute("SELECT id FROM memory_vectors")}

    # The temporal filter ran before any vector work: the future row was never even embedded.
    assert future["id"] not in vector_ids()
    later = memory.search("LEAK edge confirmed on btc funding", as_of=iso(clock.now), cubes=["crypto"])
    assert later["hits"][0]["id"] == future["id"]
    assert future["id"] in vector_ids()


def test_read_now_never_precedes_the_log_head(memory, clock):
    # Found as an intermittent CLI failure: a wall clock that steps back made "now" miss an event.
    fact = memory.assert_fact("crypto", "H1", "state", "REFUTED", status="DECLARED")
    clock.advance(seconds=-5)  # the clock steps back after the write
    now = memory.now()
    assert now == fact["recorded_at"]
    assert [f["id"] for f in memory.facts(as_of=now, cubes=["crypto"])] == [fact["id"]]
    clock.advance(seconds=10)
    assert memory.now() > fact["recorded_at"]


def test_corrected_fact_before_and_after_the_correction(memory, clock):
    original = memory.assert_fact("stocks", "QUAL-PIT-MOM-001", "net_excess_bps", 29, status="DECLARED")
    before = iso(clock.advance(hours=1))
    clock.advance(hours=1)
    corrected = memory.correct_fact(original["id"], 31, reason="re-read of the frozen report")
    after = iso(clock.advance(hours=1))
    earlier = memory.facts(as_of=before, cubes=["stocks"])
    assert [f["object"] for f in earlier] == [29]
    # The as-of view must not reveal that a correction happens later.
    assert earlier[0]["superseded_at"] is None
    now = memory.facts(as_of=after, cubes=["stocks"])
    assert [f["object"]["value"] for f in now] == [31] and now[0]["supersedes"] == original["id"]
    chain = memory.fact_history(corrected["id"], as_of=after)
    assert [f["id"] for f in chain] == [original["id"], corrected["id"]]
    assert chain[0]["superseded_at"] == corrected["recorded_at"]
    # Nothing was deleted: the old row is still there, only superseded.
    assert memory.fact_history(original["id"], as_of=before)[0]["superseded_at"] is None
    with pytest.raises(MemoryStoreError) as exc:
        memory.correct_fact(original["id"], 32, reason="second correction of an already superseded fact")
    assert exc.value.code == "SUPERSEDES_UNKNOWN"


def test_tampering_with_an_old_event_breaks_the_chain(memory, tmp_path, clock):
    for index in range(3):
        memory.assert_fact("brasileirao", f"H{index}", "state", "NO_EDGE", status="DECLARED")
        clock.advance(minutes=1)
    assert memory.verify()["status"] == "intact"
    db = sqlite3.connect(tmp_path / "memory.db")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE memory_events SET body = body WHERE seq = 1")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("DELETE FROM memory_events WHERE seq = 1")
    # An attacker with file access drops the trigger and rewrites event 1.
    db.execute("DROP TRIGGER memory_events_no_update")
    body = json.loads(db.execute("SELECT body FROM memory_events WHERE seq = 1").fetchone()[0])
    body["body"]["object"] = "WATCH"
    forged = json.dumps(body, separators=(",", ":"), sort_keys=True)
    db.execute("UPDATE memory_events SET body = ? WHERE seq = 1", (forged,))
    db.commit()
    report = memory.verify()
    assert report["status"] == "broken" and report["broken_at"] == 1
    # Re-hashing the forged event only moves the break to the next link.
    db.execute("UPDATE memory_events SET entry_hash = ? WHERE seq = 1", (sha256(forged.encode()).hexdigest(),))
    db.commit()
    report = memory.verify()
    assert report["status"] == "broken" and report["broken_at"] in (1, 2)
    db.close()
    with pytest.raises(MemoryStoreError) as exc:
        memory.rebuild_index()
    assert exc.value.code == "CHAIN_BROKEN"


def test_tampered_projection_is_detected_and_rebuilt_from_the_log(memory, tmp_path, clock):
    fact = memory.assert_fact("crypto", "H1", "state", "REFUTED", status="DECLARED")
    with closing(sqlite3.connect(tmp_path / "memory.db")) as db, db:
        db.execute("UPDATE memory_facts SET object = '\"SUPPORTED\"' WHERE id = ?", (fact["id"],))
    assert memory.verify()["projection"] == "diverged"
    assert memory.rebuild_index()["events_replayed"] == 1
    assert memory.verify()["projection"] == "consistent"
    assert memory.facts(as_of=iso(clock.now), cubes=["crypto"])[0]["object"] == "REFUTED"


def test_rebuild_index_reproduces_the_same_search(tmp_path, clock):
    embedding = BagOfWordsEmbedding()
    memory = MemoryStore(tmp_path / "memory.db", clock=clock, embedding=embedding)
    for index, text in enumerate(["funding rate carry", "open interest shock", "funding basis drift"]):
        memory.assert_fact("crypto", f"H{index}", "note", text, status="DECLARED")
        memory.record_document("crypto", f"doc {index}", f"report about {text}", published_at=T0 - timedelta(days=1),
                               source=f"fixture:{index}")
        clock.advance(minutes=5)
    as_of = iso(clock.now)
    before = memory.search("funding drift", as_of=as_of, cubes=["crypto"])
    rebuilt = memory.rebuild_index()
    assert rebuilt["events_replayed"] == 6 and rebuilt["vectors"] == 6
    after = memory.search("funding drift", as_of=as_of, cubes=["crypto"])
    assert after == before and before["hits"]
    assert memory.verify()["projection"] == "consistent"


def test_as_of_is_mandatory_on_every_read(memory):
    with pytest.raises(TypeError):
        memory.facts(cubes=["crypto"])
    with pytest.raises(TypeError):
        memory.documents(cubes=["crypto"])
    with pytest.raises(TypeError):
        memory.search("x", cubes=["crypto"])
    with pytest.raises(TypeError):
        memory.fact_history("fact:x")
    with pytest.raises(MemoryStoreError) as exc:
        memory.facts(as_of="2026-09-01T00:00:00", cubes=["crypto"])  # naive instant
    assert exc.value.code == "INVALID_INSTANT"


def test_cubes_are_isolated_unless_crossing_is_explicit(memory, clock):
    memory.assert_fact("crypto", "H9", "state", "NO_EDGE", status="DECLARED")
    memory.assert_fact("brasileirao", "H9", "state", "WATCH_NO_CAPITAL", status="DECLARED")
    as_of = iso(clock.now)
    assert [f["cube"] for f in memory.facts(as_of=as_of, cubes=["crypto"])] == ["crypto"]
    with pytest.raises(MemoryStoreError) as exc:
        memory.facts(as_of=as_of, cubes=["crypto", "brasileirao"])
    assert exc.value.code == "CROSS_CUBE_NOT_EXPLICIT"
    both = memory.facts(as_of=as_of, cubes=["crypto", "brasileirao"], cross_cube=True)
    assert sorted(f["cube"] for f in both) == ["brasileirao", "crypto"]
    with pytest.raises(MemoryStoreError):
        memory.facts(as_of=as_of, cubes="crypto")
    other = memory.facts(as_of=as_of, cubes=["crypto"])[0]
    with pytest.raises(MemoryStoreError):
        memory.assert_fact("brasileirao", "H9", "state", "x", status="DECLARED", supersedes=other["id"])


def test_documents_need_both_publication_and_recording_before_as_of(memory, clock):
    memory.record_document("stocks", "old report", "text A", published_at=T0 - timedelta(days=10), source="s:1")
    memory.record_document("stocks", "future-dated", "text B", published_at=T0 + timedelta(days=10), source="s:2")
    old = memory.documents(as_of=iso(T0), cubes=["stocks"])
    assert [d["title"] for d in old] == ["old report"]
    clock.advance(days=20)
    memory.record_document("stocks", "old report v2", "text A2", published_at=T0 - timedelta(days=10),
                           source="s:1", supersedes=old[0]["id"])
    assert memory.documents(as_of=iso(T0), cubes=["stocks"])[0]["superseded_at"] is None
    assert [d["title"] for d in memory.documents(as_of=iso(clock.now), cubes=["stocks"])] == [
        "old report v2", "future-dated"]
    assert len(memory.documents(as_of=iso(T0 + timedelta(days=11)), cubes=["stocks"])) == 2
    assert memory.documents(as_of=iso(T0 - timedelta(days=1)), cubes=["stocks"]) == []


def test_clock_going_backwards_is_refused(memory, clock):
    memory.assert_fact("crypto", "H1", "state", "x", status="DECLARED")
    clock.now = T0 - timedelta(seconds=1)
    with pytest.raises(MemoryStoreError) as exc:
        memory.assert_fact("crypto", "H2", "state", "y", status="DECLARED")
    assert exc.value.code == "CLOCK_WENT_BACKWARDS"


def test_status_rules_for_proven_and_extracted_facts(memory):
    with pytest.raises(MemoryStoreError) as exc:
        memory.assert_fact("crypto", "H1", "state", "x", status="PROVEN")
    assert exc.value.code == "PROVEN_REQUIRES_SOURCE"
    with pytest.raises(MemoryStoreError) as exc:
        memory.assert_fact("crypto", "H1", "state", "x", status="PROVEN", source_hash="a" * 64,
                           extractor_model="m@d", extractor_version="v")
    assert exc.value.code == "EXTRACTED_FACT_IS_DECLARED"
    with pytest.raises(MemoryStoreError):
        memory.assert_fact("crypto", "H1", "state", float("nan"), status="DECLARED")


class JsonModel:
    model = "qwen-fixture"
    model_digest = "sha256:" + "1" * 64

    def __init__(self, payload):
        self.payload = payload
        self.last_metadata = {"model": self.model}

    def generate_json(self, prompt, context, schema):
        self.prompt, self.context = prompt, context
        return json.dumps(self.payload)


def test_llm_extracted_facts_are_declared_and_literal(memory, clock):
    text = "The H11b hypothesis was closed with NO_EDGE after 380 matches."
    model = JsonModel({"facts": [
        {"subject": "H11b", "predicate": "closed_with", "object": "NO_EDGE",
         "quote": "H11b hypothesis was closed with NO_EDGE"},
        {"subject": "H11b", "predicate": "edge", "object": "confirmed", "quote": "H11b edge confirmed"},
    ]})
    result = extract_facts(memory, model, cube="brasileirao", text=text, source="note:1")
    assert result["facts_created"] == 1 and result["rejected_without_literal_support"] == 1
    fact = memory.facts(as_of=iso(clock.now), cubes=["brasileirao"])[0]
    assert fact["status"] == "DECLARED"
    assert fact["extractor_model"] == "qwen-fixture@sha256:" + "1" * 64
    assert fact["extractor_prompt_hash"] == result["extractor_prompt_hash"]
    assert fact["source_hash"] == sha256(text.encode()).hexdigest()
    with pytest.raises(MemoryStoreError):
        extract_facts(memory, JsonModel({"not": "facts"}), cube="brasileirao", text=text, source="note:2")


def _publication(ids, *, revision="1", supersedes=(), status="FAILED", event_at=None):
    text = f"Record revision {revision}."
    return seal({
        "contract": "ResearchSnapshotV1", "profile": "local-evidence/1", "extensions": {},
        "origin": {"domain": "crypto", "repository": "fixture://crypto", "publisher": "fixture",
                   "stream": "synthetic", "code_revision": "fixture", "exporter_revision": "fixture",
                   "inputs": {"report.md": digest(text.encode())}},
        "exported_at": "2026-09-11T00:00:00Z",
        "restrictions": {"policy": "fixture/1", "read": True, "disclose": False, "generate": True},
        "coverage": {"scope": "Synthetic", "completeness": "partial", "included": ["report.md"],
                     "missing": [], "excluded": [], "limitations": ["synthetic"]},
        "records": [{"source_id": source_id, "revision": revision, "kind": "documented_claim",
                     "identity_basis": "source_assigned", "source_status": status, "status_axis": "scientific",
                     "mapping": None, "reason": None, "event_at": event_at, "recorded_at": None,
                     "available_at": None, "supersedes": list(supersedes), "evidence_ids": ["e"]}
                    for source_id in ids],
        "evidence": [{"id": "e", "source": "report.md", "availability": "received", "text": text,
                      "sha256": digest(text.encode()), "hash_basis": "received_utf8", "locator": "whole_document",
                      "start": 0, "end": len(text), "offset_unit": "unicode_codepoints"}],
    })


@pytest.fixture
def research(tmp_path):
    root = tmp_path / "inbox"
    root.mkdir()
    policy = {"version": 1, "import_root": str(root), "grants": [
        {"user": "leo", "project": "", "collection": "crypto", "domain": "crypto",
         "repository": "fixture://crypto", "publisher": "fixture", "stream": "synthetic",
         "sources": ["report.md"], "policies": ["fixture/1"], "generate": True}]}
    policy_path = tmp_path / "policy.json"
    policy_path.write_bytes(canonical(policy))
    service = ResearchService(tmp_path / "research.db", policy_path)
    scope = service.scope()

    def ingest(package):
        name = package["publication_id"] + ".json"
        (root / name).write_bytes(canonical(package))
        return service.ingest(name, scope)

    return service, scope, ingest, policy_path


def test_research_ingestion_is_deterministic_idempotent_and_supersedes(memory, clock, research):
    service, scope, ingest, _ = research
    ingest(_publication(("H1", "H2"), event_at="2026-08-01T00:00:00Z"))
    first = ingest_research(memory, service, scope, cube="crypto", as_of=iso(clock.now))
    assert first["facts_created"] == 2 and first["records_read"] == 2
    clock.advance(minutes=1)
    again = ingest_research(memory, service, scope, cube="crypto", as_of=iso(clock.now))
    assert again["facts_created"] == 0 and again["skipped_existing"] == 2
    before = iso(clock.now)
    clock.advance(minutes=1)
    ingest(_publication(("H1",), revision="2", supersedes=("1",), status="REFUTED"))
    third = ingest_research(memory, service, scope, cube="crypto", as_of=iso(clock.now))
    assert third["facts_created"] == 1
    now = memory.facts(as_of=iso(clock.now), cubes=["crypto"], subject="H1")
    assert [(f["object"]["revision"], f["object"]["source_status"]) for f in now] == [("2", "REFUTED")]
    old = memory.facts(as_of=before, cubes=["crypto"], subject="H1")
    assert [f["object"]["revision"] for f in old] == ["1"]
    fact = now[0]
    assert fact["status"] == "PROVEN" and fact["extractor_version"] == RESEARCH_EXTRACTOR
    assert fact["extractor_model"] is None
    record = next(r for r in service.query(scope, source_id="H1")["records"] if r["revision"] == "2")
    assert fact["source_episode_id"] == record["publications"][0]


def test_cli_runtime_path(tmp_path, capsys, research):
    service, scope, ingest, policy_path = research
    ingest(_publication(("H7",)))
    db = tmp_path / "cli-memory.db"
    assert main(["memory", "--db", str(db), "ingest-research", "--cube", "crypto",
                 "--research-db", str(tmp_path / "research.db"), "--policy", str(policy_path)]) == 0
    assert json.loads(capsys.readouterr().out)["facts_created"] == 1
    assert main(["memory", "--db", str(db), "add-fact", "--cube", "crypto", "--subject", "H7",
                 "--predicate", "note", "--object", '{"value": 1}']) == 0
    added = json.loads(capsys.readouterr().out)
    assert added["status"] == "DECLARED"
    assert main(["memory", "--db", str(db), "facts", "--as-of", "now", "--cube", "crypto"]) == 0
    listed = json.loads(capsys.readouterr().out)["facts"]
    assert {f["status"] for f in listed} == {"DECLARED", "PROVEN"}
    assert main(["memory", "--db", str(db), "facts", "--as-of", "now", "--cube", "crypto",
                 "--status", "PROVEN"]) == 0
    assert {f["status"] for f in json.loads(capsys.readouterr().out)["facts"]} == {"PROVEN"}
    assert main(["memory", "--db", str(db), "correct", added["id"], "--object", "2", "--reason", "typo"]) == 0
    capsys.readouterr()
    assert main(["memory", "--db", str(db), "search", "H7 note", "--as-of", "now", "--cube", "crypto"]) == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "lexical"
    assert main(["memory", "--db", str(db), "verify"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "intact"
    assert main(["memory", "--db", str(db), "rebuild-index"]) == 0
    assert json.loads(capsys.readouterr().out)["events_replayed"] == 3
    doc = tmp_path / "doc.txt"
    doc.write_text("published note", encoding="utf-8")
    assert main(["memory", "--db", str(db), "add-document", "--cube", "crypto", "--title", "n",
                 "--published-at", "2026-01-01T00:00:00Z", "--source", "file:doc", "--file", str(doc)]) == 0
    capsys.readouterr()
    assert main(["memory", "--db", str(db), "documents", "--as-of", "now", "--cube", "crypto"]) == 0
    assert len(json.loads(capsys.readouterr().out)["documents"]) == 1
    assert main(["memory", "--db", str(db), "history", added["id"], "--as-of", "now"]) == 0
    assert len(json.loads(capsys.readouterr().out)["chain"]) == 1
    # --as-of is required: argparse refuses the read without it.
    with pytest.raises(SystemExit):
        main(["memory", "--db", str(db), "facts", "--cube", "crypto"])
    # Two cubes without --cross-cube fail closed.
    assert main(["memory", "--db", str(db), "facts", "--as-of", "now", "--cube", "crypto",
                 "--cube", "stocks"]) == 1
