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
Após geração recusada, `abstain ID --reason "motivo"` registra explicitamente
uma abstenção e permite continuar. Na interface, atualize o estado e use
**Registrar abstenção nesta etapa e permitir continuação**. O texto recusado
é descartado e a tentativa falha permanece. Fluxo concluído não significa que
todas as gerações foram aceitas. model_calls soma recibos concluídos; chamadas
em tentativas falhas são desconhecidas, pois a falha pode ocorrer antes ou depois
da inferência.
Não há garantia exactly-once da chamada ao modelo quando o processo morre antes
do checkpoint. Troca de corpus, política, modelo ou protocolo dos prompts exige
um novo job. O protocolo atual é research-workflow/2; jobs anteriores podem
ser lidos/cancelados, mas não avançados com prompts diferentes.

API: POST `/research/search`, `/research/entities`, `/research/jobs`,
`/research/jobs/list`, `/research/jobs/{id}/read|advance|cancel|abstain|trace`;
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
envie resultados a LLM remoto. A interoperabilidade foi verificada com o SDK
oficial MCP 2.2.0 em processo local separado, sem serviço remoto.

## Instalação e recuperação

Código isolado: `C:\CAIN\work\research-capabilities-20260911`, branch
`feature/research-capabilities-20260911`. Pacote não editável em `C:\CAIN\.venv`.
O checkout `C:\CAIN\projeto` não é a origem deste wheel. Seu trabalho concorrente
foi publicado em `architecture/complete-20260911`, HEAD `2e9350c`, e permanece
preservado. A integração entre essas branches requer revisão própria; este lote
não trocou esse checkout. Python e bancos dos produtores não foram alterados.

Ollama 0.34.0 standalone oficial em `C:\CAIN\runtime\ollama`; modelos em
`C:\CAIN\modelos`, loopback, cloud desligada, um modelo carregado e uma chamada
por vez. Qwen3.5:0.8b para texto e visão, Qwen2.5:3b disponível no seletor e
Qwen3-embedding:0.6b para recuperação. Timeout local de 240 s e contexto 8192.
O modelo menor foi escolhido por viabilidade neste host, sem alegar superioridade.
Não há chaves pagas. CPU Intel integrada e cerca de 8 GB RAM:
carregar/trocar modelos e processar textos extensos pode ser lento.

Licenças dos modelos foram preservadas nos recibos locais: Qwen3.5:0.8b declara
Apache 2.0; Qwen2.5:3b declara Qwen Research License, sem presumir permissão
comercial. A resposta /api/show do embedding não traz licença; não tratá-la
como concessão. Os modelos não são redistribuídos no repositório.

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

Rodada inicial com gramática corrigida: quatro de seis explicações passaram;
Stocks EN truncou, Brasileirão PT propôs síntese sem citação e a extração H6
inventou palavras na citação. Todas foram recusadas. O protocolo /2 pede
citações curtas e literais e limita relações a duas por chamada; a rodada
seguinte usa os mesmos casos e permanece avaliação de desenvolvimento.

Na repetição /2, as seis explicações PT/EN passaram com uma citação exata cada;
ranking lexical/híbrido manteve IDs/estados nos seis filtros. Fonte ausente
produziu abstenção com zero chamadas. Não foi avaliado ganho de ranking sem
filtro de identidade, nem superioridade sobre outro modelo. A extração H6
continuou recusada por suporte inexato; consta em real-evaluation-bounded/report.json.
No relatório simples de Stocks, extração e suporte passaram; crítica e síntese
sem citação foram recusadas e receberam abstenção explícita no teste de recuperação.
Portanto, ainda não há demonstração de debate autônomo confiável neste modelo.

MCP real: quatro ferramentas listadas e consulta H6 validada pelo cliente
oficial. Exportação OTLP: IDs hexadecimais conferidos e mensagem validada pelos
tipos protobuf oficiais 1.44.0 após conversão de representação dos IDs.
Nenhum coletor de traces externo recebeu dados.

Nenhuma superioridade semântica, rentabilidade, previsão ou autoridade científica
é demonstrada por estes testes. Fontes admitidas permanecem a autoridade sobre
seus próprios estados; as saídas do modelo são propostas.

Referências técnicas: [Ollama generate](https://docs.ollama.com/api/generate),
[Windows](https://docs.ollama.com/windows),
[MCP stdio](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports),
[OTLP JSON](https://opentelemetry.io/docs/specs/otlp/).
