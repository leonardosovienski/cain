# Inventário ampliado de capacidades — 11/09/2026

## Atualizacao 0.4.7

[Entrega atual](../DELIVERY_047.md): arquitetura integrada, campos JSON/tabelas
literais, debate com trechos enderecaveis, interface legivel e avaliacao separada.
A matriz atual de cobertura esta nessa entrega; os diagnosticos abaixo sao historicos.

## Atualização 0.4.6

As tabelas seguintes preservam o diagnóstico da versão 0.4.5. O novo pedido
reabriu seus adiamentos técnicos; a [entrega 0.4.6](../DELIVERY_046.md) acrescenta:

| Família | Implementação atual |
|---|---|
| Streaming e multimodal | NDJSON incremental com terminal obrigatório, interrupção, PNG/JPEG/WebP local limitado; seletor de modelos instalados e CLI |
| Recuperação | Ranking lexical e híbrido no acervo L0, IDs e permissões preservados; embeddings somente para fontes admitidas à inferência |
| Entidades e relações | Extração proposta por LLM, referências e trechos exatos, sujeito/objeto presentes na citação; sem promoção a fatos |
| Debate | Etapas suporte, crítica e síntese com fontes; papéis do mesmo modelo, sem alegar agentes independentes |
| Workflows | Seis ferramentas registradas, checkpoints SQLite, retomada, cancelamento, recuperação explícita, identidade de modelo/corpus fixada |
| Observabilidade | Tentativas, falhas, duração, hashes e exportação OTLP JSON local sem conteúdo das fontes; nenhum coletor externo conectado |
| MCP | Servidor stdio 2025-06-18, quatro ferramentas de leitura, usuário/projeto/acervo fixos; verificação em processo separado |
| Runtime | Ollama Windows instalado e três modelos locais; texto, imagem e embeddings exercitados com inferência real |

Isso fecha os blocos pertinentes selecionados, sem transformar o Cain em
corretora, executor científico dos produtores, plataforma distribuída ou cópia
integral dos produtos. Ontologia automática aceita como verdade, feeds pagos,
execução de capital e benchmarks prospectivos não foram autorizados por este lote.

## Diagnóstico histórico 0.4.5

Pedido: examinar os recursos dos rivais e ampliar a implementação no Cain.
Este inventário cobre as famílias anunciadas nas fontes primárias abaixo,
consultadas novamente nesta rodada. Não é uma auditoria de cada opção de cada
produto, nem comprova as alegações comerciais ou científicas dos autores.

## Domínio e análise

| Fonte primária | Capacidades anunciadas | Situação no Cain / impedimento concreto |
|---|---|---|
| [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | Agentes de dados, análise, modelagem, síntese e relatório; debate; valuation DCF/DDM/LBO/comparáveis/WACC/Monte Carlo; dados de mercado e SEC; interface desktop | Exportadores e referências já disponíveis. Dossiê local e comparação de revisões adicionados nesta rodada. Valuation, mercado ao vivo e debate não implementados: precisam de fontes/modelo e de projeto analítico próprio; não correspondem a consultar relatórios recebidos. A oferta desktop anunciada exige macOS Apple Silicon; este host é Windows. V2 é anunciada sem código aberto e V3 em desenvolvimento; não podem ser copiadas como pacote OSS disponível. |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | Análise fundamentalista, sentimento, notícias, indicadores técnicos, debate bull/bear, decisão e gestão de risco; execução simulada | Consulta e explicação dos registros existentes. Não há feed de preços, redes sociais ou indicadores admitido no contrato atual. Debate real depende de modelo inexistente neste host. Execução e alteração de estratégias continuam fora da autorização original. |
| [Qlib](https://github.com/microsoft/qlib), [RD-Agent](https://github.com/microsoft/RD-Agent) | Dados quantitativos, modelos, pesquisa de fatores, backtests; loops de proposta/código/avaliação, extração de fatores de relatórios | Produtores são responsáveis por esses processos. Cain preserva resultados publicados. Não duplicar seus runtimes, executar holdouts ou reabrir hipóteses com a autorização de consulta. |
| [CryptoTrade](https://arxiv.org/abs/2407.09546) | Informação on-chain/off-chain e reflexão para trading | Não há essas séries admitidas no Cain. Relatos Crypto podem ser consultados; reflexão não é uma nova evidência. Artigo não basta para estabelecer licença de um runtime reproduzível. |
| [Polymarket Agents](https://github.com/Polymarket/agents) | Conexão ao mercado, RAG de notícias, decisões e ordens | Framework arquivado na consulta anterior; não instalado. Carteira, ordens e novo domínio de contratos não estão autorizados. Fontes externas exigem admissão própria. |
| [BTF](https://arxiv.org/abs/2506.21558) | Avaliação de forecasting com corpus temporal congelado | Protocolos e avaliações de recuperação existem no Cain. Não equivalem a forecasting: corpus histórico sem vazamento e resolução independente não estão disponíveis. |
| [LLM-SoccerArena](https://arxiv.org/abs/2607.24573) | Benchmark de previsões esportivas em eventos reais | Estados do Brasileirão disponíveis. Previsões prospectivas e resultados lacrados continuam responsabilidade do produtor; testes de software não substituem o protocolo. |

## Memória, execução e ferramentas

| Fonte primária | Capacidade | Cain antes | Ampliação / limite |
|---|---|---|---|
| [Graphiti](https://github.com/getzep/graphiti) | Grafo de entidades e relações | Arquivo e revisões preservados | Grafo de proveniência explícita adicionado: revisão → publicação/evidência/revisão substituída. Não é extração automática de entidades. |
| Graphiti | Histórico temporal e consultas sobre validade | Datas e supersedes preservados | Linha do tempo tipada, datas desconhecidas separadas, comparação explícita e detecção de ciclos adicionadas. Não inferir intervalos de validade ausentes. |
| Graphiti | Ontologias aprendidas e extração por LLM | Não disponível | Modelo local ausente; evidência e avaliação relacionais independentes ainda necessárias. |
| Graphiti | Busca semântica, lexical e travessia de grafo | Busca lexical/híbrida em documentos; filtros no L0 | Navegação das relações explícitas no dossiê. Não introduz ranking semântico no L0. |
| [LangGraph](https://github.com/langchain-ai/langgraph) | Execução durável, memória curta/longa | Sessões, preferências, recibos e resultados persistidos | Mantidos; backup de documentos já entregue em 0.4.4. Não equivale a retomar cada passo de qualquer workflow LangGraph. |
| LangGraph | Inspeção humana de estado | Memória editável, histórico e referências | Dossiê e comparação oferecem novas inspeções. Alterações de estados científicos seguem proibidas. |
| LangGraph | Deployment e observabilidade de workflows | API/interface loopback | Métricas locais ampliadas. Não há serviço distribuído nem autenticação remota. |
| [Haystack](https://github.com/deepset-ai/haystack) | Pipelines modulares, roteamento, ferramentas e memória | Protocolos de agentes, router, retriever e provider | Mantidos; inspeção adicionada à API e CLI, sem troca de framework. |
| Haystack | Recuperação, ranking e preparação de contexto | Busca lexical/híbrida de documentos e evidência limitada | Sem novo modelo/ranking nesta rodada. Comparação independente necessária para alegar ganho. |
| Haystack | Hooks, monitoramento de chamadas, tokens e custos | Limites de entrada e metadados do provider | Duração, chamadas, hash de política/snapshot e contagens no dossiê. Sem estimativa fictícia de preço. |
| Haystack | Async, streaming, ferramentas concorrentes, multimodal e agentes de deep research | Não equivalentes no Cain | Não implementados nesta rodada. Exigem um lote de arquitetura e testes próprios; não são bloqueados somente por credenciais. |

## Avaliação, proveniência e diagnóstico

| Fonte primária | Capacidade | Cain / entrega |
|---|---|---|
| [Phoenix](https://github.com/Arize-ai/phoenix) | Tracing, diagnóstico, métricas | Recibos e metadados existentes; métricas de inspeção e hash do conjunto autorizado adicionados. Não é tracing distribuído/OpenTelemetry. |
| Phoenix | Datasets e experimentos versionados | Protocolos em Git, corpus e avaliação no Cain já existentes. Não foram convertidos ao formato Phoenix. |
| Phoenix | Playground, gestão de prompts, comparação de modelos | Prompts e parâmetros versionados, harness de qualidade existente. Execução real bloqueada por runtime/modelo ausente. |
| Phoenix | Agente de diagnóstico e servidor MCP | Não instalados. Exigem integração, revisão de acesso e teste próprios, além do modelo quando aplicável. |
| [W3C PROV](https://www.w3.org/TR/2013/NOTE-prov-overview-20130430/) | Origem e derivação | Hashes, fontes, offsets, origens e relações explícitas. Não declaramos conformidade formal ou identidade autenticada do publicador. |

## Decisão e custo

O lote implementado reabre parte das decisões de adiar Graphiti/Phoenix/relatórios:
usa os próprios dados e componentes do Cain, sem importar código dos rivais ou
adicionar dependências. Consome CPU e memória locais; limites explícitos recusam
saídas excessivas. Detalhes e aceite em ADR 0014.

Licenças da comparação anterior continuam registradas por produto. Apache/MIT
do repositório não concedem licença sobre dados comerciais, versões fechadas ou
serviços hospedados. Phoenix usa ELv2 na comparação consultada; não presumir
licença permissiva porque o README se apresenta como open source.

**Pendências não são recursos entregues.** Streaming, multimodal, MCP, extração
de entidades e workflows gerais não foram implementados. Não existe paridade
universal. A ausência do Ollama foi confirmada no caminho configurado
`C:\CAIN\runtime\ollama\ollama.exe`; nenhuma inferência real foi executada.
