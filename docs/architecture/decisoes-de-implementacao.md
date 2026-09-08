# Escolhas de engenharia nesta entrega

Data: 2026-09-07. Escopo: esqueleto e instrumento técnico; decisões de pesquisa abertas.

1. Python 3.11+, núcleo com biblioteca padrão; FastAPI apenas no extra `api`.
2. SQLite para identidade, sinais, transcritos e log. O índice é derivado.
3. `IdentityStore.iter_documents()` estende o contrato incompleto do ADR-0009:
   sem enumerar documentos/usuários, `rebuild_from(source)` não pode reconstruir tudo.
   A extensão fica na porta, sem consulta SQL vazando para os serviços.
4. Índice lexical local determinístico. Ele exercita o contrato e a reconstrução;
   não equivale à recuperação semântica ChromaDB. O adaptador vetorial fica pendente.
5. Busca trabalha sobre corpus local de demonstração. Código gera/analisa texto;
   nunca executa o texto gerado. Resumo usa a abstração de LLM.
6. Personalidade estável inicial, adaptação no-op e regras de roteamento são
   implementações provisórias identificadas por ADR-0006/0007/0008.
7. `FakeLLM` marca simulação na resposta. O adaptador Ollama usa `POST /api/generate`,
   `system`, `stream=false`, temperatura e seed configuráveis.
8. API local cria/fecha runtime por requisição para respeitar o uso de SQLite por thread.
9. A versão não inclui paralelismo de agentes, conversação agente-a-agente,
   criação dinâmica, retry/fallback, grafos ou streaming (ADR-0011).

Referências de integração: [Ollama generate](https://docs.ollama.com/api/generate)
e [FastAPI](https://fastapi.tiangolo.com/tutorial/first-steps/), consultadas em 2026-09-07.

## Condição científica

O pipeline A/B/C é um instrumento em desenvolvimento. Limitar caracteres não
estabelece igualdade de tokens. Roteamento validado contra regras de demonstração
não estima desempenho em linguagem natural fora desses casos. Memória factual,
estilo, adaptação e eficácia de delegação exigem instrumentos separados.
