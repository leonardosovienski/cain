"""Small shared normalization utility, with no backend dependencies."""

import re
import unicodedata


def tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return set(re.findall(r"\w+", "".join(c for c in normalized if not unicodedata.combining(c))))


RETRIEVAL_STOP_WORDS = tokens(
    "a o as os um uma uns umas e de da do das dos em no na nos nas para por com "
    "que qual quais como sobre eu voce me ao aos favor busque busca buscar pesquise "
    "pesquisa pesquisar encontre procurar procure consulte consultar quero gostaria "
    "pode poderia local corpus fonte fontes documentacao documentos "
    "responda resposta respostas somente apenas frase frases explique explicar "
    "converse comigo diga texto fornecido fornecida informacao informacoes"
)
