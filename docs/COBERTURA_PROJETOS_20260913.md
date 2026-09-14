# Cobertura dos projetos conectados — 13/09/2026

A verificação incremental posterior está na seção [Verificação incremental de conhecimento](#verificação-incremental-de-conhecimento--13092026), que registra o ensaio anterior à instalação. Depois desse ensaio, o usuário solicitou a instalação do commit `dfabf6dab05df1662e9882ebe1091236daa14724`, concluída e verificada: [instalação vigente](LOCAL_INSTALLATION.md). Os recibos históricos e limites semânticos permanecem abaixo; menções a candidato não instalado referem-se ao momento do ensaio.

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


## Verificação incremental de conhecimento — 13/09/2026

**Resultado final: integração parcial em cada predictor.** Esta rodada amplia o diagnóstico existente e reduz uma falha demonstrada de geração; não certifica conhecimento completo nem interpretação livre. A implementação foi exercitada em cópias de QA. Durante o fechamento, outra atividade publicou o código e atualizou a instalação principal; a divergência está detalhada abaixo. Não foram alterados produtores, Ecosystem, Core, Ops, modelos, políticas ou bancos principais por esta tarefa. Não foram conectados acervos de QA à principal.

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

### Alteração concorrente da instalação — limite da preservação

A conferência final detectou que o hash instalado de analysis.py mudou desde o baseline. A documentação concorrente registra instalação do código `dfabf6d` após solicitação do usuário, com recibos em `C:/CAIN/work/install-dfabf6d-20260913`; esta tarefa não executou comandos de instalação, commit ou push. A main avançou durante a execução, chegando a `3f88a2535f08c70bce561cd3822e7558cebec326` na conferência. Não se presume que esse SHA seja imutável nem que seja o código instalado: este continua identificado separadamente.

Conferência própria: analysis.py, grounding.py e workflows.py instalados coincidem com os hashes dos casos finais; health retornou 200/0.4.12 e declara inferência não exercitada. Todos os registros do research.db que existiam no baseline continuam presentes, a integridade SQLite passou, e os hashes de política/cain.toml permaneceram iguais. Os HEADs e estados Git dos três produtores e do Ecosystem ficaram inalterados. **O baseline do pacote principal não permaneceu byte a byte igual**, por essa mudança concorrente; a tarefa não ocultou nem desfez a diferença. A instalação relatada externamente e seus testes não são atribuídos a esta verificação isolada.

### Validação, entrega e reversão

Os 47 testes direcionados passaram na primeira correção, seguidos de 681 testes/um skip antes da abstenção. Após a proteção, 54 direcionados passaram; o auditor recebeu sete testes de cobertura, incluindo duas regressões novas de drift/relógios/escopo. Testes de protocolo usam doubles e não validam interpretação. A suíte final desta rodada passou com **690 testes, um skip Windows e dois avisos**; Ruff passou. Recibos: `tests-final.log`, `ruff-final.log` e `preservation.json`. Os três workflows finais foram reabertos e comparados integralmente aos checkpoints, com hashes dos módulos iguais aos exercitados. Não atribuir resultados intermediários ao código final sem comparar os hashes.

Limites de execução: o Python principal não contém pytest; a primeira tentativa não executou testes, e a validação usou o ambiente de QA já existente. Uma preparação assumiu a existência do diretório opcional de objetos; o acervo principal contém apenas Bundle reference_only e não possui payloads nesse diretório. A ausência foi registrada, a preparação corrigida para esse caso, e os fluxos Snapshot finais usam seus bytes inline preservados. Não houve instalação de dependências ou substituição de bancos para resolver esses problemas.

Arquivos de implementação alterados nesta tarefa: `src/cain/research/analysis.py`, `src/cain/research/workflows.py`, `tools/verify_project_coverage.py`, `tests/integration/test_grounded_analysis.py`, `tests/test_project_coverage.py`. Documentação própria atualizada: este relatório canônico e uma atualização pontual de resultados em ANALYSIS_GUARD_20260913.md, criado por atividade concorrente. Os demais documentos concorrentes foram preservados.

| Estado da entrega | Alcance |
|---|---|
| Documentado | Matrizes, gabaritos, falhas, dependências e reprodução com fontes/recibos locais |
| Implementado | Contexto explícito, abstenção para tabelas sem rótulos no contexto e auditor por revisão/acervo no checkout |
| Testado | Recuperação real e geração/abstenção em cópias, mais testes técnicos identificados; nenhuma aprovação integral dos três casos |
| Disponível na principal | Foi detectada instalação concorrente do código `dfabf6dab05df1662e9882ebe1091236daa14724`, ainda nominalmente 0.4.12. Esta tarefa não executou instalação; conferiu três módulos instalados iguais aos casos finais e health HTTP 200. Inferência na API principal não foi exercitada nesta verificação |

Reversão: esta tarefa não executou instalação ou restauração, mas a principal avançou concorrentemente. Não restaurar o baseline antigo sobre essa instalação; qualquer reversão operacional precisa considerar o recibo e o backup próprios em C:/CAIN/work/install-dfabf6d-20260913, além de dados e decisões posteriores. Reverter o checkout não reverte o pacote instalado. Para retirar a alteração do checkout, comparar os hashes/diff atuais com os recibos finais e reverter somente os hunks desta rodada nos cinco arquivos de código/testes e neste relatório, usando `baseline/code` como referência; para a atualização pontual do documento concorrente, usar `before-doc-refresh` apenas como comparação. Não usar reset global nem restaurar diretórios/bancos; alterações concorrentes, commits posteriores, publicações e históricos precisam permanecer. A versão intermediária do contexto foi preservada em `after/code`. Se os arquivos já tiverem avançado, fazer reversão seletiva revisada, sem sobrescrever o trabalho posterior.

**Próximo incremento prioritário, não iniciado:** transportar e preservar cabeçalhos/qualificações canônicas no contexto de Brasileirão e Stocks, com aceite explícito do recorte exato e regressão semântica dos três casos antes de liberar novamente síntese livre. A recuperação relacionada de H4 já admitida é uma lacuna separada do CAIN. Nenhuma delas foi declarada resolvida por esta proteção.

## Acréscimo dos registros de hipóteses — 13/09/2026

Pedido posterior: incluir as hipóteses já registradas dos três projetos. O critério foi ampliado para os ledgers completos, definições, pré-registros sem execução e pesquisas posteriores, independentemente do que os exportadores anteriores enviavam. Não se contou trial, variante, documento ou proposta como hipótese científica nova. O inventário explícito está em `tools/hypothesis_sources.json`: 92 fontes, cada uma com caminho, finalidade e SHA-256, nos mesmos três commits registrados acima. O preparador `tools/prepare_hypothesis_catalog.py` usa ResearchSnapshotV1 e o receptor existente; não cria outro banco de conhecimento ou contrato.

| Projeto | Acréscimo examinado | Cobertura da preparação e recuperação |
|---|---|---|
| Brasileirão | 22 fontes: todas as 29 entradas de `data/trials.json`, as 29 representações migradas em `data/trials.v2.json`, registro de lógica, roadmap, Evidence Registry, protocolos de experimentos e registros de pesquisa OSS | 82 ocorrências documentais. Inclui encerradas, substituídas, inconclusivas, pré-registradas, PIT, MARKET e H14/H15; não somente os três claims de mercado. As duas representações do ledger não são 58 tentativas independentes |
| Crypto | 31 fontes: todas as 26 entradas do ledger, `scientific_state`, `HYPOTHESES.md` integral, Evidence Registry, freeze, protocolos/ledgers AR1–AR3 e BR1/BR2, carry, altcoins, Aave e registros OSS | 89 ocorrências documentais. H1–H9, inclusive H7/H8 não ativadas, e pesquisas posteriores estão no conteúdo. Backlog B e propostas não registradas permanecem texto documental, sem promoção automática a hipótese formal |
| Stocks | 39 fontes: todas as 15 entradas legadas e suas 15 representações v2, freeze e revisão histórica, estado atual, registros/protocolos e resultados H17–H22, plano prospectivo H21 e protocolos OSS | 74 ocorrências documentais. H3 permanece documentada como não executada; H17–H19 preservam a diferença entre pré-registro histórico e pesquisas posteriores; H21 não vira resultado prospectivo; H22 conserva rejeição no recorte. Os dois formatos não são 30 tentativas independentes |

São **70 entradas dos três ledgers legados**, mais 44 representações migradas e documentos complementares; **245 ocorrências não significam 245 hipóteses**. A cobertura integral comprovável é a dos arquivos explicitamente inventariados. Não há atestado de que toda hipótese existente em qualquer arquivo, branch, banco, conversa ou artefato referenciado esteja catalogada, nem um denominador universal validado de hipóteses únicas. Arquivos referenciados não materializados, fontes não inventariadas, bancos operacionais, coortes protegidas e configurações privadas permanecem fora. Não se acessaram dados protegidos para completar esse denominador.

### Implementação e manutenção

Cada entrada de ledger mantém identidade local e texto JSON original. Documentos são recebidos integralmente por recortes contíguos de até 12 mil caracteres, com offsets e hashes verificáveis; uma resposta que usa um recorte continua sem ler automaticamente o documento inteiro. `source_status` estruturado é copiado quando existe, sem normalização científica; estados presentes apenas na prosa continuam na evidência. Datas válidas de registro e execução são copiadas do ledger; datas ausentes, sem fuso e `UNKNOWN` não são adivinhadas. A disponibilidade histórica continua desconhecida. Data de empacotamento/recebimento não substitui data da informação.

Publicador explícito: `cain-local-curation`, fluxo `hypothesis-catalog`, preparador `hypothesis-catalog/2`. Esta é curadoria local do receptor, não exportação autenticada dos produtores. As identidades incluem o caminho da fonte; não foram inventadas equivalências entre nomes H e trials. A revisão depende do hash da fonte e da versão do preparador. Sem declaração canônica de substituição, revisões ficam preservadas e sem ordenação científica inferida.

O inventário fixa os bytes revisados: alteração ou ausência em qualquer fonte aborta a preparação daquele projeto antes de escrever publicações. Atualização exige revisar a diferença e atualizar conscientemente o hash; o auditor existente `verify_project_coverage.py` também compara os hashes recebidos com o checkout. Novos arquivos fora do inventário exigem revisão explícita: não existe descoberta ou sincronização automática de todo registro futuro. Reprocessamento idêntico reutiliza os arquivos endereçados por conteúdo e o receptor registra duplicação sem duplicar ocorrências. Não há exclusão de revisões anteriores.

### Validação e disponibilidade

Acervo isolado: `C:/CAIN/work/hypothesis-catalog-20260913/final`, identidade `qa-hypothesis-catalog`, uma coleção por projeto. Banco iniciado por backup consistente, política própria restrita às fontes inventariadas; não conectado à principal. `*-report.json` registra publicações/recibos/contagens; `*-retrieved.json` registra conteúdo recuperado. O piloto anterior nesse diretório de trabalho usou relógio fixo de teste; somente `final` usa o relógio real de empacotamento e a versão final com datas estruturadas.

A verificação real do receptor pagina todas as ocorrências, consulta cada identidade, pesquisa cada identidade, resolve cada evidência e compara o texto aos offsets da fonte original. Para cada documento recompõe o arquivo integral. Reimporta todas as publicações e verifica a contagem inalterada. Isso é ingestão/recuperação real em isolamento, não mock nem certificação de resposta. Testes sintéticos: 88 aprovados, um ignorado e dois avisos de depreciação no conjunto direcionado de catálogo, cobertura, receptor e análise; recibo `final-tests.log`. Não foram executados experimentos científicos dos produtores.

Os gabaritos anteriores foram preservados em `rubrics.md`. Os três workflows reais foram reexecutados sobre o catálogo final com o mesmo provedor configurado, sem filtrar uma identidade antiga que excluiria as novas fontes. `final/workflows.json` contém perguntas, configuração/digest do modelo, inspeção, resultados da busca, contexto selecionado, respostas de proteção e erro. A mudança do filtro é explícita: estes resultados não são uma comparação controlada apenas do tamanho do acervo.

| Caso | Antes desta ampliação, na rodada anterior | Depois, no catálogo isolado ampliado |
|---|---|---|
| Brasileirão / CLAIM-BR-MARKET-001 | Três abstenções no recorte exato da linha do claim | Seis etapas concluídas; suporte, contestação e síntese retornaram `abstained_unlabelled_table`. Conteúdo adicional recuperado não produziu explicação aprovada |
| Crypto / H4 | Inferência real parcial sobre dois pares JSON; motivo/amostra não acompanhavam o filtro exato H4 | Inspeção, busca e entidades concluídas; suporte falhou com `Review context exceeds budget; select a source identity`. O conteúdo ampliado inclui os motivos, mas a montagem do contexto impede a resposta deste fluxo |
| Stocks / prontidão operacional | Três abstenções no recorte exato da linha de prontidão | Seis etapas concluídas; suporte, contestação e síntese retornaram `abstained_unlabelled_table`. Ter os protocolos e estados completos no receptor não remove a limitação de seleção/contexto |

**Zero chamadas ao modelo nesta reexecução:** a proteção ou o limite de contexto atuou antes da inferência. Não se apresenta isso como teste de redação pelo LLM. As abstenções não equivalem a respostas científicas corretas ou completas. Esta ampliação fecha a lacuna de recebimento/recuperação dos arquivos inventariados no ambiente isolado, mas não fecha a interpretação, a associação automática entre todas as identidades nem o acesso na principal. O recibo `final/preservation.json` confirma os quatro repositórios consultados inalterados, política principal idêntica, registros anteriores preservados e zero publicações `cain-local-curation` na principal.

Reprodução da preparação, sem ingestão ou alteração de permissões:

```text
python tools/prepare_hypothesis_catalog.py --inventory tools/hypothesis_sources.json --domain crypto --checkout C:/CRIPTO/pesquisa-20260909 --output C:/CAIN/work/SEU_ENSAIO/publications/crypto --exported-at HORARIO_ISO_COM_FUSO
```

Usar `brasileirao` e `stocks` com seus checkouts para os outros projetos. O horário é de empacotamento e deve ser real; reutilizar o mesmo horário para repetir exatamente o mesmo pacote. A admissão continua sendo feita pelo fluxo Snapshot existente e pela política do receptor, não por esse comando.

**Documentado:** inventário, distinções e limites nesta seção. **Implementado:** preparador e inventário no checkout. **Testado:** acervo isolado e testes identificados. **Disponível na instalação principal:** este acréscimo não está disponível; não houve instalação, mudança da política principal ou admissão do acervo QA. A restrição original de preservar a principal continua aplicada ao pedido de acrescentar conhecimento. A presença dos arquivos preparados não significa que as perguntas usuais de `leo` já consultem estas fontes.

Dependências externas: produtores precisam manter registros e qualificações canônicas; para substituição futura dessa curadoria por publicação do produtor, a menor mudança é exportar as fontes e identidades faltantes sob um manifesto explícito, com revisões e escopo autorizado. CAIN não alterou esses repositórios. Admissão na principal requer uma decisão explícita sobre as novas fontes/permissões, respeitando a restrição desta tarefa; não foi feita implicitamente.

Arquivos desta ampliação: `tools/prepare_hypothesis_catalog.py`, `tools/hypothesis_sources.json`, `tests/test_hypothesis_catalog.py`, esta seção e a nota de continuidade. Reversão: retirar apenas esses três arquivos novos e as notas desta ampliação, após conferir mudanças posteriores. A cópia anterior dos documentos está em `C:/CAIN/work/hypothesis-catalog-20260913/before-*`; usar para comparação, não sobrescrever documentos inteiros. Preservar os recibos e o trabalho anterior em `ANALYSIS_GUARD_20260913.md` e neste relatório. Nenhuma restauração de banco/configuração principal é necessária ou autorizada.

**Próximo incremento prioritário, não iniciado nesta ampliação:** corrigir a montagem limitada do contexto no acervo ampliado, começando pelo bloqueio demonstrado de H4, e transportar qualificações/cabeçalhos sem extrapolação; reexecutar os três gabaritos antes de propor admissão na principal. Aumentar o acervo sozinho não resolveu a resposta.

## Correção do contexto do catálogo — continuação autorizada em 13/09/2026

O pedido posterior autorizou o incremento acima. Trabalho em `C:/CAIN/work/context-integration-20260913`, com cópias isoladas do catálogo anterior e seus mesmos gabaritos/fontes. Os três produtores, Ecosystem, política, arquivos instalados e publicações da principal foram preservados; recibo `preservation.json`. Esta continuação não admite o catálogo na principal e não instala código.

Duas correções incrementais, sem trocar modelo ou contratos de publicação:

1. **Orçamento completo:** `analysis.review` mede instruções, metadados e trechos serializados. Antes, 2.200 bytes de citações podiam gerar um pedido maior que 5.000 bytes após a inclusão de proveniência, interrompendo H4. Agora exclui trechos inteiros de menor prioridade, registra as exclusões e ajusta as referências permitidas. Se nenhum trecho couber, retorna abstenção explícita. Não corta frases ou qualificações para caber. As datas, identidades e limitações do recorte continuam presentes.
2. **Seleção e rótulos:** `grounding.cards` prioriza identificadores alfanuméricos exatos e expressões da pergunta, sem IDs específicos dos predictors. Remove a vantagem automática de JSON/tabelas e de um campo “estado” de assunto distinto na consulta ampla. Quando há candidatos com o identificador perguntado, registra a exclusão dos candidatos que não o contêm. Markdown com tabelas não esconde mais sua prosa. Uma linha de tabela recebe o cabeçalho/separador realmente presentes no mesmo trecho, preservando o intervalo literal contínuo. Se o cabeçalho estiver ausente, a proteção continua; não são inventados rótulos. Essa recuperação pode incluir linhas anteriores da mesma tabela, e não implica que o modelo interprete corretamente todas as identidades.

Versões finais: `identity_then_lexical_excerpts/5`, `addressable-review/8`, `research-workflow/12`. Checkpoints anteriores continuam legíveis, mas não são retomados misturando protocolos. Os ensaios `after` preservam a versão intermediária (`addressable-review/7`, workflow 11), inclusive cópias do código; `final` identifica os hashes da versão efetivamente carregada.

### O que foi executado e o que não foi certificado

Após a primeira correção, os três workflows de seis etapas foram reexecutados. Brasileirão e Stocks mantiveram três abstenções cada. Crypto passou a alcançar o modelo: três inferências reais, porém semanticamente reprovadas. A seleção entregara notas de H6 à pergunta H4; as redações confundiram as identidades, transportaram o veredito e inventaram interpretações sobre a alteração manual do ledger. Isso demonstrou que remover o erro de tamanho não bastava. `after/workflows.json` preserva entradas, contexto, respostas brutas e resultados de validação; não se confunde resposta bruta com resposta aceita pelo CAIN.

Na versão final, foram reexecutadas as mesmas perguntas em workflows de quatro etapas: inspeção, busca, entidades e resposta fundamentada (`support`). A configuração local `qwen3.5:4b` foi mantida. As etapas adicionais `challenge` e `synthesis` não são certificadas pela rodada final. Capturas com modelo simulado (`static-context-capture*.json`) serviram apenas para inspecionar a seleção durante o desenvolvimento; não contam como inferência real nem aprovação semântica. A seleção ampla não certifica o conhecimento inteiro de qualquer predictor.

| Predictor | Resultado final observado | Qualificação semântica |
|---|---|---|
| Brasileirão | Resposta real gerada com cabeçalho e linha CLAIM-BR-MARKET-001. Preservou `BLOCKED_PENDING_PIT_FEATURES`, ausência de comparação e limites de cobertura/features | **Parcial, não aprovada integralmente.** Atribuiu ao relatório a contagem de 2.428 trechos omitidos, que é diagnóstico do receptor. Omissões do gabarito incluem 245/245 e os três snapshots antigos. Não é prova de informação incremental |
| Crypto | Resposta real gerada sem erro de tamanho. Preservou H4, `CLOSED_INSUFFICIENT_SAMPLE`, n=5 e encerramento sem veredicto | **Parcial, não aprovada integralmente.** “Poder não documentado” e “causalidade exclusiva” pertenciam a linhas H2/H1 incluídas antes de H4, não a H4. O critério n≥30 aparece em outro trecho que remete expressamente a H4, mas as citações escolhidas não o sustentam. A resposta omite o trial e o risco de cota, conhecido na fonte completa |
| Stocks | Primeira tentativa: timeout do provedor, sem resposta. Repetição separada em `final/stocks-retry.json`: resposta bruta real, rejeitada como `INVALID_REVIEW_OUTPUT` por ter 1.119 caracteres, acima do limite de 1.000 | **Não aprovado.** A redação bruta preserva “não aptos”, mas apresenta a nota histórica de 06/09 sobre H17–H19 sem a qualificação temporal necessária, apesar da observação posterior recebida; também amplia o papel da falta de certificação do host. Não se aumentou o limite para aceitar a resposta |

A suíte ampla concluiu **703 testes aprovados, um ignorado e dois avisos de depreciação**, em `tests.log`. Dois testes adicionais, escritos depois da coleta dessa suíte, passaram separadamente (`additional-tests.log`): preferência pela expressão da pergunta sobre um rótulo histórico de outro assunto e preservação da abstenção em múltiplas linhas sem cabeçalhos. Ruff aprovado. Os testes são técnicos/sintéticos e não certificam as redações acima.

Total das duas correções e repetição: sete chamadas/tentativas reais ao provedor, seis respostas brutas e um timeout. Cinco respostas passaram o formato técnico; nenhuma aprovação semântica integral dos três casos. `semantic-review.json` registra a avaliação manual do assistente, não uma revisão independente. Nenhum erro ou resposta anterior foi apagado.

**Documentado:** alterações, matrizes, falhas e limites nesta seção. **Implementado:** orçamento, seleção e transporte literal de cabeçalhos no checkout. **Testado:** suíte e execuções reais isoladas identificadas. **Disponível na principal:** nenhuma alteração desta continuação; os três módulos instalados permanecem iguais ao baseline. O catálogo ampliado continua fora da política principal.

Arquivos desta continuação: `src/cain/research/analysis.py`, `src/cain/research/grounding.py`, `src/cain/research/workflows.py`, `tests/integration/test_grounded_analysis.py`, esta seção e nota em `CONTINUIDADE.md`. O preparador e o inventário do catálogo anterior foram preservados. Reversão: comparar esses arquivos com `context-integration-20260913/baseline` e retirar somente os hunks desta continuação, preservando as alterações anteriores e posteriores. Não restaurar bancos, diretórios ou configurações. Reverter o checkout não altera o pacote instalado.

**Próximo incremento prioritário, não iniciado:** isolar a linha da identidade perguntada dos demais assuntos da tabela sem perder seus cabeçalhos verificáveis, separar diagnósticos do receptor das afirmações da fonte e reavaliar citações/qualificações nos três casos. A integração não está liberada para admissão na principal nem certificada como conhecimento completo.

## Separação de identidades e qualificações — continuação de 13/09/2026

O usuário autorizou o incremento anterior. Evidências em `C:/CAIN/work/context-isolation-20260913`, mantendo os gabaritos, perguntas, fontes e configuração do modelo. O trabalho pré-existente no checkout foi preservado em `baseline` antes das mudanças. Não houve instalação nem conexão do catálogo à principal.

Mudança de contexto: cada linha é agora um trecho próprio, acompanhado por cabeçalhos e títulos **separados**, cada qual com referência/offset verificável. O cabeçalho não transporta mais as linhas intermediárias de outras hipóteses. Títulos delimitam o assunto de uma seção, inclusive quando ela atravessa trechos contíguos da mesma fonte/publicação já autorizada. Não se juntam revisões/publicações diferentes, lacunas ou intervalos sobrepostos; não se leem arquivos externos. Um título que atravessa uma fronteira e não possa ser representado como um único trecho literal não é fabricado. Isso não certifica a completude do documento nem uma análise geral de Markdown.

O filtro usa identidades alfanuméricas explícitas e a hierarquia de títulos, sem regras para H4, CLAIM-BR-MARKET-001 ou nomes dos predictors. Uma linha com identidade explícita tem precedência sobre um título de grupo; uma menção a outra hipótese em sua prosa não a transforma no assunto daquela seção. A evidência selecionada preserva os títulos históricos disponíveis. A API resolve e devolve também as citações dos cabeçalhos/títulos, inclusive quando se encontram em outra parte autorizada da mesma publicação. O orçamento conta o texto de todos esses componentes; não os corta silenciosamente para caber.

A primeira execução (`final/workflows.json`, prompt 9, workflow 13) concluiu quatro etapas nos três projetos, com uma inferência real por projeto. As falhas foram preservadas: Brasileirão inverteu a presença de três snapshots antigos em ausência; Crypto confundiu insuficiência/interrupção com falta de execução; Stocks datou melhor a nota antiga, mas acrescentou conclusões não sustentadas sobre dados e gates. Ter contexto melhor não foi apresentado como aprovação das redações.

A segunda correção retira **todo** `evidence_scope` do pedido ao modelo; esse diagnóstico permanece no envelope retornado pelo CAIN. Também explicita, de forma geral, que limitações não invertem presença em ausência e que insuficiência ou interrupção não implicam ausência de execução. Os títulos qualificam as datas; ausência no trecho não demonstra inexistência no projeto. O schema expressa o limite de 1.000 caracteres já existente e permite citar todos os trechos necessários, até oito; a validação continua rejeitando excesso de tamanho. Não houve aumento de limite para aceitar a resposta antes rejeitada de Stocks.

Versões finais: `identity_then_lexical_excerpts/6`, `addressable-review/10`, `research-workflow/14`. Checkpoints anteriores são preservados e legíveis, sem retomada entre protocolos. `first-code` preserva os três módulos usados na primeira execução. `second/workflows.json` registra a segunda execução real de inspeção, busca, entidades e resposta fundamentada; `challenge` e `synthesis` não são certificadas por esta rodada. A captura `final/static-context.json` usou modelo simulado e não conta como inferência real.

### Resultado desta continuação por predictor

As duas rodadas concluíram quatro etapas por projeto: seis chamadas reais ao modelo ao todo, com entradas, fontes recuperadas, contexto e respostas preservados. A avaliação manual do assistente implementador está em `semantic-review.json`; não é revisão independente. Os gabaritos anteriores não foram relaxados. A cobertura recebida continua sendo a do inventário de 92 fontes e das ocorrências demonstradas na ampliação anterior; esta correção não acrescentou fontes nem certifica todas as hipóteses possíveis.

| Predictor e caso | Antes desta continuação | Depois, segunda rodada real | Lacunas e dependências |
|---|---|---|---|
| Brasileirão / CLAIM-BR-MARKET-001 | Diagnóstico do receptor atribuído ao relatório; omissão de 245/245 e dos três snapshots antigos | Preserva bloqueio, comparação não executada, cobertura 245/245, três snapshots antigos e `no claim`. Não repete a atribuição do diagnóstico | **Parcial.** Holdout 2025 e distinção SofaScore/bookmaker continuam fora da seleção. “Recursos” traduz imprecisamente features, e a frase causal final amplia a formulação explícita do estado bloqueado. Não há aprovação integral do gabarito nem ganho incremental comprovado. Nenhuma mudança do produtor necessária para corrigir estes problemas de seleção/redação |
| Crypto / H4 | Fatos de outras linhas atribuídos a H4; motivo de cota e trial ausentes | Preserva H4, trial, `CLOSED_INSUFFICIENT_SAMPLE`, n=5, interrupção por risco de cota e ausência de veredicto; não transfere H1/H2/H6 nem afirma que nada foi executado | **Reprovado semanticamente.** Acrescenta “decisão baseada em risco financeiro, não em dados completos”, sem sustentação nos trechos. Cota operacional não autoriza essa causalidade financeira. Nenhuma mudança científica ou do produtor necessária para corrigir a extrapolação |
| Stocks / prontidão operacional | Timeout; repetição rejeitada por tamanho e com leitura histórica incorreta | Resposta aceita no formato e no limite, mantendo “não aptos” e os quatro limites de prontidão | **Reprovado semanticamente.** Ainda diz que H17–H19 “continuam sem execução real” a partir da nota antiga, apesar de reconhecer depois a observação de H17. Atribui o denominador adaptativo desconhecido a S3, mas o trecho é S4; aproxima testes técnicos e observação científica na redação. H21 e demais qualificações amplas continuam fora da seleção. Nenhuma alteração do produtor necessária para tratar a contradição temporal |

A suíte final do código efetivamente usado na segunda rodada passou com **709 testes aprovados, um ignorado e dois avisos de depreciação** (`final-tests.log`); Ruff e `git diff --check` aprovados. Testes sintéticos verificam isolamento de identidades, cabeçalhos/títulos com offsets, continuidade entre partes autorizadas, separação de publicações, orçamento e formato. Não aprovam as afirmações do modelo. `final-verification.json` confirma os hashes dos três módulos iguais aos carregados na inferência e os quatro repositórios consultados limpos, nos mesmos commits.

**Documentado:** escopo, matriz, falhas, recibos e reversão. **Implementado:** separação de linhas/identidades, títulos verificáveis e diagnóstico do receptor fora do pedido ao modelo, somente no checkout. **Testado:** suíte técnica e duas rodadas reais isoladas, com os limites acima. **Disponível na instalação principal:** nenhuma alteração desta continuação e nenhum acréscimo do catálogo; não se afirma que as consultas usuais já recebem todas as hipóteses.

**Próximo incremento prioritário, não iniciado:** tratar extrapolações causais e contradições temporais ainda demonstradas na resposta, começando pela transformação indevida de risco de cota em risco financeiro em H4; reexecutar os três gabaritos. A seleção incompleta de qualificações também permanece registrada. Não trocar modelo, alterar conclusões das fontes ou admitir o catálogo na principal para contornar essas falhas.

## Revisão crítica e teste ampliado — 14/09/2026

O usuário pediu revisão do que foi feito, correções e teste amplo do CAIN. Baseline desta revisão: `main`, `3f88a2535f08c70bce561cd3822e7558cebec326`, com as dez alterações/adições locais anteriores preservadas em `C:/CAIN/work/review-full-20260914/baseline`. Os quatro repositórios consultados continuam nos commits anteriores, limpos. A revisão mantém o escopo de implementação no CAIN e não autoriza instalação ou admissão do catálogo na principal.

**Decisão de revisão:** manteria o inventário explícito, as fontes literais, os gabaritos anteriores à mudança e os ensaios isolados. Não repetiria ajustes sucessivos de instrução como se garantissem interpretação correta, nem usaria só a etapa de suporte para avaliar um workflow com contestação e síntese. A revisão testa também os limites do recebimento e da montagem do contexto.

Falhas reproduzidas e corrigidas até esta etapa:

- Registros JSON com chaves duplicadas, inclusive aninhadas, e valores `NaN`/`Infinity` eram admitidos pelo preparador. O decoder agora os rejeita antes de escrever publicações. As fontes legítimas preservam os mesmos bytes e identificadores; não foi necessário mudar `hypothesis-catalog/2`.
- Comentários `#` em blocos de código eram interpretados como títulos e podiam excluir a hipótese correta. A leitura de títulos agora respeita cercas de crases e tils. Não se declara suporte integral a todo Markdown.
- Propostas anteriores eram cortadas em 200 caracteres, podendo perder a ressalva final. Agora entram inteiras ou são omitidas com diagnóstico explícito; são descartadas antes de retirar evidência da fonte por orçamento. As citações devolvidas também identificam o trecho (`excerpt_id`) para permitir conferir atribuições como S1/S2 sem inferir a ordem.

Sete testes reproduziram as duas primeiras falhas; dois reproduziram o corte das propostas. A suíte após essas correções passou com 718 testes e um ignorado. Uma reprodução posterior, em três testes, mostrou que a função da etapa estava apenas no JSON de contexto, enquanto a instrução principal era igual. O workflow real de Brasileirão repetiu a mesma resposta em suporte, contestação e síntese.

A tentativa seguinte promoveu a função da etapa para a instrução principal e reservou propostas anteriores para a síntese. Passou em **721 testes**, mas a execução real voltou a descrever uma comparação bloqueada/não executada como executada em Brasileirão. **A tentativa foi rejeitada e retirada.** `third/workflows.json`, `rejected-role-code` e `role-rejection.json` preservam essa evidência. Brasileirão e Crypto concluíram seis etapas; Stocks teve erro do provedor/timeout e o revisor cancelou as etapas restantes da variante já rejeitada. Não se atribui o timeout à mudança textual nem ao cancelamento sem prova, e não se declara essa rodada integralmente concluída.

Na rodada anterior de Stocks, a síntese tinha exatamente 1.000 caracteres e terminava em “e a c”, apesar de ser JSON válido. Um teste negativo reproduziu a aceitação de uma resposta cortada por um provedor que aplica `maxLength`. A versão retida remove esse teto do schema enviado ao modelo e **mantém o limite de 1.000 caracteres na validação do CAIN**: excesso é recusado, sem cortar a resposta para fazê-la passar. Isso trata o risco de corte pelo formato; não certifica completude semântica nem resolve sozinho as extrapolações do modelo.

Versão retida: seletor `identity_then_lexical_excerpts/7`, prompt `addressable-review/13`, workflow `research-workflow/18`. A suíte completa passou com **719 testes, um ignorado e dois avisos** (`reviewed-tests.log`); Ruff aprovado. As três expectativas específicas da abordagem rejeitada foram retiradas com ela, e o teste do corte pelo schema foi incluído. A limitação da contestação independente continua aberta; não se apresenta repetição da mesma resposta como debate validado.

O preparador foi reexecutado com as 92 fontes e o horário de empacotamento original: Brasileirão 22 fontes/82 ocorrências; Crypto 31/89; Stocks 39/74. Recuperação de cada ocorrência, offsets, reconstrução dos documentos e reimportação sem duplicação passaram; os identificadores das publicações ficaram iguais aos anteriores. `catalog/*-report.json`, `catalog/*-retrieved.json` e `coverage-audit.json` registram os resultados. Isso não estabelece total de hipóteses únicas, descoberta automática de futuros documentos ou entendimento correto de tudo que foi recebido.

Recibos desta revisão ficam somente em `C:/CAIN/work/review-full-20260914`. `final/workflows.json` preserva a rodada de quatro etapas após a correção do parser; `second/workflows.json` registra o workflow de seis etapas após preservar propostas inteiras; `third` é a tentativa rejeitada; `fourth/workflows.json` registra o reteste concluído da versão retida, incluindo a falha de Stocks. As versões carregadas e os textos brutos estão nos recibos. Os testes gerais estão no [teste integral](TESTE_INTEGRAL_20260912.md), sem apagar falhas intermediárias.

### Resultado final separado por predictor

| Predictor, escopo e caso | Cobertura comprovada e lacunas | Antes da revisão | Versão retida: execução real e avaliação | Dependências externas |
|---|---|---|---|---|
| Brasileirão — 22 fontes inventariadas, 82 ocorrências/revisões; contratos, hipóteses, protocolos, registros e decisões. Caso CLAIM-BR-MARKET-001 | Todas as ocorrências do inventário recuperadas em QA. A linha do claim entra no contexto; qualificações recebidas sobre holdout 2025 consumido e distinção SofaScore/bookmaker continuam fora da seleção. Artefatos apenas referenciados não se tornam conteúdo disponível | Parcial, com tradução imprecisa de features e formulação causal mais ampla que o registro | Seis etapas, três chamadas reais, três textos iguais. Preserva bloqueio, comparação não executada, 245/245, três snapshots antigos e `no claim`. **Parcial:** não atende ao gabarito amplo nem demonstra contestação efetiva; imprecisões persistem | Nenhuma mudança no produtor necessária para os problemas de seleção/redação demonstrados. Exportação autenticada de futuros registros/artefatos autorizados continua dependência do produtor |
| Crypto — 31 fontes, 89 ocorrências/revisões; hipóteses, trials, charters, decisões e limites. Caso H4 | Todas as ocorrências inventariadas recuperadas em QA. Trechos selecionados sustentam H4/trial/n=5/cota/sem veredicto; acervo e artefatos não inventariados continuam fora do conhecimento comprovado | Reprovado: transformava risco operacional de cota em risco financeiro | Seis etapas, três chamadas reais. A síntese preserva o núcleo do gabarito selecionado. **Workflow reprovado semanticamente:** suporte extrapola ausência de resultado observável; contestação acrescenta “não por falha técnica observada”, sem sustentação. A aprovação restrita da síntese não apaga essas falhas | Nenhuma mudança científica ou do produtor necessária para corrigir extrapolações. Novos registros/fontes autorizados exigem manutenção do inventário e emissão pelo produtor, sem copiar bancos indiscriminadamente |
| Stocks — 39 fontes, 74 ocorrências/revisões; hipóteses, protocolos, observações e prontidão. Caso retorno líquido pessoal/operação real | Todas as ocorrências inventariadas recuperadas em QA. Estado de prontidão, RUNBOOK_H18 histórico e observação posterior de H17 foram selecionados. H21 e qualificações amplas continuam fora deste recorte; referências não materializadas permanecem referências | Reprovado: histórico de H17–H19 apresentado como atual, atribuição incorreta e aproximação de testes técnicos com observação científica | Suporte e contestação retornaram; cinco etapas completas. A terceira chamada gerou 1.092 caracteres e foi recusada com `INVALID_REVIEW_OUTPUT`, preservando o teto de 1.000. **Workflow falhou, sem síntese aceita.** O suporte e a resposta bruta final mantêm a contradição temporal; “não aptos” não basta para aprovação. Contestação melhorou a atribuição, sem resolver integralmente a interpretação | Nenhuma alteração no produtor necessária para reconciliar as fontes já disponíveis. Qualquer nova evidência/execução científica ou exportação autenticada pertence ao produtor e não foi realizada aqui |

O último reteste fez **nove chamadas reais ao provedor, três por predictor**. Os contadores persistidos do workflow registram 3/3/2 gerações bem-sucedidas; a última de Stocks recebeu saída bruta e a rejeitou na validação, não foi timeout. `fourth-receipts-verified.json` confirma reabertura igual dos checkpoints e 9/28/20 citações literais verificadas; isso não certifica sustentação de cada afirmação. A análise manual por fase está em `semantic-review.json`, feita pelo assistente implementador, sem revisão humana independente.

A síntese intermediária de Stocks tinha sido aceita com 1.000 caracteres e final cortado; a versão retida recusa o excesso sem fabricar completude. Não se elevou o limite nem se tentou repetidamente gerar até obter aprovação. Propostas anteriores que não cabem no orçamento são omitidas por inteiro e diagnosticadas; na síntese final de Stocks nenhuma coube. Isso limita o que se pode afirmar sobre revisão das etapas anteriores.

**Documentado:** gabaritos, cobertura, falhas intermediárias/finais e reversão. **Implementado:** correções incrementais no checkout. **Testado:** 719 testes locais aprovados, um ignorado, Ruff, pacote isolado e os fluxos reais descritos. **Disponível na instalação principal:** nenhuma alteração desta revisão; zero publicações do catálogo local. Não está comprovado que o CAIN principal tenha todas as hipóteses de todos os projetos. `final-preservation.json` confirma bancos íntegros, todas as linhas anteriores preservadas, configurações e módulos instalados iguais ao baseline e os quatro repositórios consultados inalterados.

**Próximo incremento prioritário, não iniciado:** corrigir a reconciliação temporal e a seleção das qualificações necessárias, começando pela contradição de Stocks entre a nota antiga e a observação posterior de H17; exigir conclusões limitadas às fontes e reexecutar os três gabaritos. A falha causal de H4 e a contestação inefetiva de Brasileirão permanecem regressões explícitas. Não trocar modelo ou instalar o catálogo para contornar esses resultados.

### Manutenção e reversão da revisão de 14/09

Continuam valendo o inventário explícito, commit e hashes de cada fonte, identificação de publicações/revisões, relatório de cobertura e reprocessamento idempotente existentes. O auditor foi reexecutado contra os checkouts atuais. Data de ingestão não foi promovida a data da informação; relógios de fonte desconhecidos continuam desconhecidos. Novos documentos fora do inventário não são descobertos automaticamente, e referências a artefatos não materializam seu conteúdo. Essas lacunas exigem revisão do inventário autorizado; exportação autenticada e atualização emitida pelo produtor continuam dependências externas, sem implementação nos produtores nesta tarefa. Não se promete sincronização completa ou verdade científica atual a partir de hashes iguais.

Arquivos alterados **nesta revisão**, comparados ao baseline local anterior: `tools/prepare_hypothesis_catalog.py`, `src/cain/research/grounding.py`, `src/cain/research/analysis.py`, `src/cain/research/workflows.py`, `tests/test_hypothesis_catalog.py`, `tests/integration/test_grounded_analysis.py`, `docs/COBERTURA_PROJETOS_20260913.md`, `docs/TESTE_INTEGRAL_20260912.md` e `CONTINUIDADE.md`. As alterações anteriores em `docs/ANALYSIS_GUARD_20260913.md` e `tools/hypothesis_sources.json` foram preservadas, sem nova edição nesta revisão.

Reversão: comparar cada arquivo com sua cópia em `C:/CAIN/work/review-full-20260914/baseline` e retirar somente os hunks desta revisão, conferindo trabalho posterior antes de aplicar. Não restaurar o checkout inteiro nem bancos/configurações. Manter os recibos históricos; o pacote instalado continua inalterado. Os wheels intermediários são evidência de teste, não autorização para instalação; somente `dist-reviewed` corresponde à implementação retida.

Preservação: `preservation.json` confirma os três predictors e Ecosystem inalterados, política principal idêntica, módulos instalados preservados, registros/publicações anteriores mantidos e zero publicações do catálogo local na principal. Não existe dependência de mudança nos produtores para estas correções; seus registros e conclusões não foram alterados.

Arquivos desta continuação: `src/cain/research/grounding.py`, `src/cain/research/analysis.py`, `src/cain/research/workflows.py`, `tests/integration/test_grounded_analysis.py`, esta seção e `CONTINUIDADE.md`. Reversão: comparar com `context-isolation-20260913/baseline` e retirar somente os hunks desta continuação, preservando todo o trabalho anterior e posterior. Não restaurar bancos/configurações ou apagar recibos. O pacote instalado não foi alterado.
