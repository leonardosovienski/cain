from dataclasses import asdict

from cain.common import Signal
from cain.runtime import build_cain


def test_rule_priority_and_explicit_intent_are_auditable(tmp_path):
    with build_cain(tmp_path / "cain.db") as cain:
        inferred = cain.run("alice", "s1", "Resuma este código Python", run_id="inferred")
        explicit = cain.run("alice", "s1", "Resuma este código Python", intent="codigo", run_id="explicit")
        assert inferred.selected_agent == "resumo"
        assert explicit.selected_agent == "codigo"
        assert "keyword_rule:resumo" in list(cain.decision_log.export("inferred"))[0].reason
        assert "explicit_intent:codigo" in list(cain.decision_log.export("explicit"))[0].reason


def test_unattributed_transcript_does_not_train_profile_and_signal_is_retained(tmp_path):
    with build_cain(tmp_path / "cain.db") as cain:
        before = asdict(cain.identity.get("alice"))
        cain.identity.update("alice", Signal("Prefiro respostas extensas", kind="feedback"))
        after = asdict(cain.identity.get("alice"))
        assert after == before
        assert len(list(cain.store.iter_documents())) == 1
        assert len(cain.store.history("alice", 10)) == 1


def test_identity_context_does_not_retrieve_another_user(tmp_path):
    with build_cain(tmp_path / "cain.db") as cain:
        cain.identity.update("alice", Signal("projeto abacaxi segredo ALICE_ONLY"))
        alice = cain.identity.context_for("alice", "abacaxi")
        bob = cain.identity.context_for("bob", "abacaxi")
        assert "ALICE_ONLY" in alice
        assert "ALICE_ONLY" not in bob
