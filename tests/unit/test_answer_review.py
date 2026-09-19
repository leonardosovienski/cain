from cain.research.answer_review import parse_sections, receipt_hash, render_pending, review_answer


def example(text, source="Sharpe -0,312. DSR 0,95. n=84."):
    return {
        "question": "Resultado?",
        "fields": ["resultado"],
        "evidence": [{"id": "S1", "text": source, "provenance": "fixture"}],
        "proposal": {"resultado": {"explanation": text, "source_ids": ["S1"]}},
        "structural_errors": [],
    }


def test_numeric_review_preserves_sign_and_percent_units():
    wrong_sign = review_answer(example("Sharpe +0,312. [S1]"))
    assert any(alert.get("token") == "+0,312" for alert in wrong_sign["alerts"])
    percentage = review_answer(example("n=84%. [S1]"))
    assert any(alert.get("token") == "84%" for alert in percentage["alerts"])
    matching = review_answer(example("Sharpe −0.312; n=84. [S1]"))
    assert not any(
        alert["code"] == "number_requires_verification" for alert in matching["alerts"]
    )


def test_numbers_from_an_unreferenced_source_do_not_launder_a_claim():
    analysis = example("n=999 [S1]")
    analysis["evidence"].append({"id": "S2", "text": "n=999", "provenance": "other"})
    assert any(alert.get("token") == "999" for alert in review_answer(analysis)["alerts"])


def test_metric_and_economic_topics_route_to_review_without_claim_classification():
    metric = review_answer(example("Sharpe mínimo 0,95. [S1]"))
    assert any(alert["code"] == "metric_assignment_requires_review" for alert in metric["alerts"])
    negated = review_answer(example("Não há lucro comprovado. [S1]"))
    assert any(alert["code"] == "economic_claim_requires_review" for alert in negated["alerts"])
    assert not any(alert["code"] == "false_claim" for alert in negated["alerts"])


def test_receipt_changes_with_evidence_or_answer():
    analysis = example("n=84 [S1]")
    original = receipt_hash(analysis)
    analysis["evidence"][0]["text"] += " correction"
    assert receipt_hash(analysis) != original
    evidence_changed = receipt_hash(analysis)
    analysis["proposal"]["resultado"]["explanation"] = "n=60 [S1]"
    assert receipt_hash(analysis) != evidence_changed


def test_parser_supports_accented_and_bold_headings_but_rejects_extras():
    text = (
        "### critérios_exatos\nDSR >= 0,95 [S1]\n\n"
        "**Resultado Comparação**\nHistórico [S2]"
    )
    sections, errors = parse_sections(text, ["criterios_exatos", "resultado_comparacao"])
    assert errors == []
    assert sections["criterios_exatos"]["explanation"] == "DSR >= 0,95 [S1]"
    assert sections["resultado_comparacao"]["source_ids"] == ["S2"]
    _, errors = parse_sections("**Extra**\nconteúdo", ["resultado"])
    assert "extra:unexpected_field" in errors
    assert "incorrect_fields" in errors


def test_alert_free_output_still_remains_unapproved_and_malformed_evidence_is_safe():
    analysis = example("Conclusão qualitativa. [S1]")
    assert review_answer(analysis)["alerts"] == []
    assert render_pending(analysis)["review"]["approved_knowledge"] is False
    analysis["evidence"].append({"unexpected": True})
    assert review_answer(analysis)["approved_knowledge"] is False
