# Comparação de sistemas e decisões — 11/09/2026

Pesquisa de documentação oficial, repositórios e artigos, consultados nesta data.
As descrições externas são alegações dos autores, não resultados reproduzidos aqui.
Não executamos sistemas de trading, contratamos APIs nem baixamos modelos.
O objetivo comparável do Cain é recuperar evidências admitidas e preservar contexto,
não prever preços ou executar estratégias. Nenhum LLM isolado foi tratado como aplicação.

## Sistemas de domínio

| Sistema / fonte primária | Problema e função | Cain existente / lacuna pertinente | Custo, dependência, licença e risco | Decisão e verificação necessária |
|---|---|---|---|---|
| [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot), [NOTICE](https://github.com/AI4Finance-Foundation/FinRobot/blob/master/NOTICE) | Aplicação de análise financeira com agentes, dados e relatórios | Cain possui recuperação e referências; falta ligação reproduzível de todos os produtores | Apache-2.0; LLMs, ferramentas financeiras e APIs com condições próprias; dados comerciais não herdam licença do código | **Adaptar** separação entre aquisição e análise: exportadores explícitos, hash e referência; aceitar somente se três percursos reais preservarem estados |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | Fluxos colaborativos de análise financeira e decisão | Cain já tem abstração de provider; debate entre agentes não resolve uma lacuna demonstrada de L0 | Apache-2.0 conforme repositório consultado; múltiplas chamadas e fontes; variação de resultados e risco de decisão sem suporte | **Rejeitar** adoção do executor/debate nesta etapa; futura avaliação exigiria ganho de suporte em corpus independente e orçamento igual |
| [Qlib](https://github.com/microsoft/qlib) + [RD-Agent](https://github.com/microsoft/RD-Agent) | Plataforma quantitativa e automação de pesquisa sobre dados/modelos | O equivalente funcional está nos produtores; Cain conserva relatos e revisões | MIT nos repositórios; ambientes científicos, dados, execução de código e LLMs; custo computacional não medido neste host | **Adiar** automação de pesquisa; reabrir só com preflight do produtor, autorização e protocolo próprio. Não duplicar evaluator no Cain |
| [CryptoTrade](https://arxiv.org/abs/2407.09546) | Agente de trading cripto que combina informação on-chain e off-chain e reflexão | Cain não calcula alpha; estados Crypto já vêm do produtor | Artigo não estabelece sozinho licença de reutilização do código/dados; LLM, séries e notícias; contaminação temporal e custos de execução | **Avaliar** apenas como referência metodológica futura; nenhuma transferência de resultado econômico. Reflexão livre não promove memória a evidência |
| [Polymarket Agents](https://github.com/Polymarket/agents) | Framework com conectores de mercados de eventos, RAG, notícias e ordens | Cain possui evidência local e recuperação; não precisa de carteira nem executor | MIT; repo arquivado em 11/05/2026, Python 3.9 indicado, carteira/API/LLM; manutenção e exposição financeira | **Rejeitar** dependência e execução. Metadados de resolução seriam necessários a eventual acervo desse domínio, que não integra os três produtores atuais |
| [FutureSearch](https://futuresearch.ai/iterating-on-a-forecaster/), [BTF](https://arxiv.org/abs/2506.21558) | Forecasting com corpus temporalmente congelado e avaliação de previsões | Cain já separa recepção de disponibilidade histórica; faltava avaliação PT/EN conjunta dos três acervos | Serviço comercial; não assumir licença OSS ou preço zero; acesso a benchmark/corpus depende dos termos; vazamento temporal é risco central | **Adaptar** protocolo prévio e agrupamento de variantes. Nesta entrega mede recuperação atual, sem alegar pastcasting válido |
| [LLM-SoccerArena](https://arxiv.org/abs/2607.24573) | Benchmark prospectivo de previsões esportivas | Cain consulta o registro Brasileirão; não gera previsões autorizadas | Artigo/benchmark não equivalem a licença de dados ou ferramenta instalável; LLM e coleta prospectiva; resultados dependem de resolução e corte | **Adiar** avaliação preditiva. Aceite futuro requer previsões lacradas antes dos jogos e protocolo do produtor; não executar holdouts protegidos |

Ações envolvem retornos, universo e custos; cripto acrescenta venues e dados on-chain;
esportes têm eventos, horizontes e regras de resultado; contratos de previsão têm
preço, liquidez, custos e regra de resolução. Acertar uma probabilidade não demonstra
lucro executável, nem permite transportar um resultado entre esses domínios.

## Componentes gerais

| Componente / fonte | Oferta e Cain existente | Lacuna / decisão | Custos, licença, riscos e aceite |
|---|---|---|---|
| [Haystack](https://github.com/deepset-ai/haystack) | Pipelines modulares de recuperação, ferramentas e geração; Cain já tem retriever lexical/híbrido e provider substituível | **Avaliar** como baseline ampliado, sem substituição agora | Apache-2.0; dependências e infraestrutura dos componentes escolhidos. Exigir ganho >=10 pontos percentuais de suporte factual em episódios independentes, sem piora de acesso revogado, mesmo corpus/orçamento |
| [Graphiti](https://github.com/getzep/graphiti) | Grafo temporal com proveniência; Cain já preserva revisões, supersedes e tempos desconhecidos | **Adiar** extração de entidades/relacionamentos; corpus e utilidade ainda pequenos | Apache-2.0 na versão consultada; backend de grafo, embeddings e extração; inferência de relações pode confundir narrativa e fato. Aceite exige perguntas relacionais reais, sem inventar validade temporal |
| [LangGraph](https://github.com/langchain-ai/langgraph) | Orquestração durável; Cain 0.4.3 já tem resultado durável e recibos idempotentes | **Adiar** troca de orquestrador; **adotar** fechamento da recuperação completa dos documentos externos | MIT no núcleo; serviço/hosting têm termos separados. Migração sem benefício acrescenta risco aos IDs e às transações. Aceite: restaurar documentos, identidades e consultas em destino novo |
| [Phoenix](https://github.com/Arize-ai/phoenix) | Observabilidade, avaliações e datasets; Cain já registra recibos, hashes, falhas e metadados de geração | **Adiar** servidor de observabilidade; manter relatórios locais reproduzíveis | ELv2 (source-available; não tratar como licença permissiva OSS); OpenTelemetry e serviço próprio; risco de exportar conteúdo sensível. Aceite futuro: diagnóstico mais rápido medido e redação de dados validada |
| [W3C PROV](https://www.w3.org/TR/2013/NOTE-prov-overview-20130430/) | Modelo de proveniência; Cain já separa origem, inputs, exportação e recepção | **Adaptar** disciplina de origem nos novos exportadores; não declarar conformidade PROV | Documento normativo, não runtime; sem dependência nova. Validar hashes/offsets e não confundir fonte com autor autenticado |

## Lotes selecionados

1. Raízes de importação por usuário/projeto/acervo: política v2, mantendo leitura v1.
   Evita colocar publicações Stocks/Brasileirão dentro da pasta Crypto ou admitir C:\ inteiro.
   Não altera o contrato ResearchSnapshotV1 nem a identidade das revisões.
2. Exportadores stdlib pertencentes a Stocks e Brasileirão, com relatório permitido,
   hash explícito, fonte commitada, releitura e recusa de sobrescrita. Validação canônica
   continua no consumidor; a serialização no produtor não é um segundo validador.
3. Backup completo: snapshots SQLite, documentos verificados, política e manifesto.
   Cada banco é consistente separadamente; não prometer snapshot atômico entre bancos.
4. Avaliação de recuperação dos três acervos com perguntas PT/EN e IDs explícitos.
   Sem mudança de modelo, ranking ou memória nesta entrega. Não justificar ganho semântico
   com um teste de transporte nem contar traduções como episódios independentes.

Critérios de engenharia: estados e IDs intactos, referências resolvíveis, importação
idempotente, revogação e isolamento preservados, consulta com raízes indisponíveis,
backup/restauração e wheel instalado fora do checkout. Zero dependências de runtime novas.
O custo é armazenamento local de snapshots e execução CPU/SQLite; nenhum preço de API
foi estimado sem consumo. Consulta offline é benefício funcional, não vantagem universal
sobre RAG. Utilidade comparativa e validação econômica permanecem conclusões separadas.
