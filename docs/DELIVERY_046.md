# Cain 0.4.6 — capacidades locais de análise

11/09/2026. Fecha os blocos técnicos selecionados no pedido reiterado:
streaming, imagem, busca no L0, relações citadas, debate, workflows retomáveis,
playground, traces e MCP. [ADR 0015](adr/0015-local-agent-capabilities.md)
registra o aceite anterior à implementação e
[protocolo PT/EN](../evaluation/agent-capabilities-20260911.json) os casos prévios.

## Uso na interface

Abra `C:\CAIN\ABRIR_CAIN.cmd`, http://127.0.0.1:8877. Em **Pesquisa · L0 Historian**,
use usuário leo/projeto Geral e um acervo: crypto, stocks ou brasileirao.
Preencha a pergunta e, quando pertinente, a identidade da fonte. Os novos
comandos usam esses campos; os filtros estado/texto pertencem à consulta literal.

- **Buscar pela pergunta** oferece ranking lexical; a opção semântica acrescenta
  embeddings locais. O score não é probabilidade e não traduz a evidência original.
- **Extrair relações com fontes** propõe sujeito/relação/objeto com citação exata.
  Resposta não sustentada é recusada ou produz abstenção. Não altera o grafo factual.
- **Criar fluxo de análise e debate** salva inspeção, busca, relações, suporte,
  crítica e síntese. Execute uma etapa ou todas; reabra em **Fluxos salvos**.
  Etapas concluídas não se repetem. O cancelamento descarta resultados em voo.
- **Laboratório local** aceita texto e uma imagem PNG/JPEG/WebP de até 2 MB e
  4.194.304 pixels. Lista modelos instalados, transmite tokens, distingue término
  e interrupção. A imagem é processada localmente; não é importada como evidência.

Debate usa papéis do mesmo modelo; não são votos de especialistas independentes.
A comparação/linha do tempo/grafo de proveniência da versão 0.4.5 continua disponível.

## CLI e API

```powershell
C:\CAIN\CAIN_RESEARCH.cmd --collection crypto search "O que H6 informa?" --source-id H6
C:\CAIN\CAIN_RESEARCH.cmd --collection crypto search "O que H6 informa?" --source-id H6 --semantic
C:\CAIN\CAIN_RESEARCH.cmd --collection crypto entities "Quais relações são explícitas?" --source-id H6
C:\CAIN\CAIN_RESEARCH.cmd --collection crypto workflow "O que H6 permite concluir?" --source-id H6
C:\CAIN\CAIN_RESEARCH.cmd --collection crypto advance ID --approve-generation
C:\CAIN\CAIN_RESEARCH.cmd --collection crypto job ID
C:\CAIN\CAIN_RESEARCH.cmd --collection crypto trace ID
C:\CAIN\.venv\Scripts\cain-stream.exe "Descreva a imagem" --config C:\CAIN\work\research-capabilities-20260911\cain.toml --image C:\caminho\imagem.png
```

`jobs` lista, `cancel ID` cancela. `advance ID --recover --approve-generation`
recupera falha; execução interrompida sem recibo exige lease expirado de 600 s.
Não há garantia exactly-once da chamada ao modelo quando o processo morre antes
do checkpoint. Troca de corpus, política ou modelo exige um novo job.

API: POST `/research/search`, `/research/entities`, `/research/jobs`,
`/research/jobs/list`, `/research/jobs/{id}/read|advance|cancel|trace`;
GET `/assistant/models`; POST `/assistant/stream` com resposta NDJSON.
Contexto: user_id, project_id, collection. Geração no advance é explícita por
`approve_generation: true`. Não existe execução arbitrária de shell ou plugins.

## MCP local

```powershell
C:\CAIN\.venv\Scripts\cain-mcp.exe --db C:\CAIN\dados\research.db --policy C:\CAIN\config\research-policy.json --collection crypto --trusted-local-client
```

Cliente stdio MCP 2025-06-18: initialize, notifications/initialized, tools/list,
tools/call. Ferramentas research_query, research_search, research_inspect e
research_evidence. Processo tem escopo fixo, revalida política a cada chamada,
não fornece rede/shell nem alterações científicas. As publicações deste host
não autorizam divulgação externa; não registrar esse servidor em cliente que
envie resultados a LLM remoto. Nenhum cliente externo foi conectado.

## Instalação e recuperação

Código isolado: `C:\CAIN\work\research-capabilities-20260911`, branch
`feature/research-capabilities-20260911`. Pacote não editável em `C:\CAIN\.venv`.
O checkout `C:\CAIN\projeto` tem alterações concorrentes preservadas e não é
a origem deste wheel. Python e bancos dos produtores não foram alterados.

Ollama 0.34.0 standalone oficial em `C:\CAIN\runtime\ollama`; modelos em
`C:\CAIN\modelos`, loopback, cloud desligada, um modelo carregado e uma chamada
por vez. Qwen3.5:0.8b para texto e visão, Qwen2.5:3b disponível no seletor e
Qwen3-embedding:0.6b para recuperação. Timeout local de 240 s e contexto 8192.
O modelo menor foi escolhido por viabilidade neste host, sem alegar superioridade.
Não há chaves pagas. CPU Intel integrada e cerca de 8 GB RAM:
carregar/trocar modelos e processar textos extensos pode ser lento.

O extra `vision` adiciona Pillow. Wheels, probes, XML e recibos ficam em
`C:\CAIN\entregas\0.4.6` e `C:\CAIN\work`. Backup anterior em
`entregas\0.4.6\before-backup`, restauração ensaiada em `restore-check`.
Novas tabelas agent_jobs/agent_steps/agent_attempts ficam no research.db e entram
no backup existente. Não sobrescrever banco ativo ao testar restauração.

## Evidência e limites

O protocolo é de desenvolvimento, com seis variantes PT/EN de três grupos,
comparação de IDs/estados com consulta literal e citações recebidas verificadas.
Imagem vermelha sintética identifica transporte/inferência; não é benchmark.
Testes de fixtures verificam revogação, isolamento, concorrência, interrupção,
retomada, ausência de evidência, gramática, MCP stdio e backup.

A primeira execução real detectou incompatibilidade da gramática de strings
limitadas no Ollama 0.34.0/llama.cpp. Foram retiradas apenas as repetições de
maxLength da gramática; validação de tamanho, quantidade, conteúdo e referência
continua obrigatória após a geração. A referência da explicação foi restringida
por enum às referências admitidas, evitando erros ao copiar hashes longos em
modelos pequenos. A validação independente do resultado continua obrigatória.
Sem fallback para resposta simulada.

Nenhuma superioridade semântica, rentabilidade, previsão ou autoridade científica
é demonstrada por estes testes. Fontes admitidas permanecem a autoridade sobre
seus próprios estados; as saídas do modelo são propostas.

Referências técnicas: [Ollama generate](https://docs.ollama.com/api/generate),
[Windows](https://docs.ollama.com/windows),
[MCP stdio](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports),
[OTLP JSON](https://opentelemetry.io/docs/specs/otlp/).
