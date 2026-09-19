"""Apply explicitly approved research knowledge under the current source policy."""

import json

from cain.research.grounded_analysis import Evidence, analyze_text


def recover_approved(service, scope, entry_id, session_id=None):
    memory = service.recall(scope, entry_id, session_id=session_id)
    approval = memory.get("evaluator_approval")
    if not isinstance(approval, dict) or approval.get("approved") is not True:
        raise ValueError("Only explicitly approved memory can be applied")
    if not memory.get("facts", {}).get("records"):
        raise ValueError("Approved source evidence unavailable")
    explanation = memory.get("explanation")
    if not isinstance(explanation, dict) or "proposed_synthesis" not in explanation:
        raise ValueError("Approved synthesis unavailable")
    synthesis = explanation["proposed_synthesis"]
    if isinstance(synthesis, dict) and all(
        isinstance(value, dict) and isinstance(value.get("explanation"), str)
        for value in synthesis.values()
    ):
        text = "\n\n".join(
            key + ": " + value["explanation"] for key, value in synthesis.items()
        )
        projection = "verbatim explanation fields; source records retained in memory receipt"
    else:
        text = synthesis if isinstance(synthesis, str) else json.dumps(synthesis, ensure_ascii=False)
        projection = "unchanged synthesis"
    if not text.strip():
        raise ValueError("Approved synthesis unavailable")
    return memory, Evidence("S1", text, "approved memory " + entry_id), projection


def apply_approved(service, scope, entry_id, question, llm, session_id=None):
    """Apply approved knowledge but persist the new answer as an unapproved proposal."""
    memory, evidence, projection = recover_approved(
        service, scope, entry_id, session_id=session_id
    )
    # The user question is prompt context, never evidence supporting its own answer.
    analysis = analyze_text(
        llm,
        question,
        ["conhecimento_recuperado", "aplicacao", "limitacoes"],
        [evidence],
    )
    response = {
        "facts": memory["facts"],
        "explanation": {"proposed_synthesis": analysis["proposal"]},
        "validation": {
            "structural": analysis["structural_status"],
            "semantic": "requires_review",
            "approved": False,
            "answer_review": analysis["answer_review"],
        },
        "user_response": analysis["user_response"],
        "memory_parent": entry_id,
        "memory_projection": projection,
    }
    proposal_id = service.log_explanation(scope, question, response, session_id=session_id)
    return {
        "analysis": analysis,
        "user_response": analysis["user_response"],
        "proposal_id": proposal_id,
        "approved_knowledge": False,
        "memory_parent": entry_id,
        "memory_projection": projection,
    }
