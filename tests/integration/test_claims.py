"""Evidence and claims: literal citations, verifier agreement, review queue, linter, trace, golden set."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

import pytest

from cain.claims import assess_empirical, assess_textual, lint_report, review
from cain.claims.extract import extract_claims
from cain.claims.golden import golden_bytes, run_golden
from cain.cli import main
from cain.memory import MemoryStore, MemoryStoreError

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
GOLDEN_V1_SHA256 = "2258a9826e9621628f06661c63ae78ce7aef26e61badd6ba422aaf8e5ff1cf05"


class Clock:
    def __init__(self):
        self.now = T0

    def __call__(self):
        return self.now

    def tick(self, **delta):
        self.now = self.now + timedelta(**(delta or {"seconds": 1}))
        return self.now


class Overlap:
    """Deterministic stand-in: support = share of hypothesis words present in the premise."""

    def __init__(self, verifier_id, threshold=0.8, weights_revision="fake-rev"):
        self.verifier_id, self.threshold, self.weights_revision = verifier_id, threshold, weights_revision

    def score(self, premise, hypothesis):
        words = [w.strip(".,").casefold() for w in hypothesis.split()]
        text = premise.casefold()
        return sum(w in text for w in words) / len(words)


class Constant:
    def __init__(self, verifier_id, value, threshold=0.5):
        self.verifier_id, self.value, self.threshold, self.weights_revision = verifier_id, value, threshold, "c"

    def score(self, premise, hypothesis):
        return self.value


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def memory(tmp_path, clock):
    return MemoryStore(tmp_path / "memory.db", clock=clock)


SOURCE = ("The backtest covered 49 rebalance periods. Net excess return averaged 29 basis points "
          "per period, with a 95% confidence interval from -43 to 95 basis points.")
REPORT = "Our study found that the backtest covered 49 rebalance periods. The net excess was 29 basis points."


def _setup(memory, clock):
    source = memory.record_document("stocks", "frozen report", SOURCE, published_at=T0 - timedelta(days=5),
                                    source="fixture:report")
    clock.tick()
    report = memory.record_document("stocks", "draft", REPORT, published_at=T0, source="fixture:draft")
    clock.tick()
    return source, report


def _span(text, fragment):
    start = text.index(fragment)
    return start, start + len(fragment)


def test_invented_or_normalized_quote_is_rejected(memory, clock):
    source, _ = _setup(memory, clock)
    start, end = _span(SOURCE, "49 rebalance periods")
    evidence = memory.record_evidence("stocks", source["id"], start, end, "49 rebalance periods")
    assert evidence["doc_hash"] == sha256(SOURCE.encode()).hexdigest()
    for quote, (a, b) in (("49 rebalancing periods", (start, end)),            # invented wording
                          ("49  rebalance periods", (start, end)),             # whitespace-normalized
                          ("49 rebalance periods", (start + 1, end + 1)),       # right text, wrong offsets
                          ("49 rebalance periods", (0, 10_000))):              # outside the document
        with pytest.raises(MemoryStoreError) as exc:
            memory.record_evidence("stocks", source["id"], a, b, quote)
        assert exc.value.code == "QUOTE_NOT_LITERAL"
    with pytest.raises(MemoryStoreError) as exc:
        memory.record_evidence("crypto", source["id"], start, end, "49 rebalance periods")
    assert exc.value.code == "DOCUMENT_UNKNOWN"


def test_number_without_provenance_blocks_the_report(memory, clock, tmp_path):
    source, report = _setup(memory, clock)
    s, e = _span(SOURCE, "49 rebalance periods")
    evidence = memory.record_evidence("stocks", source["id"], s, e, "49 rebalance periods")
    clock.tick()
    now = clock.now.isoformat()
    blocked = lint_report(memory, "The backtest covered 49 periods.", as_of=now, cubes=["stocks"])
    assert blocked["status"] == "blocked" and blocked["violations"][0]["code"] == "NO_PROVENANCE"
    ok = lint_report(memory, f"The backtest covered 49 periods [ev:{evidence['id']}].", as_of=now, cubes=["stocks"])
    assert ok["status"] == "publishable" and ok["numbers_checked"] == 1
    wrong = lint_report(memory, f"Net excess was 31 bps [ev:{evidence['id']}].", as_of=now, cubes=["stocks"])
    assert wrong["status"] == "blocked" and wrong["violations"][0]["code"] == "NOT_IN_CITED_SOURCE"
    unknown = lint_report(memory, "It was 49 [ev:evidence:missing].", as_of=now, cubes=["stocks"])
    assert unknown["violations"][0]["unresolved_markers"] == ["ev:evidence:missing"]
    layout = lint_report(memory, "## 2. Results\n1. No numbers here.", as_of=now, cubes=["stocks"])
    assert layout["status"] == "publishable" and layout["numbers_checked"] == 0
    # An evidence recorded after as_of does not count as provenance at as_of.
    earlier = lint_report(memory, f"49 periods [ev:{evidence['id']}].", as_of=T0.isoformat(), cubes=["stocks"])
    assert earlier["status"] == "blocked"
    # Runs: only a SUPPORTED EMPIRICAL_PROOF claim whose artifact still hashes the same counts.
    artifact = tmp_path / "run-report.txt"
    artifact.write_text("run r-7: net excess 29 bps over 49 periods", encoding="utf-8")
    digest = sha256(artifact.read_bytes()).hexdigest()
    rs, re_ = _span(REPORT, "The net excess was 29 basis points.")
    claim = memory.record_claim("stocks", "Net excess was 29 basis points.", source_document_id=report["id"],
                                char_start=rs, char_end=re_, kind="EMPIRICAL_PROOF",
                                run_ref={"run_id": "r-7", "report_sha256": digest, "report_path": artifact.name})
    clock.tick()
    assert assess_empirical(memory, claim["id"], root=tmp_path)["status"] == "SUPPORTED"
    clock.tick()
    text = f"Net excess was 29 bps [run:r-7@{digest}]."
    assert lint_report(memory, text, as_of=clock.now.isoformat(), cubes=["stocks"], root=tmp_path)["status"] == "publishable"
    artifact.write_text("run r-7: net excess 31 bps", encoding="utf-8")
    assert lint_report(memory, text, as_of=clock.now.isoformat(), cubes=["stocks"], root=tmp_path)["status"] == "blocked"


def test_verifier_disagreement_goes_to_the_human_review_queue(memory, clock):
    source, report = _setup(memory, clock)
    s, e = _span(SOURCE, "Net excess return averaged 29 basis points per period")
    evidence = memory.record_evidence("stocks", source["id"], s, e, SOURCE[s:e])
    cs, ce = _span(REPORT, "The net excess was 29 basis points.")
    claim = memory.record_claim("stocks", "Net excess return averaged 29 basis points.", source_document_id=report["id"],
                                char_start=cs, char_end=ce, evidence_ids=[evidence["id"]])
    clock.tick()
    result = assess_textual(memory, claim["id"], [Overlap("v-a"), Constant("v-b", 0.1)])
    assert result["status"] == "INCONCLUSIVE" and result["review_state"] == "needs_human_review"
    assert result["verifier_scores"]["v-a"]["score"] >= 0.8 and result["verifier_scores"]["v-b"]["score"] == 0.1
    assert result["verifier_scores"]["policy"] == "custom"
    before_review = clock.tick()
    queue = [c for c in memory.claims(as_of=clock.now, cubes=["stocks"]) if c["review_state"] == "needs_human_review"]
    assert [c["id"] for c in queue] == [claim["id"]]
    clock.tick()
    review(memory, claim["id"], "CONTRADICTED", reviewer="leo", note="source says 29 per period, not overall")
    assert memory.claims(as_of=before_review, cubes=["stocks"])[0]["status"] == "INCONCLUSIVE"
    now = memory.claims(as_of=clock.now, cubes=["stocks"])[0]
    assert now["status"] == "CONTRADICTED" and now["assessed_by"] == "human:leo"
    with pytest.raises(MemoryStoreError):
        review(memory, claim["id"], "SUPPORTED", reviewer="leo", note=" ")


def test_agreement_decides_and_long_documents_use_the_best_chunk(memory, clock):
    filler = "Unrelated operational notes about scheduling and storage. " * 120
    text = filler + "The confirmed hit rate was 61 percent in the holdout. " + filler
    doc = memory.record_document("crypto", "long", text, published_at=T0, source="fixture:long")
    report = memory.record_document("crypto", "draft", "Hit rate 61 percent.", published_at=T0, source="fixture:d")
    clock.tick()
    s, e = _span(text, "The confirmed hit rate was 61 percent in the holdout.")
    evidence = memory.record_evidence("crypto", doc["id"], s, e, text[s:e])
    claim = memory.record_claim("crypto", "The confirmed hit rate was 61 percent in the holdout.",
                                source_document_id=report["id"], char_start=0, char_end=20,
                                evidence_ids=[evidence["id"]])
    clock.tick()
    supported = assess_textual(memory, claim["id"], [Overlap("v-a"), Overlap("v-b", threshold=0.9)], chunk_size=800)
    assert supported["status"] == "SUPPORTED" and supported["review_state"] == "not_applicable"
    other = memory.record_claim("crypto", "The hit rate was 99 percent everywhere.", source_document_id=report["id"],
                                char_start=0, char_end=20, evidence_ids=[evidence["id"]])
    clock.tick()
    rejected = assess_textual(memory, other["id"], [Constant("v-a", 0.2), Constant("v-b", 0.3)])
    assert rejected["status"] == "INCONCLUSIVE" and rejected["review_state"] == "not_applicable"
    with pytest.raises(MemoryStoreError):
        assess_textual(memory, claim["id"], [Overlap("v-a")])
    no_evidence = memory.record_claim("crypto", "Something.", source_document_id=report["id"], char_start=0,
                                      char_end=5)
    clock.tick()
    assert assess_textual(memory, no_evidence["id"], [Overlap("a"), Overlap("b")])["status"] == "UNVERIFIABLE"


def test_the_policy_thresholds_decide_and_cannot_be_moved_at_call_time(memory, clock):
    from cain.claims.verifiers import HHEM_REPO, MINICHECK_REPO, policy

    text = "The confirmed hit rate was 61 percent in the holdout."
    doc = memory.record_document("crypto", "doc", text, published_at=T0, source="fixture:p")
    clock.tick()
    evidence = memory.record_evidence("crypto", doc["id"], 0, len(text), text)
    claim = memory.record_claim("crypto", text, source_document_id=doc["id"], char_start=0, char_end=len(text),
                                evidence_ids=[evidence["id"]])
    clock.tick()
    rules = policy(claim["recorded_at"])
    # The policy's own verifiers with another threshold: refused before any scoring.
    moved = [Overlap(HHEM_REPO, threshold=0.3), Overlap(MINICHECK_REPO, threshold=rules["thresholds"][MINICHECK_REPO])]
    with pytest.raises(MemoryStoreError) as refused:
        assess_textual(memory, claim["id"], moved)
    assert refused.value.code == "POLICY_MISMATCH"
    assert memory.claims(as_of=memory.now(), cubes=["crypto"], ids=[claim["id"]])[0]["rule"] is None  # nothing decided
    # With the policy's thresholds, the decision records the policy (id, version, sha256).
    pair = [Overlap(HHEM_REPO, threshold=rules["thresholds"][HHEM_REPO]),
            Overlap(MINICHECK_REPO, threshold=rules["thresholds"][MINICHECK_REPO])]
    decided = assess_textual(memory, claim["id"], pair)
    assert decided["verifier_scores"]["policy"] == {"policy": rules["policy"], "version": rules["version"],
                                                    "sha256": rules["sha256"]}


def test_textual_support_and_empirical_proof_are_never_mixed(memory, clock, tmp_path):
    _, report = _setup(memory, clock)
    with pytest.raises(MemoryStoreError) as exc:
        memory.record_claim("stocks", "x", source_document_id=report["id"], char_start=0, char_end=5,
                            run_ref={"run_id": "r", "report_sha256": "a" * 64, "report_path": "p"})
    assert exc.value.code == "RUN_REF_ON_TEXTUAL"
    with pytest.raises(MemoryStoreError) as exc:
        memory.record_claim("stocks", "x", source_document_id=report["id"], char_start=0, char_end=5,
                            kind="EMPIRICAL_PROOF")
    assert exc.value.code == "RUN_REF_REQUIRED"
    with pytest.raises(MemoryStoreError) as exc:
        memory.record_claim("stocks", "x", source_document_id=report["id"], char_start=0, char_end=5,
                            status="SUPPORTED")
    assert exc.value.code == "INVALID_STATUS"
    artifact = tmp_path / "r.txt"
    artifact.write_text("49 periods", encoding="utf-8")
    ref = {"run_id": "r", "report_sha256": sha256(artifact.read_bytes()).hexdigest(), "report_path": "r.txt"}
    empirical = memory.record_claim("stocks", "It covered 49 periods and 12 regimes.", source_document_id=report["id"],
                                    char_start=0, char_end=5, kind="EMPIRICAL_PROOF", run_ref=ref)
    textual = memory.record_claim("stocks", "x", source_document_id=report["id"], char_start=0, char_end=5)
    clock.tick()
    with pytest.raises(MemoryStoreError):
        assess_textual(memory, empirical["id"], [Overlap("a"), Overlap("b")])
    with pytest.raises(MemoryStoreError):
        assess_empirical(memory, textual["id"], root=tmp_path)
    missing_number = assess_empirical(memory, empirical["id"], root=tmp_path)
    assert missing_number["status"] == "UNVERIFIABLE" and "12" in missing_number["note"]
    clock.tick()
    artifact.write_text("tampered", encoding="utf-8")
    assert assess_empirical(memory, empirical["id"], root=tmp_path)["note"] == "run artifact sha256 differs from run_ref"


class JsonModel:
    model, model_digest = "qwen-fixture", "sha256:" + "2" * 64

    def __init__(self, payload):
        self.payload, self.last_metadata = payload, {"eval_count": 3}

    def generate_json(self, prompt, context, schema):
        return json.dumps(self.payload)


def test_extraction_keeps_only_literal_spans_and_never_guesses(memory, clock):
    _, report = _setup(memory, clock)
    model = JsonModel({"claims": [
        {"text": "The backtest covered 49 rebalance periods.", "source_quote": "the backtest covered 49 rebalance periods",
         "verifiable": True, "ambiguous": False, "reason": "count"},
        {"text": "The net excess (per period or total?) was 29 basis points.", "source_quote": "The net excess was 29 basis points.",
         "verifiable": True, "ambiguous": True, "reason": "unit unclear"},
        {"text": "Our study is important.", "source_quote": "Our study found", "verifiable": False,
         "ambiguous": False, "reason": "opinion"},
        {"text": "Invented.", "source_quote": "a sentence that is not in the report", "verifiable": True,
         "ambiguous": False, "reason": "x"},
    ]})
    result = extract_claims(memory, model, cube="stocks", document_id=report["id"])
    assert [c["status"] for c in result["claims"]] == ["INCONCLUSIVE", "AMBIGUOUS", "UNVERIFIABLE"]
    assert len(result["rejected"]) == 1
    stored = memory.claims(as_of=clock.now, cubes=["stocks"])
    assert {c["extractor"]["model_digest"] for c in stored} == {"sha256:" + "2" * 64}
    first = next(c for c in stored if c["status"] == "INCONCLUSIVE")
    assert REPORT[first["source_start"]:first["source_end"]] == first["source_quote"]
    assert first["review_state"] == "pending_verification"
    with pytest.raises(MemoryStoreError):
        extract_claims(memory, JsonModel({"nope": 1}), cube="stocks", document_id=report["id"])


def test_extraction_with_a_local_ollama_model_records_the_installed_digest(memory, clock, monkeypatch):
    # Found by the runtime demo: OllamaLLM has no model_digest attribute, so the digest was null.
    from cain.llm import OllamaLLM

    class Local(OllamaLLM):
        def generate_json(self, prompt, context, schema):
            return json.dumps({"claims": [{"text": "The backtest covered 49 rebalance periods.",
                                           "source_quote": "the backtest covered 49 rebalance periods",
                                           "verifiable": True, "ambiguous": False, "reason": "count"}]})

    class Tags:
        def __init__(self, models):
            self.raw = json.dumps({"models": models}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            return self.raw

    _, report = _setup(memory, clock)
    installed = [{"name": "qwen-local:4b", "digest": "9" * 64}]
    monkeypatch.setattr("cain.research.workflows.urlopen", lambda *a, **kw: Tags(installed))
    result = extract_claims(memory, Local(model="qwen-local:4b"), cube="stocks", document_id=report["id"])
    assert result["extractor"]["model_digest"] == "9" * 64
    monkeypatch.setattr("cain.research.workflows.urlopen", lambda *a, **kw: Tags([]))
    with pytest.raises(MemoryStoreError, match="cannot establish the model digest"):
        extract_claims(memory, Local(model="qwen-local:4b"), cube="stocks", document_id=report["id"])


def test_trace_answers_where_a_number_came_from(memory, clock):
    source, report = _setup(memory, clock)
    s, e = _span(SOURCE, "49 rebalance periods")
    evidence = memory.record_evidence("stocks", source["id"], s, e, "49 rebalance periods", query="how many periods")
    cs, ce = _span(REPORT, "the backtest covered 49 rebalance periods")
    claim = memory.record_claim("stocks", "The backtest covered 49 rebalance periods.", source_document_id=report["id"],
                                char_start=cs, char_end=ce, evidence_ids=[evidence["id"]])
    clock.tick()
    assess_textual(memory, claim["id"], [Overlap("v-a"), Overlap("v-b")])
    trace = memory.claim_trace(claim["id"], as_of=clock.now)
    assert trace["claim"]["status"] == "SUPPORTED"
    assert trace["source_document"]["id"] == report["id"]
    assert trace["evidence"][0]["quote"] == "49 rebalance periods"
    assert trace["evidence_documents"][source["id"]]["content_sha256"] == sha256(SOURCE.encode()).hexdigest()
    assert [a["status"] for a in trace["assessments"]] == ["SUPPORTED"]
    assert memory.verify() == {**memory.verify(), "status": "intact", "projection": "consistent"}
    rebuilt = memory.rebuild_index()
    assert rebuilt["events_replayed"] == 5
    assert memory.claims(as_of=clock.now, cubes=["stocks"])[0]["status"] == "SUPPORTED"
    assert memory.claims(as_of=clock.now, cubes=["stocks"], unsupported=True) == []


def test_golden_set_is_frozen_and_measured_by_the_runner():
    assert sha256(golden_bytes()).hexdigest() == GOLDEN_V1_SHA256
    result = run_golden([Overlap("v-a", threshold=0.9), Constant("v-b", 0.9)])
    assert result["pairs"] == 48 and result["golden_sha256"] == GOLDEN_V1_SHA256
    assert result["verifiers"]["v-b"]["all"] == {"correct": 24, "total": 48, "accuracy": 0.5}
    combined = result["combined"]["all"]
    assert combined["decided"] + combined["sent_to_review"] == 48


def test_cli_paths(memory, clock, tmp_path, capsys, monkeypatch):
    db = str(tmp_path / "cli.db")
    source_file = tmp_path / "source.txt"
    source_file.write_text(SOURCE, encoding="utf-8")
    assert main(["memory", "--db", db, "add-document", "--cube", "stocks", "--title", "src",
                 "--published-at", "2026-09-01T00:00:00Z", "--source", "file:src", "--file", str(source_file)]) == 0
    doc = json.loads(capsys.readouterr().out)
    s, e = _span(SOURCE, "49 rebalance periods")
    assert main(["claims", "--db", db, "add-evidence", "--cube", "stocks", "--document-id", doc["id"],
                 "--start", str(s), "--end", str(e), "--quote", "49 rebalance periods"]) == 0
    evidence = json.loads(capsys.readouterr().out)
    assert main(["claims", "--db", db, "add-evidence", "--cube", "stocks", "--document-id", doc["id"],
                 "--start", str(s), "--end", str(e), "--quote", "49 rebalancing periods"]) == 1
    capsys.readouterr()
    assert main(["claims", "--db", db, "add-claim", "--cube", "stocks", "--text", "It covered 49 rebalance periods.",
                 "--document-id", doc["id"], "--start", str(s), "--end", str(e), "--evidence", evidence["id"]]) == 0
    claim = json.loads(capsys.readouterr().out)
    monkeypatch.setattr("cain.claims.verifiers.load_default_pair", lambda models_dir=None: [Overlap("a"), Constant("b", 0.1)])
    assert main(["claims", "--db", db, "verify", claim["id"]]) == 0
    assert json.loads(capsys.readouterr().out)["review_state"] == "needs_human_review"
    assert main(["claims", "--db", db, "review-queue", "--as-of", "now", "--cube", "stocks"]) == 0
    assert len(json.loads(capsys.readouterr().out)["review_queue"]) == 1
    assert main(["claims", "--db", db, "review", claim["id"], "--status", "SUPPORTED", "--reviewer", "leo",
                 "--note", "checked against the frozen report"]) == 0
    capsys.readouterr()
    assert main(["claims", "--db", db, "list", "--as-of", "now", "--cube", "stocks", "--unsupported"]) == 0
    assert json.loads(capsys.readouterr().out)["claims"] == []
    assert main(["claims", "--db", db, "trace", claim["id"], "--as-of", "now"]) == 0
    assert len(json.loads(capsys.readouterr().out)["assessments"]) == 2
    report = tmp_path / "report.md"
    report.write_text("It covered 49 periods.", encoding="utf-8")
    assert main(["claims", "--db", db, "lint", str(report), "--as-of", "now", "--cube", "stocks"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "blocked"
    report.write_text(f"It covered 49 periods [claim:{claim['id']}].", encoding="utf-8")
    assert main(["claims", "--db", db, "lint", str(report), "--as-of", "now", "--cube", "stocks"]) == 0
