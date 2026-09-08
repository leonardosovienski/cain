from cain.orchestrator.routing import RuleRouter
from cain.runtime import build_cain


def test_configured_router_can_classify_a_request_outside_rules_before_agent_generation(tmp_path):
    class Model:
        def __init__(self):
            self.calls = []

        def generate(self, prompt, context=""):
            self.calls.append((prompt, context))
            if len(self.calls) == 1:
                return '{"intent":"resumo","reason":"condensar a ideia informada"}'
            return "Uma função reúne operações."

    model = Model()
    with build_cain(tmp_path / "hybrid.db", model, router=RuleRouter(model)) as runtime:
        result = runtime.run("alice", "one", "Preciso de uma versão condensada deste texto: "
                             "Uma função reúne operações que podem ser chamadas novamente.")
        assert result.selected_agent == "resumo"
        assert len(model.calls) == 2
        records = list(runtime.decision_log.export(result.run_id))
        assert records[-1].reason.startswith("llm_classifier:")
