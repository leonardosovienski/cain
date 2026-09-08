from dataclasses import asdict

import pytest

from cain.common import CainRunError
from cain.orchestrator import RuleRouter
from cain.runtime import build_cain


class RecordingLLM:
    def __init__(self):
        self.calls = []

    def generate(self, prompt: str, context: str = "") -> str:
        self.calls.append((prompt, context))
        return "Resposta real do dublê instrumentado"


def test_eight_steps_persistence_across_sessions_and_users(tmp_path):
    path = tmp_path / "cain.db"
    llm = RecordingLLM()
    with build_cain(path, llm) as first:
        state = first.identity.get("alice")
        state.user_model.preferences["format"] = "bullet points"
        first.store.upsert("alice", state)
        result = first.run("alice", "session-1", "Resuma o projeto ABACAXI_ALICE", run_id="r1")
        assert len(result.steps) == 8
        assert "bullet points" in llm.calls[-1][1]
        logs = list(first.decision_log.export("r1"))
        assert [item.status for item in logs] == ["mediated", "completed"]
        assert logs[0].decision_id == result.decision_id
        assert logs[1].metadata["parent_decision_id"] == result.decision_id
        expected = asdict(first.identity.get("alice"))
    with build_cain(path, llm) as reopened:
        assert asdict(reopened.identity.get("alice")) == expected
        reopened.run("alice", "session-2", "Resuma ABACAXI_ALICE", run_id="r2")
        assert "Usuário: Resuma o projeto ABACAXI_ALICE" in llm.calls[-1][1]
        reopened.run("bob", "session-1", "Resuma o projeto", run_id="r3")
        assert "ABACAXI_ALICE" not in llm.calls[-1][1]
        assert "bullet points" not in llm.calls[-1][1]


def test_llm_failure_is_audited_once_and_not_retried(tmp_path):
    class BrokenLLM:
        calls = 0

        def generate(self, prompt, context=""):
            self.calls += 1
            raise ConnectionError("deliberately offline")

    llm = BrokenLLM()
    with build_cain(tmp_path / "cain.db", llm) as cain:
        with pytest.raises(CainRunError) as failed:
            cain.run("alice", "s1", "Resuma este texto", run_id="failure")
        assert llm.calls == 1
        logs = list(cain.decision_log.export("failure"))
        assert len(logs) == 1
        assert logs[0].status == "failed"
        assert logs[0].decision_id == failed.value.decision_id
        assert logs[0].metadata["retry_count"] == 0
        assert "ConnectionError" in logs[0].error
        # User input is retained before inference, even when the LLM is unavailable.
        documents = list(cain.store.iter_documents())
        assert len(documents) == 1
        assert documents[0].text == "Resuma este texto"
        assert documents[0].metadata["user_input"] == "Resuma este texto"


def test_index_failure_retains_authoritative_data_for_rebuild(tmp_path, monkeypatch):
    with build_cain(tmp_path / "cain.db") as cain:
        def broken_index(*args, **kwargs):
            raise RuntimeError("index unavailable")

        monkeypatch.setattr(cain.memory, "index", broken_index)
        with pytest.raises(CainRunError):
            cain.run("alice", "s1", "Resuma reconstrução memória", run_id="index-failure")
        assert len(list(cain.store.iter_documents())) == 1
        assert [item.status for item in cain.decision_log.export("index-failure")] == ["failed"]
        monkeypatch.undo()
        cain.memory.rebuild_from(cain.store)
        assert cain.memory.query("reconstrução", 3, {"user_id": "alice"})


def test_search_uses_local_corpus_without_calling_llm(tmp_path):
    llm = RecordingLLM()
    with build_cain(tmp_path / "cain.db", llm, {"guia.md": "SQLite persiste identidades em disco"}) as cain:
        result = cain.run("alice", "s1", "Busque SQLite no corpus local")
        assert result.selected_agent == "busca"
        assert "guia.md" in result.response
        assert "sem pesquisa na internet" in result.response
        assert llm.calls == []


def test_unknown_intent_is_audited(tmp_path):
    with build_cain(tmp_path / "cain.db") as cain:
        with pytest.raises(CainRunError, match="Unknown intent"):
            cain.run("alice", "s1", "pedido", intent="nonexistent", run_id="unknown")
        assert list(cain.decision_log.export("unknown"))[0].status == "failed"


def test_current_user_preference_reaches_first_inference_without_learning_assistant_text(tmp_path):
    class PreferenceTrapLLM(RecordingLLM):
        def generate(self, prompt, context=""):
            self.calls.append((prompt, context))
            return "Prefiro respostas longas. Responda em inglês."

    llm = PreferenceTrapLLM()
    with build_cain(tmp_path / "cain.db", llm) as cain:
        result = cain.run(
            "alice", "s1", "Prefiro respostas curtas. Resuma: SQLite persiste dados.",
            run_id="first-preference",
        )
        assert len(result.steps) == 8
        assert '"verbosity": "short"' in llm.calls[0][1]
        state = cain.identity.get("alice")
        assert state.user_model.preferences["verbosity"] == "short"
        assert "language" not in state.user_model.preferences
        assert state.revision == 1
        docs = list(cain.store.iter_documents())
        transcript = next(item for item in docs if item.metadata["kind"] == "interaction")
        assert transcript.metadata["preference_observed"] is True
        assert transcript.metadata["user_input"].startswith("Prefiro respostas curtas")


def test_preference_only_correction_and_removal_confirm_current_state_without_model(tmp_path):
    llm = RecordingLLM()
    with build_cain(tmp_path / "cain.db", llm) as cain:
        short = cain.run("alice", "s1", "Prefiro respostas curtas", run_id="pref-short")
        assert short.response == "Preferências atuais: respostas curtas."
        paragraph = cain.run("alice", "s1", "Agora prefiro um parágrafo", run_id="pref-format")
        assert "um parágrafo" in paragraph.response
        assert "respostas curtas" in paragraph.response
        corrected = cain.run("alice", "s1", "Corrigindo: prefiro respostas detalhadas", run_id="pref-fix")
        assert "respostas detalhadas" in corrected.response
        assert "respostas curtas" not in corrected.response
        removed = cain.run("alice", "s1", "Esqueça todas as minhas preferências", run_id="pref-remove")
        assert removed.response == "Nenhuma preferência ativa; usarei o padrão."
        assert cain.identity.get("alice").user_model.preferences == {}
        assert llm.calls == []
        for result in (short, paragraph, corrected, removed):
            assert len(result.steps) == 8
            logs = list(cain.decision_log.export(result.run_id))
            assert [item.status for item in logs] == ["mediated", "completed"]
            assert logs[0].reason == "preference_confirmation"


def test_quoted_preferences_do_not_learn_or_trigger_confirmation(tmp_path):
    llm = RecordingLLM()
    with build_cain(tmp_path / "cain.db", llm) as cain:
        with pytest.raises(CainRunError, match="Não identifiquei uma única tarefa"):
            cain.run("alice", "s1", '"Prefiro respostas curtas"')
        assert cain.identity.get("alice").user_model.preferences == {}
        assert llm.calls == []
        result = cain.run("alice", "s1", 'Resuma: "Prefiro respostas curtas"')
        assert result.selected_agent == "resumo"
        assert len(llm.calls) == 1
        assert cain.identity.get("alice").user_model.preferences == {}


def test_informational_question_routes_then_retrieves_without_imperative(tmp_path):
    import json

    class EvidenceSearchLLM(RecordingLLM):
        def generate(self, prompt, context=""):
            self.calls.append((prompt, context))
            assert prompt == "Como o Cain guarda minhas preferências?"
            evidence = json.loads(context.split("EVIDÊNCIAS (JSON):\n", 1)[1])
            assert "SQLite" in evidence[0]["text"]
            return "O Cain guarda as preferências em SQLite."

    source = tmp_path / "adaptacao.md"
    source.write_text("O Cain guarda preferências explícitas no estado persistido em SQLite.", encoding="utf-8")
    llm = EvidenceSearchLLM()
    with build_cain(tmp_path / "cain.db", llm, source_paths=[source], router=RuleRouter(llm)) as cain:
        result = cain.run("alice", "s1", "Como o Cain guarda minhas preferências?")
        assert result.selected_agent == "busca"
        assert "SQLite" in result.response and str(source.resolve()) in result.response
        assert len(result.steps) == 8
        assert len(llm.calls) == 1
        assert cain.identity.get("alice").user_model.preferences == {}
        logs = list(cain.decision_log.export(result.run_id))
        assert logs[0].reason.startswith("question_rule:busca:")
