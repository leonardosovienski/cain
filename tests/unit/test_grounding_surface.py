"""Characterisation of ``cain.research.grounding`` ahead of its split (Phase 5).

Protected behaviour: every public function stays importable from ``grounding`` with the
same signature, and ``structured``, ``cards`` and the span helpers return exactly the same
values for a fixed evidence set. Golden hashes captured on main at bd025a6 (2026-09-24).
"""
import hashlib
import inspect
import json

from cain.research import grounding as G

DOC = """# CLAIM-CR-001

Hipótese registrada em 2026-09-01. Resultado: falha.

## Motivo

O sinal não superou o custo de execução. Interrompido por risco.

| campo | valor |
| --- | --- |
| status | FAILED |
| trial_id | CLAIM-CR-001 |

# CLAIM-CR-002

Outra hipótese. Resultado: aprovado.
"""
OBS = json.dumps({"id": "CLAIM-CR-001", "observation_revision": "3", "metrics": {"sharpe": 0.4, "trades": 12},
                  "status": "FAILED", "reason": "cost"}, indent=1)
TEXTS = {"pub:doc": DOC, "pub:obs": OBS}
EVIDENCE = {"pub:doc": {"text": DOC, "source": "report.md", "offset_unit": "unicode_codepoints", "start": 0, "end": len(DOC)},
            "pub:obs": {"text": OBS, "source": "obs.jsonl", "offset_unit": "unicode_codepoints", "start": 0, "end": len(OBS)}}
SIGNATURES = {
    "bounded_prose_spans": "(text, source_id, budget)",
    "cards": "(evidence, question, source_id=None, *, max_bytes=2200, max_cards=8)",
    "document_contexts": "(evidence)",
    "document_preamble_span": "(text, start)",
    "heading_spans": "(text, start)",
    "markdown_headings": "(text)",
    "matches_identity": "(relation, source_id)",
    "prose_spans": "(text, source_id)",
    "question_identities": "(question, evidence)",
    "structured": "(evidence, source_id=None, *, addressable=False)",
    "table_header_span": "(text, start, end)",
    "terms_of": "(text)",
    "tokens_of": "(text)",
}
GOLDEN = {
    "structured_default": "22b15feb4d3ca38440539017e654dd0c516a410ab0b1469ebdfa60eeaf1ab2f1",
    "structured_addressable": "188b7c423e4587d24c5ea7f11546582e199cf3d2a386c0cab727390f75b11c59",
    "cards_q1": "dd035727cc81597222cffeb2093b22ade0b327a96b29d1521b6dac20b338ed43",
    "cards_q2": "b90e9d1b29241d273ab54138b6550cc4e53090a1237cb56f54d3ab95a5a1deae",
    "cards_q3": "97b1fbc86b903048f7caa64b13136f7eb7e2904e03d0293f3f8ea1876d4c8f81",
    "document_contexts": "9bfc6ce7cb3d6b99171591e24b197bdda835ce163fee371850c95a15985142a5",
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def test_public_functions_and_signatures_are_stable():
    for name, expected in SIGNATURES.items():
        assert str(inspect.signature(getattr(G, name))) == expected, name
    assert set(SIGNATURES) <= set(getattr(G, "__all__", SIGNATURES))


def test_structured_relations_are_unchanged():
    default = G.structured(TEXTS)
    assert digest(default) == GOLDEN["structured_default"]
    assert default["status"] == "literal" and len(default["relations"]) == 8
    addressable = G.structured(TEXTS, "CLAIM-CR-001", addressable=True)
    assert digest(addressable) == GOLDEN["structured_addressable"] and len(addressable["relations"]) == 6


def test_card_selection_is_unchanged():
    q1 = G.cards(EVIDENCE, "Qual o resultado e o motivo de CLAIM-CR-001?")
    assert digest(q1) == GOLDEN["cards_q1"] and sorted(q1[0]) == ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]
    assert q1[1]["question_identifiers"] == ["CLAIM-CR-001"] and q1[1]["used_bytes"] == 294
    q2 = G.cards(EVIDENCE, "status de CLAIM-CR-001 e CLAIM-CR-002", max_bytes=600, max_cards=3)
    assert digest(q2) == GOLDEN["cards_q2"] and sorted(q2[0]) == ["S1", "S2", "S3"]
    q3 = G.cards(EVIDENCE, "O que diz o relatório?", source_id="CLAIM-CR-002")
    assert digest(q3) == GOLDEN["cards_q3"] and q3[0] == {}


def test_span_helpers_are_unchanged():
    contexts = {k: (v[0][:20], v[1], v[2]) for k, v in G.document_contexts(EVIDENCE).items()}
    assert digest(contexts) == GOLDEN["document_contexts"]
    assert G.prose_spans(DOC, None) == [(0, 14), (16, 68), (70, 79), (81, 145), (147, 226), (228, 242), (244, 280)]
    assert G.prose_spans(DOC, "CLAIM-CR-001") == [(0, 14), (16, 68), (70, 79), (81, 145), (147, 226)]
    assert list(G.markdown_headings(DOC)) == [(1, 0, 14, "CLAIM-CR-001"), (2, 70, 79, "Motivo"), (1, 228, 242, "CLAIM-CR-002")]
    assert G.heading_spans(DOC, 120) == [(0, 14), (70, 79)]
    assert G.document_preamble_span(DOC, 200) is None
    start = DOC.index("| status")
    assert G.table_header_span(DOC, start, start + len("| status | FAILED |")) == (147, 178)
    assert list(G.bounded_prose_spans(DOC, None, 40)) == [(0, 14), (16, 68), (16, 68), (70, 79), (81, 145),
                                                          (81, 145), (147, 226), (228, 242), (244, 280)]
    anchors, resolutions = G.question_identities("resultado de CLAIM-CR-001, 002 e não transfira para CLAIM-CR-002", EVIDENCE)
    assert anchors == ["CLAIM-CR-001"]
    assert [r["rule"] for r in resolutions][:2] == ["explicit_contiguous_prefix_list", "unique_received_claim_suffix"]
    assert resolutions[-1] == {"literal": "CLAIM-CR-002", "rule": "explicit_do_not_transfer_target",
                               "role": "constraint_not_requested_subject"}
    assert G.matches_identity({"subject": "CLAIM-CR-001"}, "CLAIM-CR-001") is True
    assert G.terms_of("hipótese_registrada") == {"hipotese_registrada", "hipotese", "registrada"}
