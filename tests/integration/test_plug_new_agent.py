import pytest

from cain.agents import Capabilities
from cain.common import Message
from cain.runtime import build_cain


class UppercaseAgent:
    def describe(self) -> Capabilities:
        return Capabilities("maiusculas", ("uppercase",), "Transformação determinística sem LLM")

    def handle(self, message: Message) -> str:
        return message.payload.upper()


def test_plug_new_agent_without_changing_core(tmp_path):
    with build_cain(tmp_path / "cain.db") as cain:
        cain.registry.register(UppercaseAgent())
        result = cain.run("alice", "s1", "olá mundo", intent="uppercase", run_id="plugin")
        assert result.response == "OLÁ MUNDO"
        assert result.selected_agent == "maiusculas"
        assert len(result.steps) == 8
        assert list(cain.decision_log.export("plugin"))[-1].selected_agent == "maiusculas"
        with pytest.raises(RuntimeError, match="frozen"):
            cain.registry.register(UppercaseAgent())
