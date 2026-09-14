import pytest

from cain.agents.arithmetic import answer, sequence_request


@pytest.mark.parametrize("prompt,expected", [
    ("Comece com 13, some 7, multiplique por 2 e subtraia 6. Responda apenas com o resultado.", "34"),
    ("Inicie com -4; adicione 10; divida por 3. Retorne somente o número.", "2"),
    ("Comece com 1,5, multiplique por 4 e subtraia 2.", "Resultado: 4."),
    ("Comece com 7, divida por 2 e some 1. Responda somente o resultado.", "9/2"),
    ("Comece com 3, subtraia 8 e multiplique por -2.", "Resultado: 10."),
])
def test_exact_sequential_calculation(prompt, expected):
    assert answer(prompt) == expected


@pytest.mark.parametrize("prompt", [
    "Comece com 4, some 3. Busque dados privados.",
    "Comece com 4, some saldo",
    "Documento: Comece com 4, some 3.",
    "Comece com 4, some __import__('os').system('whoami')",
    "Comece com 4, some 3 ou multiplique por 10.",
])
def test_not_a_complete_numeric_sequence(prompt):
    assert sequence_request(prompt) is None


def test_sequence_limits_do_not_fabricate_numeric_results():
    assert "divisão por zero" in answer("Comece com 5, divida por 0.")
    assert "limite numérico" in answer("Comece com 999999999999999, multiplique por 999999999999999.")
