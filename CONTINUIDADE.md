# Continuidade do CAIN

## Checkpoint local para o próximo chat — 14/09/2026

**Ponto de retomada:** branch `checkpoint/conversa-v2-parcial-20260914`, derivada de `main` em `3f88a2535f08c70bce561cd3822e7558cebec326`. O commit de checkpoint preserva a composição acumulada, não é release nem aprovação integral. Obtenha seu SHA com `git rev-parse checkpoint/conversa-v2-parcial-20260914`. Não houve merge, push, instalação ou promoção. A instalação principal não foi atualizada por esta continuação nem por este fechamento. Os relatos anteriores abaixo são históricos e não descrevem a branch atual.

Comece pelo [relatório da continuação, matriz das 36 famílias e reversão](docs/CONTINUACAO_CONVERSA_20260914.md), usando a [avaliação v2 anterior](docs/EVALUACAO_V2_20260914.md) como baseline. Este fechamento fez somente revisão para commit, conferência de hashes/ZIP e documentação; não executou correções, testes de comportamento, inferências ou builds.

**Origem do material versionado.** Havia 24 arquivos alterados/não rastreados antes da continuação; o fechamento encontrou 31. Comparação com `R/baseline.json`: 18 preservados sem mudança naquela continuação, seis com trabalho anterior mais continuação, sete adicionais em relação ao baseline (inclui arquivos antes limpos). Não atribuir tudo ao último ajuste:

- Preexistentes: catálogo de hipóteses (`tools/hypothesis_sources.json`, `tools/prepare_hypothesis_catalog.py` e teste); revisão de pesquisa em `src/cain/research/{analysis,grounding,workflows}.py` e teste de integração; executores/catálogos/gabaritos v2 e teste de literalidade; documentação de cobertura e avaliações anteriores.
- Continuação de conversa: `src/cain/agents/{__init__,arithmetic}.py`, `src/cain/orchestrator/{__init__,routing}.py`, contagem de geração em `src/cain/evaluation/v2.py`, testes de roteamento, sequência e executor. `routing.py`, executor e seu teste incluem também trabalho anterior. A pesquisa preexistente faz parte do wheel testado, mas não foi corrigida pela mudança de conversa.
- Documentação: relatório da continuação, referências na v2, índice, instalação e esta continuidade. Neste fechamento somente este ponto de entrada e `.gitattributes` foram atualizados; relatórios e recibos anteriores não foram reescritos. A regra Git preserva os bytes dos três catálogos JSON, evitando normalização CRLF/LF que mudaria seus hashes. Não altera código ou conteúdo dos catálogos. O checkpoint contém os 31 arquivos acumulados mais esse metadado Git.

**Melhora demonstrada e pendências.** Preservação do payload completo, contrato de classificação, cálculo limitado de sequências e extração no agente de resumo melhoraram cópia educada, multiplicação, três linhas, extração e episódios naturais de memória. Declaração/recordação passaram a ser exercitadas, inclusive entre sessões; isso não aprova memória irrestrita. Continuam abertas retificações/continuações recusadas, contexto ausente no classificador para parte das perguntas referenciais, cópia literal com aspas extras, JSON com cercas, M11 com documento da entidade errada e qualificações indevidas. M04 também mostrou recusa semântica apesar de contexto na geração.

| Evidência anterior reaproveitada, sem nova execução | Resultado e limite |
|---|---|
| Suíte offline final e Ruff | 768 passaram, 1 ignorado, 2 avisos; Ruff passou. Engenharia, não certificação semântica. |
| Regressão na instalação QA correta | 14 tentativas: 11 passam, 2 parciais, 1 falha. |
| Confirmação nova após congelamento | 14 tentativas: 6 passam, 3 parciais, 5 falhas. Mesmo agente elaborou/revisou; não independente/cega. |
| Interface real | 16 casos: 11 passam, 2 parciais, 1 falha e 2 erros nominais; 24/23/21 mensagens planejadas/enviadas/concluídas. |
| Pesquisa | Crypto/H4 extrapola ausência de resultado observável; Stocks não reconcilia histórico/H17 e contradiz exit code 2; Brasileirão ainda não qualifica corretamente hipótese/causa. Nenhum dos três aprovado integralmente. Brier permanece pendência separada. |

Tentativas inválidas continuam documentadas: primeira montagem QA com Bundle histórico de mesma versão, import/coverage defeituosos nessa montagem, repetição com codificação corrompida e ajuste inicial de B09 no agente errado. Não as retirar dos denominadores nem tratar a repetição corrompida como melhora. Fonte congelada: **72 arquivos conferidos sem diferença**, incluindo 70 arquivos do pacote iguais byte a byte ao wheel. Não houve alteração de código após os testes declarados nesta rodada; somente documentação no fechamento. O commit Git pode normalizar CRLF para LF em textos, sem mudar a fonte do pacote; a comparação por bytes fica registrada no recibo local do checkpoint.

No índice Git, os 70 arquivos do pacote e `pyproject.toml` mantêm os bytes congelados. `README.md` já estava armazenado em LF no Git e em CRLF no checkout congelado: diferença apenas de quebra de linha, registrada sem alterar esse arquivo. A primeira checagem estrita do índice detectou essa diferença documental; não é nova falha do produto nem validação de um build posterior.

**Identidade e montagem QA correta.** `R = C:/CAIN/work/conversation-v2-20260914`.

| Artefato | Identidade SHA-256 |
|---|---|
| Árvore da candidata `candidate-final-freeze.json` | `6a567dd387e66121a120c15a8c4ed1e21a402505f3b9d8405e9d94490073a747` |
| `R/wheel-final/cain_research-0.4.12-py3-none-any.whl` | `a7b7cfd4d240942150375ae0a6324c9ab9ce1b0dbea8639ccad057fa4e5e77d8` |
| Bundle 1.0.0 canônico | `7c5792e6573d55af92fd9b50cd9a2c357052b7673a61eef8abdaeaeef401ebee` |
| Snapshot 1.0.1 canônico | `5e62cdf6ea7790a9e4beb0b3dd874a9a40c54cbd97e69e5a8408e88f8f22ec1a` |
| ZIP sanitizado original da rodada | `f5ff503b50645d095b53d966979ca4127ef8fee385798ca0e0b93718513a63b2` |

Python instalado e testado: `R/installed-qa-matched/Scripts/python.exe`, instalação não editável fora do checkout; dependências em `C:/CAIN/entregas/stocks-main-integration-20260912`. Use os artefatos pelo hash, não apenas pelo número de versão. `R/matched-stack-freeze.json`, `R/canonical-dependency-artifacts.json` e `R/matched-pip-check.log` atestam a montagem. A identidade da árvore acima não é SHA do arquivo JSON nem commit Git. A versão textual 0.4.12 não identifica sozinha esta candidata. Modelo e limites efetivamente usados estão no relatório; nenhum modelo foi trocado.

**Reprodução já documentada, não executada neste fechamento.** Os comandos completos e suas condições estão em `R/COMMANDS.md`. O caminho correto usa `-X utf8`, `PYTHONDONTWRITEBYTECODE=1`, sem `PYTHONPATH` herdado, e o Python de `installed-qa-matched`. Foram usados `-m cain.evaluation.v2 serve --root R/qa-ui-matched` e `-m cain.evaluation.v2 run --root R/qa-ui-matched --run-id known-failures-utf8 --cases B06,M02,M04 --paths C --catalog R/known-failure-utf8-catalog.json --rubrics R/confirmation-final-rubrics.json`. São referências às execuções preservadas: uma retomada deve preparar outra raiz/run_id pelos executores existentes, sem sobrescrever estas pastas. Não reinicie QA ou principal apenas para ler este checkpoint. Os serviços QA próprios foram encerrados ao fim da rodada.

**Fora do Git, preservado somente no disco local:**

- Recibos originais da v2: `C:/CAIN/work/evaluation-v2-20260914`; continuação: `R/qa-*/runs/*/attempts.jsonl`, `R/qa-*/transport.jsonl` e `dispatch.jsonl`, `R/matched-research`, `R/matched-supplemental`, `R/ui-matched-evidence`, revisões manuais, freezes e diffs. Não mover nem sobrescrever. Os catálogos de confirmação gerados depois do congelamento e os scripts auxiliares locais permanecem em R; os executores e os catálogos-base v2 entram no Git.
- `R/CAIN_CONTINUACAO_CONVERSA_SANITIZADO.zip`: 48 arquivos, ZIP/JSON e 47 hashes internos conferidos neste fechamento. Inclui relatório, 127 tentativas sintéticas exportadas, manifestos, evidências de interface/pesquisa, comandos e patches. Não inclui este fechamento posterior nem bancos/configurações pessoais. **Permanece local; caminho não é anexo nem publicação remota.**
- Wheels, ambientes QA, acervo autorizado de teste, configuração/política QA, modelos e recibos privados não entram no commit. A reprodução integral depende desses artefatos locais e das fontes autorizadas; o Git sozinho não contém o acervo ou a instalação. Não conectar o catálogo QA à principal.
- Conferências deste fechamento: `C:/CAIN/work/checkpoint-conversa-v2-20260914`, com inventário por arquivo/origem/hash, estado antes/depois, revisão do índice e SHA do commit. Os recibos privados ficaram nas pastas originais. Não foi criado backup remoto nem feito push.

**Próximo incremento, ainda não iniciado:** corrigir o repasse de contexto autorizado para retificações, continuações e perguntas referenciais e, depois, verificar respostas completas. Reaproveitar casos conhecidos como regressões e preparar nova confirmação após congelar outra candidata. Preservar autorização, orçamento e rotas explícitas. Formato, recuperação e pesquisa continuam pendências próprias; não presumir que a mudança de contexto as resolva. Não reiniciar a avaliação v2 geral nem promover para a principal.

## Continuação de conversa — 14/09/2026

Correção parcial implementada e testada em QA novo, sem promoção: [relatório, matriz das 36 famílias, evidências e reversão](docs/CONTINUACAO_CONVERSA_20260914.md). Preservação do payload, contrato de classificação, sequência aritmética limitada, pergunta curta com contexto e formato no agente de resumo melhoraram os casos documentados. A confirmação ainda reprova capacidades; não se aprova conversa irrestrita, memória completa ou síntese dos predictors. O wheel testado permanece fora da principal. A instalação principal e seus bancos/configurações não foram alterados. Recibos completos: `C:/CAIN/work/conversation-v2-20260914`; pacote sanitizado e contagens no relatório. Próximo incremento: repasse de contexto autorizado em retificações/continuações no fallback, ainda não iniciado.


## Avaliação de produto v2 — 14/09/2026

Executado o mandato de avaliação v2 em QA separado: [relatório canônico, matriz das 36 famílias e reversão](docs/EVALUACAO_V2_20260914.md), recibos em `C:/CAIN/work/evaluation-v2-20260914`. A cópia do pacote instalado foi comparada com um candidato que altera somente o router. Pedidos literais com dois-pontos deixavam de chegar íntegros à classificação; a correção genérica fez o caso original passar 3/3 e funcionar na interface com reabertura de histórico. A confirmação separada passou em duas variantes e falhou na forma com “Por favor”; não houve ajuste posterior para aprovar esse conjunto.

Permanecem falhas de roteamento em tarefas básicas, recuperação irrelevante quando o fato está ausente e interpretação indevida de métricas. M01/M02/M03 falham antes de exercitar memória. Testes técnicos, controles de autorização e citações não aprovam a qualidade semântica do produto. O relatório distingue a cópia instalada, o candidato isolado e a revisão acumulada de pesquisa do checkout. **Nada desta rodada foi instalado ou publicado, e o catálogo ampliado continua somente em QA.** Os relatos abaixo preservam suas próprias datas e resultados.

Fechamento v2: **750 testes aprovados, 1 ignorado por privilégio de symlink e 2 avisos**; Ruff passou, wheel candidato conferido contra 70 arquivos do checkout. Os três casos reais concluíram `inspect/search/support`, uma inferência cada: Crypto parcial, Stocks reprovado e Brasileirão parcial. Citações literais e reabertura passaram separadamente. A v2 integral não está concluída: variantes/caminhos pendentes estão explícitos na matriz. Próximo incremento prioritário, não iniciado: roteamento e preservação do assunto nas tarefas cotidianas recusadas, com novo conjunto de confirmação; reconciliação temporal de pesquisa permanece pendente.

Instalado **0.4.12**, código `dfabf6dab05df1662e9882ebe1091236daa14724`, branch **main**, ambiente não editável `C:/CAIN/.venv`. Checkout: `C:/CAIN/projeto`; interface http://127.0.0.1:8877/; atalho `C:/CAIN/ABRIR_CAIN.cmd`. A proteção posterior de análise está instalada; veja [a entrega posterior](docs/ANALYSIS_GUARD_20260913.md). Recibos, backup e wheel desta instalação: `C:/CAIN/work/install-dfabf6d-20260913`. Health OK, 62 arquivos conferidos, 20 testes do pacote instalado aprovados; dados/configurações preservados. As avaliações semânticas abaixo descrevem a rodada anterior à proteção.

Leia [estado](ESTADO_DO_PROJETO.md), [cobertura dos projetos](docs/COBERTURA_PROJETOS_20260913.md) e [instalação](docs/LOCAL_INSTALLATION.md).

Ampliação posterior de hipóteses: preparador Snapshot e inventário explícito de 92 fontes no checkout, incluindo os 70 registros dos ledgers legados e documentos posteriores dos três predictors. Validação isolada em `C:/CAIN/work/hypothesis-catalog-20260913/final`; este acervo não foi conectado à principal. Contagens de documentos/trials não são totais de hipóteses únicas. Ver [escopo, testes, limites e reversão](docs/COBERTURA_PROJETOS_20260913.md#acréscimo-dos-registros-de-hipóteses--13092026).

Continuação autorizada: orçamento completo do contexto e seleção/cabeçalhos corrigidos no checkout, workflow 12, ainda sem instalação. Suíte de 703 testes mais dois adicionais aprovada, mas as respostas reais de Brasileirão/Crypto ainda têm erros de atribuição; não são aprovação semântica. Stocks teve timeout e, na repetição, saída rejeitada por tamanho, também com problema de leitura histórica. Ver [resultados por predictor](docs/COBERTURA_PROJETOS_20260913.md#correção-do-contexto-do-catálogo--continuação-autorizada-em-13092026) e recibos em `C:/CAIN/work/context-integration-20260913`. Não conectar o catálogo à principal a partir desse resultado parcial.

Última continuação autorizada: separação de identidades/linhas, títulos verificáveis entre partes da mesma publicação e diagnóstico do receptor fora do pedido ao modelo; workflow 14 no checkout, **sem instalação**. Suíte final: 709 aprovados, um ignorado. Duas rodadas reais dos três casos: Brasileirão melhorou, mas segue parcial; Crypto ainda inventa causalidade financeira a partir de risco de cota; Stocks ainda tem contradição temporal e atribuição incorreta de ressalva. Ver [matriz e reversão desta continuação](docs/COBERTURA_PROJETOS_20260913.md#separação-de-identidades-e-qualificações--continuação-de-13092026), recibos em `C:/CAIN/work/context-isolation-20260913`. Próximo incremento registrado, não iniciado; catálogo continua fora da principal.

## Revisão do checkout em 14/09/2026

Revisão crítica e teste ampliado em `C:/CAIN/work/review-full-20260914`, preservando o trabalho local anterior. Corrigidos decoder do catálogo, interpretação de títulos fora de blocos de código, preservação integral/omissão explícita de propostas anteriores e identificação das citações. O limite de texto permanece validado no CAIN, sem induzir corte pelo schema do modelo. Versões retidas: seletor 7, prompt 13, workflow 18. A tentativa de mudar a instrução das etapas foi rejeitada por regressão real, apesar de passar nos testes.

Suíte retida: **719 aprovados, 1 ignorado, 2 avisos**; Ruff e verificação do wheel isolado aprovados. API, interface, CLI/MCP, documentos, preferências, conversa, streaming e exemplo visual foram exercitados. Conversa livre ainda teve generalização estatística indevida. Não há certificação semântica integral. Ver a [matriz por predictor](docs/COBERTURA_PROJETOS_20260913.md#revisão-crítica-e-teste-ampliado--14092026) e o [teste amplo](docs/TESTE_INTEGRAL_20260912.md#revisão-e-teste-ampliado--14092026), que distinguem falhas reais, testes sintéticos e verificações estáticas.

**Nada desta revisão foi instalado na principal**, e o catálogo de 92 fontes permanece somente em QA. Dados, configuração, política e módulos instalados preservados; produtores e Ecosystem inalterados. Reversão por hunks comparados com `review-full-20260914/baseline`, sem restaurar bancos ou apagar histórias. O wheel correspondente ao checkout é `dist-reviewed`; `dist-final` pertence à tentativa rejeitada. Não instalar nenhum deles automaticamente.

Resultado final dos casos reais: **Brasileirão parcial**, com repetição das três redações; **Crypto reprovado no conjunto das etapas**, embora a síntese atenda ao núcleo selecionado de H4; **Stocks reprovado**, mantendo contradição temporal e sem síntese aceita (1.092 caracteres recusados pelo teto de 1.000). Nove chamadas reais na última rodada; checkpoints/citações literais conferidos separadamente da interpretação. Próximo incremento prioritário, **não iniciado**: reconciliação temporal e seleção de qualificações, começando por Stocks e reexecutando os três gabaritos. A documentação canônica acima preserva as demais lacunas.

## Resultado da instalação principal anterior à revisão

O CAIN **não recebe os projetos inteiros**. Crypto tem 15 registros de dois arquivos; Stocks, um status e um acervo Bundle com um pacote/duas entidades; Brasileirão, três registros de um relatório. Existem acervos adicionais com sobreposição. As contagens e todos os itens desses seis acervos foram auditados. A interface, API `/research/coverage` e CLI `research ... coverage` agora separam Snapshot, Bundle, conteúdo recebido, referências e geração permitida.

Três Bundles adicionais foram importados somente em QA: 36 entidades, 19 artefatos, 14 materializados com hashes corretos e cinco somente referenciados. Não foram conectados à política principal. Os próprios manifestos são parciais e restringem geração. Nenhum produtor foi alterado.

Três workflows de seis etapas concluíram e reabriram os checkpoints. A redação não foi inteiramente aprovada: Crypto e Stocks tiveram extrapolações; Brasileirão tratou o texto de uma hipótese como resultado estabelecido apesar do estado bloqueado. Essa falha permanece aberta. Nove inferências redigiram as etapas; outras três explicações selecionaram trechos, sem síntese livre irrestrita. Os módulos de geração permaneceram byte a byte iguais entre 0.4.11 e 0.4.12.

## Preservação e evidências

Dados em `C:/CAIN/dados`; política `C:/CAIN/config/research-policy.json`; configuração `C:/CAIN/projeto/cain.toml`. Modelo qwen3.5:4b, Ollama 0.34.0, temperatura 0, seed 42, think=false, contexto 8192, num_predict 768 e timeout 240 s preservados. As preferências de leo foram mantidas.

Rodada atual: `C:/CAIN/work/coverage-projects-20260913`. Backup de bancos/configuração/wheel 0.4.11 em `baseline`; ensaios separados em `isolated`, `audit` e `bundle-candidates`. Não restaurar esses snapshots sobre dados atuais. O wheel final está em `release`, com hash no mapa de instalação.

Recibos principais: `coverage-audit.json`, `bundle-candidates/report.json`, `full-workflows.json`, `semantic-review.json`, `workflow-installed-readback.json`, `installed-api.json`, `installed-cli.json`, `ui-verification.json`, `preservation.json`, `git-publication.json` e `ci-final.json`.

Antes de retomar, conferir Git local/remoto e `/health`. Para ampliar acesso aos produtores, definir os novos artefatos/exportações; leitura de um recorte não significa acesso aos bancos ou compreensão de todo o projeto. Não alterar lacres, restrições ou hipóteses para obter aprovação. Para corrigir a redação, usar o caso Brasileirão já registrado como regressão semântica.

Histórico: [0.4.11](docs/LLM_REAL_20260913.md) e [0.4.10](docs/LLM_FIX_20260913.md). Recibos anteriores em `C:/CAIN/work/qa-real-20260913` permanecem preservados. A antiga contagem de “dois Bundles” foi corrigida para duas entidades de um pacote. Testes técnicos não certificam conclusões científicas/econômicas.
