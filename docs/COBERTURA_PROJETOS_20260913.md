# Cobertura dos projetos conectados — 13/09/2026

A verificação incremental posterior está na seção [Verificação incremental de conhecimento](#verificação-incremental-de-conhecimento--13092026-sem-instalação), que registra o ensaio anterior à instalação. Depois desse ensaio, o usuário solicitou a instalação do commit `dfabf6dab05df1662e9882ebe1091236daa14724`, concluída e verificada: [instalação vigente](LOCAL_INSTALLATION.md). Os recibos históricos e limites semânticos permanecem abaixo; menções a candidato não instalado referem-se ao momento do ensaio.

**Conclusão: o CAIN não recebe os projetos inteiros.** A recuperação do conteúdo conectado passou; as conexões entregam recortes Snapshot e metadados/artefatos Bundle específicos. A versão 0.4.12 acrescenta um diagnóstico conjunto à API, CLI e interface, para não confundir esses conceitos.

## Acervo principal observado

| Projeto | Snapshot principal | Bundle no CAIN principal | Inventário do checkout atual |
|---|---|---|---|
| Crypto | 15 revisões de registros, oriundas de dois arquivos | Nenhum | 3.247 arquivos versionados |
| Stocks | Uma revisão de status de um arquivo; outro acervo preserva uma publicação adicional | Um pacote, duas entidades, dois artefatos somente referenciados | 1.680 arquivos versionados |
| Brasileirão | Três revisões de registros de um arquivo | Nenhum | 2.537 arquivos versionados |

O acervo `heterogeneous` repete quatro registros selecionados de Stocks/Brasileirão. Não somar esses registros como pesquisas independentes. As quantidades de arquivos vêm de `git ls-files`; não incluem todos os dados não versionados e não medem compreensão do modelo. Mesmo os arquivos declarados podem estar representados apenas por trechos.

Arquivos declarados no conteúdo recebido: Crypto — `charters/scientific_state.json` e `docs/EVIDENCE_REGISTRY.md`; Stocks — `STOCKS_CURRENT_STATE.md` e `docs/engineering/2026-09-11-architecture/evidence/real-v020.json`; Brasileirão — `docs/EVIDENCE_REGISTRY.md`. Todo o restante fica fora dessa declaração. A auditoria encontrou uma versão histórica de `STOCKS_CURRENT_STATE.md` diferente do arquivo atual, além de uma versão coincidente; isso não autoriza substituir ou apagar a anterior.

**Retificação do relatório 0.4.11:** a expressão “dois Bundles” confundia duas entidades com pacotes. O acervo `stocks-main-bundle` contém um pacote e duas entidades na auditoria atual.

## O que foi testado

A ferramenta `tools/verify_project_coverage.py` percorreu os seis acervos configurados, paginou todos os 24 registros disponíveis entre eles (há sobreposição), recuperou cada identidade exata por consulta e busca, e resolveu suas referências. Para Bundle, conferiu as duas entidades, dois artefatos, três evidências e três relações. Um usuário sem concessão recebeu acervos vazios. Nenhuma inferência foi usada para aprovar contagens ou hashes.

A auditoria foi executada sobre cópias dos bancos, com a política preservada. Uma primeira tentativa concorrente com o workflow encontrou bloqueio de SQLite; o auditor foi separado em outra cópia e passou. Isso é uma correção do ensaio, não evidência de recuperação completa na tentativa que falhou.

Também foram validados e importados os três pacotes `bundle-v1-completion-e2e/bundle.json`, em banco e política exclusivos de QA:

| Exportação | Entidades recuperadas | Artefatos | Conteúdo materializado e hash conferido | Somente referência |
|---|---:|---:|---:|---:|
| Crypto | 20 | 12 | 12 | 0 |
| Stocks | 2 | 2 | 0 | 2 |
| Brasileirão | 14 | 5 | 2 | 3 |

A consulta de cada entidade e artefato passou. As 14 materializações coincidiram com seus hashes; os cinco artefatos somente referenciados recusaram materialização. A geração permaneceu desautorizada nos três pacotes, conforme as restrições originais. O isolamento entre usuários passou.

Esses pacotes não estão conectados à instalação principal. O teste isolado demonstra que o consumidor consegue recebê-los; não amplia a política principal nem habilita acesso aos repositórios, bancos protegidos ou conteúdos que os produtores excluíram. Todos os três manifestos declaram `completeness=partial`.

## Workflows e síntese livre

Foram executados três workflows completos de seis etapas, um por produtor: Crypto/H4, Stocks/prontidão operacional e Brasileirão/CLAIM-BR-MARKET-001. Os 18 checkpoints concluíram e foram reabertos depois pela API instalada 0.4.12. Houve nove inferências reais de redação (support/challenge/synthesis); inspect/search/extração estruturada não fizeram chamadas ao modelo. Mais três chamadas em `/research/explain` produziram seleção de trechos (`source_excerpts`), não síntese livre irrestrita.

A geração rodou com o pacote 0.4.11, Ollama 0.34.0 e qwen3.5:4b nos parâmetros existentes. Os módulos de workflow, análise, Historian, evidências e pontes foram comparados byte a byte e permanecem iguais na 0.4.12. A mudança desta entrega é o diagnóstico de cobertura; a leitura dos checkpoints foi retestada pela API 0.4.12.

**Conclusão técnica não é aprovação semântica.** A revisão das redações identificou:

- Crypto: estado e trial preservados, mas a expressão “status atual” pode ultrapassar o que um snapshot congelado atesta. Resultado parcial.
- Stocks: a etapa support diz que a conclusão decorre “exclusivamente” da ausência de dados; essa atribuição é mais forte que o trecho disponível. Resultado parcial.
- Brasileirão: support/challenge/synthesis tratam a descrição de uma hipótese (“Model has incremental information…”) como informação estabelecida, mesmo com estado bloqueado e nenhuma comparação executada. **Falha semântica**. Citações válidas não corrigem essa interpretação.

Esses resultados estão em `semantic-review.json`. Não houve alteração dos produtores, das hipóteses ou das restrições de geração para fazer o teste passar.

## Correção do diagnóstico

O comando `cain research ... coverage` preserva os campos anteriores de Snapshot e acrescenta contagens separadas para Bundle, arquivos declarados, permissões de geração e disponibilidade dos artefatos. A API oferece `POST /research/coverage`, e a interface inclui **Cobertura do acervo** no painel Pesquisa.

O diagnóstico não declara cobertura integral do repositório. Também informa que os workflows de seis etapas usam Snapshot; a consulta de metadados Bundle é separada. Permissões e integridade continuam verificadas, com escopo consistente e limite explícito de tamanho da resposta. As regressões cobrem acervos somente Bundle, mistura das duas pontes, duplicação, revogação, isolamento, corrupção, API e CLI.

## Reprodução e entrega

Recibos: `C:/CAIN/work/coverage-projects-20260913`. `coverage-audit.json` contém inventários e recuperação completa do acervo configurado; `bundle-candidates/report.json` contém as três importações isoladas; `full-workflows.json` preserva cada etapa e explicação, incluindo falhas se houver. Os diretórios `baseline`, `isolated`, `audit` e `bundle-candidates` mantêm os ensaios separados.

Para repetir o auditor, fornecer uma cópia consistente do banco com seu diretório `research-objects` e um JSON com `projects` (domain/checkout) e `bundles` (manifestos explicitamente selecionados):

```text
python tools/verify_project_coverage.py --db COPIA/research.db --policy POLICY.json --inventory producer-inventory.json --output coverage-audit.json
```

Versão instalada **0.4.12**, código `5364c3b1de5d01c1cf6747b9eed52e562e1a63cd`; wheel SHA256 `20bf092380eb9f2a62fee9cf19975dd3586766309b9c99d0c00f60b0edea73f9`. Suíte completa: **680 aprovados, 1 skip Windows e 2 avisos**. Ruff, sintaxe JavaScript, instalação offline, pip check e comparação dos **62 arquivos** aprovados. API principal nos seis acervos, CLI e botão **Cobertura do acervo** verificados. A tela mostrou corretamente Crypto com 2 publicações/15 revisões e Stocks Bundle com 1 pacote/2 entidades/2 referências sem conteúdo recebido.

Os bancos principais estão íntegros, com todas as linhas preexistentes preservadas. Configurações, política, atalhos e dependências de terceiros não mudaram. Os HEADs e estados Git dos três produtores permaneceram iguais. Backup da 0.4.11 e dos bancos em `baseline`; ver `preservation.json`. Publicação local/remota em `git-publication.json`; resultado da CI da referência final em `ci-final.json`, separado do pacote e da avaliação semântica.

A cobertura de importação/recuperação e a validade de citações não comprovam aprendizado, compreensão integral, correção científica, lucro ou prontidão operacional dos produtores.


## Verificação incremental de conhecimento — 13/09/2026, sem instalação

**Resultado final: integração parcial em cada predictor.** Esta rodada amplia o diagnóstico existente e reduz uma falha demonstrada de geração; não certifica conhecimento completo nem interpretação livre. O código da rodada está no checkout, separado da instalação 0.4.12 descrita acima. Não foram alterados produtores, Ecosystem, Core, Ops, modelos, políticas ou bancos principais por esta tarefa. Não foram conectados acervos de QA à principal.

Baseline inicial: CAIN `d7001bc7c8c50df8a9fb03ca76ad0f74e797705e`, main limpa. Ecosystem `c51d9e63e8441e15b2d045ea4d6a7c67f4ebbdfd`; Brasileirão `f87806900d2aa3c5e267259a67f27ce56e18dc03`; Crypto `4eb96e141389b8390536716af3c4a0cb46edab23`; Stocks `3066321e599ee15dd0ace4167d2791545ce6eb95`, todos inicialmente limpos em main. São checkouts locais conferidos, não uma nova certificação dos remotos ou da ciência. Edições documentais concorrentes detectadas em CONTINUIDADE, ESTADO_DO_PROJETO, LOCAL_INSTALLATION e ANALYSIS_GUARD foram preservadas; não são atribuídas a esta rodada.

Recibos desta rodada: [knowledge-integration-20260913](C:/CAIN/work/knowledge-integration-20260913). `baseline.json` fixa as identidades; `rubrics.md` fixa os gabaritos antes das mudanças; `knowledge-needs.json` registra 24 fontes explicitamente selecionadas, sua necessidade, existência, hash e último commit do arquivo; `audit/publications.json` preserva revisões, fontes e relógios recebidos; `related-retrieval.json` demonstra a lacuna de seleção H4. Data de commit, exportação e ingestão não substituem a data da informação.

### Matriz — Brasileirão

| Dimensão | Comprovação e limite |
|---|---|
| Conhecimento necessário examinado | Objetivo/funcionamento e contratos: README, ARCHITECTURE_IMPLEMENTATION e docs/RESEARCH_BUNDLE_V1. Para julgar EXP-001: docs/EVIDENCE_REGISTRY, diagnóstico de features PIT, avaliação de cobertura/identidade e decisão de prontidão em reports, datados de 02/09/2026. Foram selecionadas nove referências por necessidade, sem exigir todos os arquivos ou bancos. |
| Fonte e período | HEAD `f878069...`; registro de claims com hash recebido igual aos bytes atuais. A avaliação de identidade relata população de 01/01 a 02/09/2026; holdout 2025 consumido. Os relógios científicos dos registros recebidos permanecem null. Os relatórios datados não certificam a situação operacional presente. |
| Disponível e recuperável | Acervo brasileirao: duas publicações, três revisões de registros; linhas completas de CLAIM-BR-MARKET-001/002/003 com identidade, estado e offsets. O caso recebeu a linha de 341 caracteres, com BLOCKED_PENDING_PIT_FEATURES, no model comparison executed, no claim, limites e seleção de horizonte. Recuperação exata e evidências resolvidas novamente nesta rodada. |
| Recebido mas não utilizado / referência | As outras claims podem ser consultadas, mas não são evidência independente de H-24h. Não há Bundle no acervo principal brasileirao. O Bundle externo já ensaiado historicamente em QA continua separado; seu manifesto/payloads foram novamente verificados, sem nova importação nesta rodada. |
| Lacunas | Cabeçalhos da tabela e parágrafos de contexto não chegaram no Snapshot. Objetivos, contratos, diagnósticos de PIT e metadados explicativos não estão no fluxo de seis etapas. Dois relatórios citados — exp001_data_pilot_2026-09-02.json e exp001_coverage_audit_2026-09-02.json — não foram encontrados nos caminhos apontados pelo registro no checkout atual; isso não prova perda em todos os históricos/locais. |
| Exclusões | Bases Sports/Market, coortes protegidas H14/H15/H9/A1, holdouts e demais fontes não admitidas permanecem fora do transporte. Ler contratos/metadados não autoriza executar avaliações protegidas ou copiar bancos. |
| Caso e gabarito | CLAIM-BR-MARKET-001: informação incremental H-24h é hipótese; comparação não executada, bloqueio preservado, decisão no claim. Cobertura 245/245 não é incrementabilidade. Sem odds multitemporadas, disponibilidade PIT não comprovada e três snapshots >24h. Não inferir efeito, AFE, lucro ou resultados preliminares. |
| Antes / primeira correção / final | Antes: falha nos três textos, incluindo hipótese promovida a efeito. Primeira correção de contexto: falha persistiu. Final: três abstenções explícitas, zero inferências, estados e trechos preservados. Proteção técnica demonstrada; interpretação correta da hipótese pelo modelo **não foi aprovada**. |
| Testes e limites | Fluxo real Workflows completo nas três rodadas, sobre cópias; seis inferências nas duas primeiras rodadas: três antes e três após o primeiro ajuste; nenhuma na final. Testes com doubles verificam a proteção, não compreensão. Não houve comparação preditiva nova. |
| Dependência mínima | Produtor: incluir cabeçalhos/contexto com offsets e versão no recorte autorizado, e esclarecer localização/publicação dos dois relatórios referenciados. CAIN: conservar esses rótulos na seleção antes de reconsiderar síntese livre. Nada disso foi alterado no produtor. |

### Matriz — Crypto

| Dimensão | Comprovação e limite |
|---|---|
| Conhecimento necessário examinado | Objetivos e funcionamento atuais (README/arquitetura), charter, EVIDENCE_REGISTRY, HYPOTHESES, trials, contrato Bundle e AAVE_VALIDACAO_20260910: oito fontes selecionadas. As famílias congeladas não resumem a pesquisa posterior. Aave documenta resultado histórico condicional, não lucro pessoal ou futuro; não foi reavaliada nesta tarefa. |
| Fonte e período | HEAD `4eb96e1...`; hashes recebidos de charter e EVIDENCE_REGISTRY coincidem com os arquivos atuais. Exportações recebidas referem `e4f8974...`, de 11/09/2026. H4/trial tem registro histórico em julho/2026; as_of_commit do charter é histórico. Clocks científicos recebidos null; ingestão em setembro não redata a pesquisa. |
| Disponível e recuperável | Duas publicações, 15 revisões, sete objetos de evidência únicos: charter e seis blocos de claims. Recuperação paginada e identidade exata passaram. H4 restrito recupera estado CLOSED_INSUFFICIENT_SAMPLE e trial v2-dpl-gemini-h7. |
| Recebido mas não utilizado | **n=5 e interrupção por risco de estouro de cota já foram recebidos**, no bloco CLAIM-CR-LLM, com geração permitida na política copiada. Consulta exata dessa claim recupera o conteúdo; busca sem filtro de identidade encontra H4 e a claim. O filtro exato H4 do workflow seleciona só o charter. Portanto, essa lacuna é de ligação/recuperação/contexto no CAIN, não de ausência desses fatos no acervo. |
| Lacunas e referências | README/arquitetura, protocolos completos, trials e Aave não estão no Snapshot principal. Nenhum Bundle em crypto principal. O Bundle externo de QA contém conteúdo materializado de seleção de trials/atestados, mas não participa deste fluxo nem concede geração; nesta rodada foi verificado como exportação externa, sem conectá-lo. Dados brutos históricos ausentes não são recuperados por citar um registro. |
| Exclusões | Bancos operacionais, holdouts protegidos e outras pesquisas estão explicitamente excluídos das publicações existentes. Documentos públicos adicionais de que a tarefa necessita exigem exportação/aceite delimitados; não foram concedidas novas permissões. Segredos e configuração privada não foram lidos nem copiados. |
| Caso e gabarito | H4: estado/trial corretos; amostra insuficiente não confirma nem refuta. A fonte mais ampla informa n=5 e risco de cota; não transferir métricas/veredito de H5. Não apresentar estado atual certificado nem inventar motivo quando o recorte não o contém. |
| Antes / primeira correção / final | Antes: parcial, com status atual sem atestado. Após contexto e na final: estado/trial preservados no conjunto das etapas, mas resposta ainda parcial; synthesis fala em ausência de dados estatísticos relevantes e challenge chama a trial de comparação de desempenho registrada, além dos campos fornecidos. A síntese omite trial; motivo e n continuam fora do contexto. Não houve aprovação semântica integral. |
| Testes e limites | Três workflows reais completos; nove inferências neste caso ao longo das três rodadas. Consulta relacionada testada sem mocks, mas não utilizada automaticamente na geração. A correção não estabelece relações semânticas universais nem valida o experimento original. |
| Dependência mínima | CAIN: recuperação relacionada limitada e verificável entre identidades já admitidas, com distinção H4/H5 e cobertura explícita. Produtor: apenas para objetivos/protocolos/pesquisa posterior ainda fora do acervo, seleção documental e exportação autorizadas. O motivo/n de H4 não exige inventar nem reexportar fatos que já chegaram. |

### Matriz — Stocks

| Dimensão | Comprovação e limite |
|---|---|
| Conhecimento necessário examinado | Sete fontes: README/arquitetura, STOCKS_CURRENT_STATE, contrato Bundle, recibo real-v020, protocolo H21_FORWARD_OBSERVATION_PLAN_V1 e relatório OSS-20260911-01. Necessidades: separar prontidão de engenharia de prontidão econômica, evidências históricas, hipóteses, custos, eventos, premissas pessoais e obrigações prospectivas. |
| Fonte e período | HEAD `3066321...`; documento de estado com registros de 11/09/2026 e integração posterior. Protocolo H21 fixa entrada na primeira sessão em/após 10/09/2026 e saída na primeira sessão em/após 10/09/2027; o registro é plano sem execução, não monitor atual. Os relógios do status exportado são null. |
| Disponível e recuperável | Acervo stocks: duas publicações, uma revisão de status, linha de 118 caracteres. stocks-main-snapshot: outra publicação/revisão com origem no HEAD atual. stocks-main-bundle: um pacote, duas entidades, dois artefatos reference_only, três evidências e três relações, sem geração autorizada. Consulta de todos esses itens passou. |
| Recebido mas não utilizado / referência | O workflow selecionado usa stocks, não stocks-main-snapshot nem o Bundle. Metadados do catálogo são recebidos; preços e recibo bruto referenciados não se tornam payloads acessíveis. O Bundle não é entrada do workflow Snapshot. |
| Desatualização e lacunas | No acervo stocks, hash do arquivo de origem difere do checkout atual; no stocks-main-snapshot, coincide. A linha de prontidão é a mesma, mas isso não atualiza o documento inteiro nem escolhe automaticamente o acervo correto. Não chegaram os cabeçalhos, contexto H21/H22, protocolo prospectivo, custos/premissas e detalhes econômicos necessários a explicações mais completas. |
| Exclusões | Preços/bancos, documentos com licença não certificada, dados pessoais e fontes fora do aceite permanecem fora. UNKNOWN de licença não é permissão de redistribuir. Nenhum runtime Stocks foi instalado ou executado no Windows. |
| Caso e gabarito | Retorno líquido pessoal e operação real: Não aptos — custos, eventos, cenário pessoal e observações insuficientes. Não atribuir exclusivamente à ausência de dados nem negar existência de análise histórica. Engenharia funcional não prova lucro; H21 histórico condicional não é resultado pessoal/futuro. |
| Antes / primeira correção / final | Antes: support inventa justificativa exclusiva e falta de análise detalhada. Primeiro ajuste: ainda extrapola ausência de execução/resultados e chega a inventar leitura inteira negada. Final: três abstenções explícitas com a linha de status preservada, zero inferências. Não aprova interpretação econômica nem completa cobertura. |
| Testes e limites | Três workflows reais completos; seis inferências antes da proteção final, nenhuma depois. Recuperação do Bundle é técnica e separada. Não houve novo backtest, observação prospectiva, ordem ou validação econômica. |
| Dependência mínima | Produtor: recorte público de prontidão com cabeçalhos e qualificações de H21/protocolo, conservando versões e licenças. CAIN/operador: escolher explicitamente o acervo/revisão pertinente após comparar as fontes; não substituir histórico nem escolher verdade pela ingestão mais recente. |

### Caminho inspecionado e correções incrementais

Recebimento: contratos, hashes, política e arquivo bruto verificado; projeção e reimportação são mecanismos existentes. Recuperação: query/inspect/search exatos e paginados; isolamento por usuário e coleção preservado. Contexto: cards preserva bytes/offsets mas seleciona linhas e campos; os cabeçalhos dos casos de tabela não foram recebidos e a identidade H4 não une automaticamente a claim relacionada. Geração: review recebe esses recortes e produz propostas; validar citação não verifica a inferência.

A primeira correção acrescentou identidade/localização/revisão/relógios e limites ao contexto e às instruções, sem ampliar orçamento, trocar modelo ou importar fontes. Os três casos foram reexecutados; a revisão manual mostrou que isso foi insuficiente. Os recibos `after` conservam essa tentativa falha.

A segunda correção impede síntese livre quando o contexto selecionado contém linha de tabela sem seus rótulos. Retorna `abstained_unlabelled_table`, fatos, trechos resolvidos, motivo e zero chamadas. **A restrição também alcança outras tabelas selecionadas como linhas, inclusive quando o cabeçalho existe em outra parte da fonte mas não chegou ao contexto.** É uma limitação deliberada e visível; não é prova de compreensão. Os demais formatos continuam sujeitos a erro. O protocolo research-workflow/10 impede retomar etapas antigas sob instruções novas; a leitura dos históricos é preservada.

`before/workflows.json`, `after/workflows.json` e `final/workflows.json` contêm perguntas, entradas recuperadas, checkpoints, respostas, prompts exatos, schemas, hashes do código e identidade/configuração do modelo. Foram 21 inferências reais ao todo: nove antes, nove após o primeiro ajuste, três na final. Na final, foram seis abstenções em Brasileirão/Stocks e três textos de Crypto, não nove respostas semanticamente aprovadas. `semantic-review.json` registra a avaliação manual por caso/rodada, não uma avaliação humana independente. O fluxo real foi a API Python Workflows com Ollama existente em processo isolado; não uma instalação do candidato na API principal.

### Manutenção no CAIN

Foi estendido **o auditor existente** `tools/verify_project_coverage.py` (project-coverage/2), sem criar sincronizador, banco ou configuração operacional paralela. O JSON opcional `expected_sources` de cada projeto recebe objetos `path`/`need`: necessidades definidas pelas tarefas, não pela allowlist atual do exportador. Isso apenas diagnostica, sem autorizar importação. A presença do nome de arquivo continua separada de cobertura de conteúdo.

O relatório agora registra, por publicação **e acervo**, revisão de origem, exported_at, received_at, relógios científicos originais, supersedes e comparação dos hashes com o checkout explicitamente informado. Ausência do checkout, caminho fora da raiz, arquivo ausente, erro de leitura e limite de tamanho são estados explícitos. Um SHA de código diferente não basta para chamar um conteúdo de desatualizado; hashes iguais também não certificam validade presente. Para Stocks, o diagnóstico deixa visível a divergência no acervo consultado mesmo quando outro acervo tem os bytes atuais.

Também resume os últimos cem recibos Snapshot e mostra os dez mais recentes por estado. Rejeições/duplicações já registradas ficam visíveis. Isso detecta tentativas no receptor; não detecta publicação nunca tentada, mudança externa sem comparação, falha de um produtor inacessível nem expiração sem prazo declarado. Para Bundle, usar também os recibos/approvals existentes; esta extensão não inventa um estado global de sincronização.

Reprodução, usando cópia consistente e preservando política/objetos:

```text
python tools/verify_project_coverage.py --db COPIA/research.db --policy COPIA/policy.json --inventory C:/CAIN/work/knowledge-integration-20260913/inventory-with-needs.json --output NOVO_RELATORIO.json
```

Antes de aceitar atualização: comparar arquivos esperados e recibos por escopo; verificar revisão/hash e datas na autoridade produtora; preservar UNKNOWN/null e ausência de relógios. Reprocessar a mesma publicação deve acrescentar recibo de duplicação sem duplicar registros; revisões coexistem e omissões não apagam histórico. As regressões existentes de duplicação, conflito, revogação, isolamento e revisões fora de ordem continuam aplicáveis. Depois de mudança em fonte/seleção/contexto, repetir os três gabaritos, examinar citações **e** inferências e não promover casos parciais por uma média agregada. Não foi agendado monitor nesta tarefa.

### Validação, entrega e reversão

Os 47 testes direcionados passaram na primeira correção, seguidos de 681 testes/um skip antes da abstenção. Após a proteção, 54 direcionados passaram; o auditor recebeu sete testes de cobertura, incluindo duas regressões novas de drift/relógios/escopo. Testes de protocolo usam doubles e não validam interpretação. A suíte final e o lint desta rodada ficam em `tests-final.log` e `ruff-final.log`; o recibo final de preservação/readback fica em `preservation.json`. Não atribuir resultados intermediários ao código final sem comparar os hashes.

Limites de execução: o Python principal não contém pytest; a primeira tentativa não executou testes, e a validação usou o ambiente de QA já existente. Uma preparação assumiu a existência do diretório opcional de objetos; o acervo principal contém apenas Bundle reference_only e não possui payloads nesse diretório. A ausência foi registrada, a preparação corrigida para esse caso, e os fluxos Snapshot finais usam seus bytes inline preservados. Não houve instalação de dependências ou substituição de bancos para resolver esses problemas.

Arquivos de implementação alterados nesta tarefa: `src/cain/research/analysis.py`, `src/cain/research/workflows.py`, `tools/verify_project_coverage.py`, `tests/integration/test_grounded_analysis.py`, `tests/test_project_coverage.py`. Documentação própria atualizada: este relatório canônico. Os documentos concorrentes foram preservados.

| Estado da entrega | Alcance |
|---|---|
| Documentado | Matrizes, gabaritos, falhas, dependências e reprodução com fontes/recibos locais |
| Implementado | Contexto explícito, abstenção para tabelas sem rótulos no contexto e auditor por revisão/acervo no checkout |
| Testado | Recuperação real e geração/abstenção em cópias, mais testes técnicos identificados; nenhuma aprovação integral dos três casos |
| Disponível na principal | A entrega anterior 0.4.12. O candidato desta tarefa não foi instalado nem conectado à política principal |

Reversão: a principal não necessita rollback desta tarefa, pois não foi atualizada. Para retirar a alteração do checkout, comparar os hashes/diff atuais com os recibos finais e reverter somente os hunks desta rodada nos cinco arquivos de código/testes e neste relatório, usando `baseline/code` como referência. Não usar reset global nem restaurar diretórios/bancos; alterações concorrentes, commits posteriores, publicações e históricos precisam permanecer. A versão intermediária do contexto foi preservada em `after/code`. Se os arquivos já tiverem avançado, fazer reversão seletiva revisada, sem sobrescrever o trabalho posterior.

**Próximo incremento prioritário, não iniciado:** transportar e preservar cabeçalhos/qualificações canônicas no contexto de Brasileirão e Stocks, com aceite explícito do recorte exato e regressão semântica dos três casos antes de liberar novamente síntese livre. A recuperação relacionada de H4 já admitida é uma lacuna separada do CAIN. Nenhuma delas foi declarada resolvida por esta proteção.
