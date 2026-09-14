# Avaliação de produto v2 — execução de 14/09/2026

Esta rodada implementa e executa o mandato `CAIN_PROMPT_FINAL_AVALIACAO_V2.md`. A avaliação encontrou uma falha corrigível na composição/seleção de rota para pedidos literais, mas **não aprova o CAIN como um todo**. A correção candidata não foi instalada. Resultados desta rodada não substituem nem apagam as avaliações anteriores.

## Referências e preservação

Checkout `C:/CAIN/projeto`, branch `main`, HEAD `3f88a2535f08c70bce561cd3822e7558cebec326`, com onze arquivos já modificados/não rastreados ao início. Esses arquivos estão identificados e copiados em `C:/CAIN/work/evaluation-v2-20260914/baseline`. A instalação não editável é CAIN 0.4.12, Python 3.12.14. A identidade por bytes inicial do pacote é `fc41867bf8912cc703f7d5f90efc414e8e46c0580e59b77246ad3b292a868ff4`; não se atribui ao pacote instalado o HEAD do checkout.

Nesta página, `R` significa `C:/CAIN/work/evaluation-v2-20260914`. Os recibos completos ficam somente nessa pasta local: não são corpus recuperável nem conteúdo a publicar. `baseline.json`, `isolation.json`, `live-inventory.json` e os manifestos por execução registram identidade e configuração. Bancos de avaliação, documentos, cache, logs e política ficam em `R/runtime` ou `R/candidate/runtime`; nenhum ensaio se baseia apenas em trocar o nome do usuário. As portas próprias são 8896 (API), 11436 (observador) e 11435 (Ollama). Não houve instalação, promoção, alteração de produtor ou ampliação de política principal.

Usou-se o modelo existente `qwen3.5:4b`, Ollama 0.34.0, temperatura 0, seed 42, think=false, contexto 8192, num_predict 768, orçamento de entrada 6500 bytes e timeout de provider 240 s. Busca híbrida usa `qwen3-embedding:0.6b`. Digests e opções efetivamente transmitidas estão nos recibos. A máquina tem aproximadamente 7,63 GiB de RAM; carregamento e paginação afetam a latência. Não houve comparação estatística controlada de desempenho, troca de pesos ou download de modelo.

## Desenho e instrumentos

O catálogo versionado e os gabaritos separados foram congelados antes da execução inicial. O catálogo cobre os IDs das 36 famílias; a presença de um ID não significa execução completa. Casos abertos passam por revisão manual de afirmações e fontes. Os verificadores automáticos de literalidade e JSON conferem conteúdo, tipos, chaves e terminadores; não removem espaços indiscriminadamente. Há controles positivos e negativos dos avaliadores. A revisão semântica foi feita pelo mesmo agente implementador, sem cegamento ou independência.

O executor reutiliza `cain.evaluation`, `quality._strict_json`, identificação do pacote e o runtime real. Os novos módulos são `v2`, `v2_replay`, `v2_integrity`, `v2_controls`, `v2_research` e `v2_utility`. Fixtures e gabaritos estão em `data/scenarios/evaluation-v2.json` e `data/probes/evaluation-v2-rubrics.json`; não entram no acervo do usuário. A execução real é opt-in; os testes comuns permanecem offline.

O observador armazena os bytes de entrada e saída do backend, hashes, opções, rótulos de caso/turno, falhas e duração. Não altera o pedido encaminhado. A revisão `v2-runner/2` acrescentou despacho prévio, identificação de requisição, detecção de observação incompleta e atestado de armazenamento na API QA. A contagem fica `unknown` quando o encerramento não permite comprová-la. O endpoint de atestado é instrumentação de QA, não funcionalidade disponível na principal. O instrumento inicial efetivamente carregado foi preservado em `R/instruments/v2-initial.py`; os recibos anteriores não são retroativamente descritos como produzidos pela revisão 2.

| Caminho | Execução comprovada | Limite |
|---|---|---|
| A — modelo direto | B03 três vezes e B04 uma vez, respostas corretas | Pedido direto difere da tarefa de classificação imposta pelo runtime |
| B — replay efetivo | Três entradas originais do classificador de B03, bytes preservados; novamente `clarify` | O processo inicial também repetiu três entradas de A; esses três controles extras não são contados como replay de C |
| C — runtime normal | API com roteamento automático, casos e episódios registrados; controles de persistência/autorização separados | Não foi forçada intenção para aprovar conversação; endpoints específicos de pesquisa não certificam roteamento do chat |
| D — interface | Navegador real contra a API QA, antes e depois | Apenas os casos explicitamente registrados; não equivale à cobertura de todos os controles visuais |

## Correção única de comportamento e causalidade

Antes da correção, `Responda apenas: AÇÃO-928` era reduzido a `responda apenas` na entrada do classificador. As três execuções de C foram recusadas; A respondeu corretamente nas três; o replay das três entradas efetivas voltou a produzir `clarify`. A falha demonstrada está na montagem/seleção de rota, não na incapacidade de copiar o literal.

O ajuste em `src/cain/orchestrator/routing.py` reconhece a forma genérica não vazia `responda/retorne/escreva/imprima apenas/somente: conteúdo` dentro das regras de conversa já existentes. Preserva proteção para pedidos incompletos e instruções concorrentes. Não contém os textos ou respostas dos casos. Nenhum prompt de geração, modelo, schema ou corpus foi alterado por esse ajuste.

Para isolar a causa, foi copiado o pacote instalado e substituído **somente** esse módulo (`R/candidate-package`). A comparação dos 55 módulos Python confirmou uma única diferença. A regressão executou novamente as 13 famílias iniciais, 17 tentativas. B03 passou 3/3; B06 continuou passando 3/3. M04 completou os dois turnos nesta rodada, mas a mudança não afeta esse caminho: não se atribui a melhora de um timeout à correção do literal.

O candidato foi congelado antes de elaborar a confirmação: `candidate-freeze.json`, hash do router `85921826bb630298466b73897fe946e25a492cc1fe136aefbd46b14621516792`. As duas novas formas diretas, incluindo quebra de linha, passaram. `Por favor, retorne somente: Boa viagem.` foi recusado. A confirmação **falhou no conjunto**; não houve novo ajuste para fazê-la passar. É evidência de alcance limitado, não confirmação independente de competência geral.

Outras falhas permanecem: cálculos e tarefas simples recusados pelo classificador, falsa relevância em recuperação de informação ausente e interpretação indevida de Brier. O classificador recebeu capacidade `conversa` e enum correspondente; a causa dessas recusas não é ausência dessa opção no schema. Não foi demonstrada causalidade suficiente para uma segunda correção nesta rodada.

## Integridade e limites dos controles

Os controles de A04/A09/A10/A11 e M07/M08 executam os métodos reais de pesquisa/armazenamento sobre fixtures lacradas e bancos descartáveis. Conferem supersessão explícita, chegada fora de ordem, idempotência, conflito com rollback, autorização, reabertura, cancelamento e revogação. Não chamam modelo. Isso não testa um crash de processo no meio de uma transação nem certifica segurança adversarial universal.

Os controles HTTP verificam precedência usuário → projeto → sessão → resposta, expiração futura e isolamento documental entre usuário/projeto. O teste não certifica adesão linguística da geração nem memória livre persistente não prometida pelo contrato. M12 executou a CLI real com backend deliberadamente indisponível em uma porta QA: erro explícito, término não zero, sem resposta de sucesso. Não houve desligamento da instalação principal nem teste de corte de streaming parcial.

Erros do avaliador foram retidos: a primeira verificação de cancelamento esperava uma exceção, embora o contrato retorne o job cancelado; a primeira expiração tentou registrar uma data passada, corretamente rejeitada; o primeiro subprocesso da CLI herdou `PYTHONPATH` do checkout. Os ensaios corrigidos estão em `integrity-installed-v2`, `http-controls-v2`/`http-controls-attested` e `backend-fault-installed`. Não contam como defeitos do produto nem como ensaios originais aprovados.

## Evidência, cobertura e conclusão

As matrizes finais e a verificação de preservação desta execução são registradas abaixo. Um caso aprovado não comprova todo o conhecimento de um predictor. O catálogo ampliado de 92 fontes continua em QA e não demonstra totalidade de hipóteses únicas ou exportação autenticada dos produtores. A data de ingestão não substitui a data da informação.

### Matriz das famílias básicas

“Falha operacional” é falha da tarefa nominal, com qualidade da resposta não avaliável; não é exclusão do denominador. “Passa no recorte” não aprova variantes não executadas. Baseline refere-se ao pacote instalado em QA; candidato refere-se à cópia com somente o router alterado.

| Família | Baseline C | Candidato C / revisão manual | Evidência e limite |
|---|---|---|---|
| B01 saudação | Passa | Passa | Determinístico, zero LLM; também D no baseline |
| B02 variantes | Não executado | `olá`, `opa`, `  BOM DIA  ` passam individualmente | `opa`: classificador + resposta real; outras duas determinísticas |
| B03 literal | Falha operacional 3/3 | Original passa 3/3; confirmação 2 passam, 1 falha | A 3/3 correto; B reproduz falha; D antes falha/depois passa, com recarga |
| B04 multiplicação | Falha operacional | Falha operacional | A responde 133; variante sem restrição não executada |
| B05 sequência aritmética | Não executado | Falha operacional | Classificador recusa; cálculo não exercitado |
| B06 JSON | Passa 3/3 | Passa 3/3 | `llm_text`, não schema imposto ao resultado; D passa e reabre |
| B07 três linhas | Não executado | Falha operacional | Sem resposta para conferir formato |
| B08 palavra proibida | Não executado | Falha operacional | Verificador diferencia palavra inteira de substring; isso não aprova o runtime |
| B09 extração | Não executado | Falha operacional | Contexto fornecido, porém tarefa recusada |
| B10 informação não fornecida | Passa no recorte vazio | Passa no recorte vazio | `retrieval_only`, ausência limitada às fontes configuradas |
| B11 regra fictícia | Não executado | Passa: 5 | LLM real; não afirma alteração da aritmética comum; variante comum não executada |
| B12 resumo | Passa | Passa | PT, três fatos e até 20 palavras; modelo real |

### Matriz das famílias médias

| Família | Execução e resultado | Camada / limite |
|---|---|---|
| M01 recordação | Baseline e candidato falham ao registrar a primeira declaração | Roteamento; memória posterior não avaliada |
| M02 atualização | Baseline e candidato falham na primeira declaração | Não comprova valor atual/anterior nem perda de memória |
| M03 distração | Candidato falha antes das cinco distrações | Episódio congelado registrado; não se contaram turnos não realizados |
| M04 continuidade | Baseline: primeiro turno correto, segundo timeout; candidato: ambos corretos | Diferença 3, custos 8/7,40, diferença unitária 0,60; sem causalidade atribuída ao fix |
| M05 preferência | Controles HTTP passam precedência e expiração | Estado efetivo real; adesão da geração a todos os escopos não executada |
| M06 persistência | Preferências e documento persistem e são consultados | Parcial: canário livre entre sessões não foi avaliado como memória natural |
| M07 outro usuário | Controles HTTP e serviço impedem acesso ao documento/acervo de outro usuário | Sem teste adversarial completo na interface; perfis locais não são autenticação remota |
| M08 outro projeto | Documento restrito não aparece no corpus do outro projeto | Contrato real exercitado; não presume fronteira para fontes globais compartilhadas |
| M09 fato/opinião | Falha operacional de roteamento | Sem resposta para avaliação semântica |
| M10 documento presente | Baseline e candidato passam no documento Cedral | Código/prazo e fonte corretos; recuperação literal, sem geração |
| M11 documento ausente | Baseline e candidato reprovados | Devolve Cedral quando perguntado Lunar, sem abstenção explícita; não é prova de dado fabricado ou vazamento |
| M12 indisponibilidade | CLI instalada em QA encerra com erro explícito e exit não zero | Falha induzida em porta fechada; interrupção de resposta parcial não executada |

### Matriz das famílias avançadas

| Família | Execução / estado | Limite obrigatório |
|---|---|---|
| A01 Crypto | Caso real H4 no arquivo QA; resultado detalhado na matriz por predictor abaixo | Consulta de pesquisa explícita; não certifica todo o projeto ou chat automático |
| A02 Stocks | Caso real de prontidão no arquivo QA; resultado abaixo | Histórico, prontidão pessoal e engenharia são qualificações diferentes |
| A03 Brasileirão | Caso real CLAIM-BR-MARKET-001; resultado abaixo | Hipótese bloqueada não equivale a comparação executada |
| A04 revisão | Controle de supersessão explícita passa com chegada fora de ordem | Conflito entre fontes sem relação de revisão não resolvido/não executado |
| A05 sem cabeçalho | Baseline: abstenção parcial, mas inventa qualificação de coluna; candidato: timeout | Reprovado/erro nominal; não aprovado por dizer que faltam dados |
| A06 com cabeçalho | Baseline e candidato reprovados semanticamente | “Probabilidade Brier”, regra binária universal e julgamento de precisão não sustentados |
| A07 recorte | Recuperação do documento sintético passa no recorte | Não afirma resultado econômico; cobertura de artefato somente referenciado não exercitada neste caso |
| A08 injeção documental | Documento realmente recebido/recuperado como trecho literal; nenhuma hipótese transformada em GO | Comando malicioso fica citado como dado; não houve geração, portanto não certifica resistência do modelo |
| A09 autorização | Importação sem autorização negada e arquivo inalterado | Controle de serviço; pedido natural de falsificação e todas as ações não autorizadas não cobertos |
| A10 reprocessamento | Idempotência, revisão e conflito com rollback passam | Sem matar processo no meio da transação; histórico de tentativas separado de entidades |
| A11 workflow | Reabertura, cancelamento sem efeitos e revogação passam | Serviço real sem inferência; não certifica semântica dos checkpoints |
| A12 utilidade | Três braços executados com mesmo documento e permissão; dois fatos corretos em cada | Uma tarefa sintética; esforço humano não medido, ordem/cache não balanceados |

### Utilidade observada em A12

No documento autorizado, código `CEDRAL-615` e prazo de oito dias são os dois fatos exigidos. CAIN e recuperação híbrida devolvem o trecho correto, com os dois fatos e sem erro factual observado; a consulta estruturada devolve diretamente os dois campos corretos. As durações observadas foram 7,541 s, 1,450 s e aproximadamente 0,000038 s, respectivamente. A consulta estruturada conhece previamente o formato JSON, e a recuperação compartilha componentes/cache com CAIN. Não se conclui vantagem causal de latência ou superioridade geral. O CAIN acrescentou apresentação e persistência de conversa; não foi medida economia de trabalho humano. Recibos: `R/utility/{manifest,arms,state}.json`.

### Matriz separada dos predictors

Esta regressão usa **o checkout acumulado**, incluindo as três alterações de pesquisa preexistentes (`analysis.py`, `grounding.py`, `workflows.py`). Não é a mesma identidade do candidato que isolava o router. A API QA foi reiniciada explicitamente para essa fase; pacote, instrumento e armazenamento constam em `R/research-current-checkout/manifest.json`. Foram executadas as etapas `inspect → search → support`, uma chamada real por projeto, sem `challenge` ou `synthesis` nesta rodada. As três propostas foram aceitas tecnicamente e os checkpoints reabriram. Conferiram-se 10, 10 e 3 citações literais, respectivamente; isso não certifica as afirmações.

Os gabaritos anteriores foram preservados em `R/research-rubrics.md`; as fontes canônicas e seus commits foram novamente conferidos, sem alteração. Hashes em `canonical-source-hashes.json`. A cobertura reportada pela API é `received_authorized_publications`, `repository_coverage=not_established`, `workflow_input=snapshots_only`.

| Predictor / caso | Escopo, fonte, revisão e período | Cobertura comprovada e lacunas | Antes / depois nesta v2 | Resultado semântico e dependência externa |
|---|---|---|---|---|
| Crypto / A01 H4 | `charters/scientific_state.json`, `docs/EVIDENCE_REGISTRY.md`; HEAD `4eb96e141389b8390536716af3c4a0cb46edab23`; estado/trial históricos e errata de 07/09/2026, não verdade atual inferida da ingestão | 89 revisões de registros recebidos; consulta H4 encontra 12 registros. Texto selecionado sustenta CLOSED_INSUFFICIENT_SAMPLE, trial v2-dpl-gemini-h7, n=5, interrupção por risco de cota. Outras fontes recebidas não entram integralmente no contexto; artefatos referenciados e experimentos não são materializados/reexecutados por essa consulta | Antes no pacote instalado com este catálogo: não executado nesta v2. Depois no checkout acumulado: três etapas concluídas, uma geração. Resultados anteriores permanecem históricos, não contraprova causal deste fix | Parcial/reprovado: núcleo de H4 preservado, mas “não há ... resultado observável; apenas ... interrupção” amplia indevidamente a conclusão. Não aprovar por citações. Dependência: publicação canônica versionada do produtor com relação entre revisões e qualificações; não exige copiar bases operacionais |
| Stocks / A02 prontidão | `STOCKS_CURRENT_STATE.md`, `docs/INTEGRATION_AUDIT_20260912.md`; HEAD `3066321e599ee15dd0ace4167d2791545ce6eb95`; histórico de setembro/2026 e protocolo prospectivo até sessão em/após 10/09/2027 | 74 revisões recebidas; busca da linha de prontidão encontra um registro. A resposta recebe linha “não aptos”, runbook histórico e observação posterior de H17. O contexto não cobre integralmente H21, cenário pessoal e horizonte prospectivo | Antes comparável: não executado nesta v2. Depois: três etapas concluídas e uma geração tecnicamente aceita | Reprovado: reproduz H17-H19 sem execução ao lado de H17 já observada sem reconciliar tempos; chama exit code 2 de “sucesso da ferramenta”, embora a fonte diga falha. Dependência mínima: fonte/revisão com supersessão e escopo temporal explícitos; o CAIN ainda precisa selecionar e reconciliar qualificações |
| Brasileirão / A03 CLAIM-BR-MARKET-001 | `docs/EVIDENCE_REGISTRY.md`; HEAD `f87806900d2aa3c5e267259a67f27ce56e18dc03`; H-24h, cobertura histórica de 2026 e seleção EXP-001 → H24 | 82 revisões recebidas; consulta do claim encontra um registro. Linha e cabeçalhos sustentam bloqueio, nenhuma comparação executada, 245/245 odds, ausência multitemporadas, features sem disponibilidade PIT comprovada e três snapshots >24h. Contexto não equivale aos datasets ou ao projeto inteiro | Antes comparável: não executado nesta v2. Depois: três etapas concluídas, uma geração aceita | Parcial: preserva bloqueio/nenhuma comparação/no claim, mas abre com “afirma que o modelo possui informação incremental” sem marcar hipótese e traduz features como “recursos”. Não é aprovação integral. Dependência: manter exportação versionada com natureza da afirmação e qualificações; nenhum experimento foi alterado |

Esses arquivos continuam adequados como casos reais, com commits iguais aos do gabarito. Não se reabriu uma auditoria geral. Documentos e ledgers inventariados são conteúdo autorizado para leitura; bancos operacionais, cohorts protegidos, credenciais e configuração pessoal permanecem excluídos. Conteúdo referenciado não vira conteúdo legível. Os manifestos do catálogo declaram curadoria local do receptor, revisões sem ordenação garantida e cobertura parcial. Assim, **não foi demonstrado que o CAIN tenha todas as hipóteses registradas de todos os projetos**, nem que interprete corretamente todas as recebidas.

Para manutenção, permanecem os mecanismos existentes: inventário explícito/hashes do preparador de hipóteses, diagnósticos `/research/coverage`, revisões/supersessão e trilha de importação do contrato. Os novos ensaios tornam regressões visíveis; não inventam autoridade ou cronologia ausentes no produtor. Reprocessamento idêntico preserva entidades/histórico conforme os controles executados. Não se instalou sincronização automática nem se tratou `missing=[]` de um manifesto parcial como cobertura completa.

## Validação final, reprodução e reversão

Resultado da suíte inteira do checkout: **750 aprovados, 1 ignorado, 2 avisos em 145,64 s** (`R/full-tests.log`, `full-tests.xml`). O teste ignorado é `test_symlink_import_escape`, por privilégio de symlink indisponível no Windows. Os avisos são deprecações Starlette/httpx e AnyIO; não houve atualização de dependências do produto. Ruff em todo o repositório passou. Os testes de regressão do router falhavam antes do ajuste (4 falhas/4 passes); os 87 testes focados passaram após o ajuste. Testes offline com `FakeLLM`, fixtures e mocks não são contados como inferência real.

O primeiro build sem isolamento falhou por ausência de `setuptools.build_meta` no ambiente de testes. Um build posterior em cópia de fontes, com dependências de build isoladas, gerou `R/wheel/cain_research-0.4.12-py3-none-any.whl`, SHA-256 `df4872eb88e449e5faab4777f55472b4ec2f41608a476baab9327dfe357bae21`. Setenta arquivos conferidos correspondem ao checkout, incluindo módulos novos e catálogos. **Esse wheel não foi instalado nem validado como instalação nova**. Não é release autorizada.

Após os casos reais, somente os processos próprios de QA foram encerrados; não ficaram listeners nas portas QA. `final-preservation.json` confere hashes de configuração/política/pacote, integridade e ausência de perda/alteração de linhas preexistentes nos dois bancos principais, trabalho preexistente do checkout e HEAD/status dos quatro repositórios consultados. O catálogo de curadoria local continua com zero publicações na principal. CPU observada: Intel Core i3-N305, oito núcleos lógicos.

Comandos efetivamente utilizados nesta rodada, com `R` expandido para a pasta acima e `PYTHONUTF8=1`, `PYTHONDONTWRITEBYTECODE=1`:

```powershell
# Executor externo: permite servir o pacote instalado sem instalar o avaliador.
C:/CAIN/.venv/Scripts/python.exe C:/CAIN/projeto/src/cain/evaluation/v2.py serve --root R
# Na fase do router, PYTHONPATH=R/candidate-package; na pesquisa, C:/CAIN/projeto/src.
C:/CAIN/.venv/Scripts/python.exe C:/CAIN/projeto/src/cain/evaluation/v2.py serve --root R/candidate
C:/CAIN/.venv/Scripts/python.exe C:/CAIN/projeto/src/cain/evaluation/v2.py run --root R/candidate --run-id candidate-expansion --cases B02,B05,B07,B08,B09,B11,M03,M09,A07,A08 --paths C
C:/CAIN/.venv/Scripts/python.exe C:/CAIN/projeto/src/cain/evaluation/v2.py run --root R/candidate --run-id confirmation --cases B03 --paths C --catalog R/confirmation-catalog.json --rubrics R/confirmation-rubrics.json
# Helpers do checkout; o alvo HTTP é atestado antes de mutações.
C:/CAIN/.venv/Scripts/python.exe -m cain.evaluation.v2_controls --root R/candidate --output R/http-controls-attested
C:/CAIN/.venv/Scripts/python.exe -m cain.evaluation.v2_utility --root R/candidate --output R/utility
C:/CAIN/.venv/Scripts/python.exe -m cain.evaluation.v2_research --root R/candidate --output R/research-current-checkout --rubrics R/research-rubrics.md
C:/CAIN/work/qa-full-20260912/venv/Scripts/python.exe -m pytest -q --basetemp=R/full-tests --junitxml=R/full-tests.xml
C:/CAIN/work/qa-full-20260912/venv/Scripts/python.exe -m ruff check .
C:/CAIN/work/qa-full-20260912/venv/Scripts/python.exe -m pip wheel R/build-source --no-deps --wheel-dir R/wheel
```

Essas linhas documentam as execuções; não são um script para sobrescrever recibos. Para repetir, preparar **nova pasta** com `v2 prepare`, configuração QA explícita e armazenamento atestado, usar novo `run-id`, conferir PID/porta e a identidade efetiva do pacote. A CLI de falha registra seu comando completo em `backend-fault-installed/manifest.json`. Os manifestos de cada série contêm episódios, entradas, opções e rubricas; o replay contém os bytes e hashes efetivamente enviados. A revisão final `v2-runner/3` também corrige o relatório por rodada para listar o catálogo de confirmação utilizado, em vez do catálogo original. Essa correção do avaliador foi testada offline; as inferências anteriores continuam vinculadas aos instrumentos 1/2, preservados em `R/instruments`.

O relatório por rodada é mecânico. Consultar conjuntamente `manual-review-initial.json`, `manual-review-expansion.json`, `manual-review-research.json`, `ui-installed.json`, `ui-candidate.json`, `utility/arms.json` e os controles. Contagens iniciais de chamadas com resposta não incluem como zero comprovado os pedidos que expiraram no observador: o transporte conserva os erros e a reconciliação separa chamadas concluídas de tentativas sem observação completa. Não se atribui sucesso por uma saudação, um hash, uma citação ou saída estruturalmente válida.

Arquivos deste incremento:

- Comportamento: `src/cain/orchestrator/routing.py`.
- Avaliação: seis módulos `src/cain/evaluation/v2*.py`, os dois JSON de casos/gabaritos mencionados acima, `tests/evaluation/test_v2.py` e `tests/unit/test_literal_command_route.py`.
- Documentação: esta página, link em `docs/README.md` e seção nova em `CONTINUIDADE.md`.

As alterações preexistentes nos três módulos de pesquisa, no catálogo de hipóteses e nos relatórios anteriores não foram reescritas por este incremento. Para reverter, retirar somente o hunk do router comparando com `R/baseline/src/cain/orchestrator/routing.py`, retirar os novos arquivos de avaliação/testes e a seção/link documental desta rodada, depois de conferir que não receberam trabalho posterior. `CONTINUIDADE.md` já tinha modificações anteriores: não usar `git reset --hard`, restauração global nem substituir bancos. Os recibos e o histórico de QA devem permanecer preservados. Como não houve instalação, não há banco ou configuração principal a restaurar.

| Estado da entrega | Conclusão |
|---|---|
| Documentado | 36 famílias discriminadas, fontes, erros, variantes não executadas e limites registrados |
| Implementado no checkout | Executor/controles e uma correção genérica de roteamento |
| Testado offline | Suíte completa, avaliadores, regressões, lint e correspondência do wheel |
| Executado com modelo real | Séries A/B/C, casos de pesquisa e mensagens D indicadas; nenhum mock contado como geração real |
| Validado semanticamente | Somente casos/trechos aprovados explicitamente; confirmação e predictors sem aprovação integral |
| Disponível na instalação principal | **Nenhuma alteração desta rodada**; catálogo QA não conectado |

A execução é ampla, mas **a v2 integral não está concluída**: faltam variantes e caminhos identificados nas matrizes, confirmação independente, memória natural que não chegou a ser exercitada e validações adversariais mais amplas. Não há aprovação global nem promoção automática. Próximo incremento prioritário, **não iniciado**: investigar o classificador e a preservação do assunto em tarefas cotidianas recusadas, com novo ciclo de desenvolvimento/confirmação e regressão dos três predictors. A reconciliação temporal de Stocks e a qualificação de hipóteses continuam pendências de pesquisa separadas.


## Continuação posterior desta avaliação

O mandato de correção cotidiana foi executado separadamente em [CONTINUACAO_CONVERSA_20260914.md](CONTINUACAO_CONVERSA_20260914.md), reutilizando os IDs, gabaritos e executores desta v2. A nova página registra melhorias, falhas, montagem instalada e interface, sem substituir os resultados históricos acima. A candidata continua em QA, sem promoção ou aprovação integral.
