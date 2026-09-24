# CAIN — Prompt 1: auditoria (somente leitura), 2026-09-24

- **Repositório:** `leonardosovienski/cain`, `main` @ `5d55732083616f7f01784ffe9e82e9dc76b8463e` (inclui os PRs #42–#44 de 24/09).
- **Onde:** PC 2 (Ubuntu 24.04/WSL2). Leitura num worktree destacado (`~/predictors/work/auditoria-cain`); testes numa cópia
  `git archive` do mesmo commit (`~/predictors/runtime/cain-auditoria/src-5d55732`) com venv do `uv.lock`.
  **Nenhum arquivo do repositório foi alterado e nada foi commitado.**
- **Legenda.** **PROVEN** = código no caminho de runtime (alcançável de `cain`, `cain-mcp` ou da API) lido nesta auditoria,
  com a suíte passando ou com comando executado aqui. **DECLARED** = só em documentação, comentário, teste ou nome.
  **AUSENTE** = não encontrado no código.
- **Limite importante:** o PC 2 não tem Ollama nem llama.cpp (`127.0.0.1:11434` sem resposta; binários ausentes).
  **Nenhuma inferência real foi executada.** Os caminhos com modelo estão verificados como código no runtime + testes com
  modelo falso (`FakeLLM`/dublês), nunca com um modelo de verdade.

## 0. Resultado dos testes (item 6)

| Comando (na cópia do commit) | Resultado real |
|---|---|
| `uv lock --check` | OK |
| `uv sync --locked --extra dev --extra vision` | OK |
| `ruff check .` | `All checks passed!` |
| `pytest -q` — CPython **3.14.7** | **1159 passed, 3 skipped, 0 failed, 0 errors** (55,6 s) |
| `pytest -q` — CPython **3.13.15** | **1159 passed, 3 skipped, 0 failed, 0 errors** (49,3 s) |
| `python -m cain --help` | exit 0 |

Os 3 pulados: dois "Windows launcher only" (`tests/integration/test_research_failures.py`) e um
`test_new_tables_legacy_snapshot_read` ("Historical baseline absent from shallow checkout"). Este último pula porque a cópia
`git archive` não tem histórico git: é causa do ambiente de teste, não do código. Num clone completo ele roda; na conferência da
madrugada, no clone, foram 1160 passed e 2 skipped. Logs: `runtime/cain-auditoria/raw/testes*.log` e `pytest*.junit.xml`.

## 1. Mapa

| Superfície | O que existe | Evidência |
|---|---|---|
| Entrypoints | `cain` (CLI), `cain-mcp` (MCP stdio), `cain-stream` | `pyproject.toml` `[project.scripts]` |
| CLI | `run`, `chat`, `profile`, `doctor`, `archive`, `research …` (`import`, `query`, `search`, `inspect`, `evidence`, `history`, `recall`, `coverage`, `receipts`, `verify`, `rebuild`, `explain`, `bundle …`, `workflow`/`job`/`jobs`/`advance`/`cancel`/`abstain`/`trace`, `backup`, `restore`) | `src/cain/cli.py:88`, `src/cain/research/cli.py:8-107` |
| API HTTP (FastAPI) | `/run`, `/runs/{user}/{run}`, `/profile/…`, `/projects/…/documents`, `/sessions/…`, `/feedback/{turn}`, `/research/*` (bundles, query, inspect, coverage, explain, evidence, capabilities, readiness, history), `/research/jobs/*` (workflows), `/assistant/stream`, `/assistant/models`. Só loopback; fora dele exige `CAIN_API_TOKEN` | `src/cain/api.py:115-372`, `src/cain/research/api.py:80-255`, `src/cain/research/agent_api.py:58-140` |
| Interface web | SPA estática (`index.html`, `app.js`, `style.css`) servida pela API | `src/cain/web/`, `src/cain/api.py:372` |
| MCP | 4 ferramentas somente leitura: `research_query`, `research_search`, `research_inspect`, `research_evidence`; escopo fixo por processo | `src/cain/mcp.py:15` |
| Motor de workflows | `Workflows`: tabelas `agent_jobs`/`agent_steps`/`agent_attempts`, 6 etapas fixas (`inspect, search, entities, support, challenge, synthesis`), avanço explícito passo a passo | `src/cain/research/workflows.py:16-235` |
| Memória | (i) identidade e preferências por escopo; (ii) conversas (`ui_sessions`/`ui_turns`); (iii) documentos do projeto (`project_documents`, por `content_hash`); (iv) acervo de pesquisa L0 (`publications` com `raw` imutável + projeções `records`/`membership`); (v) bundles; (vi) cache de embeddings | `persistence/adapters/sqlite.py:42-67`, `workspace.py:20-56`, `research/schema.py:7-33`, `research/bundle_schema.py`, `search/embeddings.py:138` |
| Recuperação | `HybridDocumentRetriever` (léxico + cosseno; embedding local com **digest obrigatório**); busca léxica no acervo de pesquisa; seletor de trechos `cards` com offsets | `search/hybrid.py:14-35`, `research/grounding.py:26` |
| Auditoria | `SQLiteDecisionLog`: append-only por triggers e **hash encadeado** com `verify_chain`; `receipts`/`queries` do acervo; `agent_attempts`; `trace` em JSON no formato OTLP | `persistence/adapters/sqlite.py:253-372`, `research/workflows.py:150` |
| Modelos locais | **Ollama** (`/api/generate`, `format` = JSON Schema) é o padrão; **llama.cpp server** (`/completion`, `json_schema`) via `LocalLlamaCppLLM`; serialização `qwen35`; só loopback (`allow_remote` explícito) | `llm/__init__.py:54-167`, `llm/llamacpp.py:27-120`, `settings.py:13` |
| "Agentes" | roteador por regras (LLM opcional) + agente de aritmética. **Não há agente autônomo** | `orchestrator/routing.py:62-246`, `agents/arithmetic.py` |
| Integração com predictors | `TaskOutbox`/`ResultInbox` (V1, só cripto): **não alcançáveis de nenhum entrypoint**. Ingestão de Snapshot/Bundle (determinística, sem LLM) alcançável | `research_tasks.py:17`, `research_results.py:20`; conferência da madrugada |

## 2. Memória (item 2)

| Pergunta | Resposta | Classe |
|---|---|---|
| Modelo de dados | Ver mapa. Não existe tabela genérica de "fatos"; há identidade/preferências, conversas, documentos, acervo L0 e bundles. | PROVEN |
| Noção de tempo válido × registrado | **Nos dados, sim; na consulta, não.** O contrato Snapshot exige em cada registro `event_at`, `recorded_at`, `available_at` e `supersedes`, validados na importação, e `publications.received_at` guarda quando chegou. Mas `ResearchService.query()` filtra só por `domain/source_id/kind/status/revision/text`. | dados: PROVEN (`research_snapshot` `validate`, `research/schema.py:9`, `research/inspection.py:10`); filtro temporal: **AUSENTE** (`research/service.py:152-250`) |
| Consulta "como estava na data X" | **AUSENTE.** Não há `as_of` em memória, busca vetorial nem acervo. O mais próximo: `identity_snapshots` (histórico da identidade por `recorded_at`, lido por `history()`) e o workflow preso à impressão digital do corpus (`guard(fingerprint)`), que recusa continuar se o corpus mudou. | PROVEN (o que existe) / AUSENTE (as_of) |
| Algo é sobrescrito? | **Sim:** estado de identidade (`ON CONFLICT … DO UPDATE`, `sqlite.py:111`, `UPDATE identities`, `:174`) e preferência corrente por local (`DO UPDATE SET record_json`, `:184`). A história fica em `identity_snapshots` e `identity_signals` (append). Também `run_receipts.status`, `agent_jobs.status`, `task_outbox.status` e `ui_sessions.title`. | PROVEN |
| Algo é apagado? | Só projeções reconstruíveis: `verify --rebuild` apaga `records`/`membership` do escopo e as refaz a partir de `publications.raw` imutável (`research/service.py:463-520`); o mesmo para bundles (`research/bundles.py:455-475`). Nenhum `DELETE` de dado de origem encontrado. | PROVEN |
| Revisões | Registros com `revision` e `supersedes`; `inspection` acusa `superseded_revision_not_received`. As duas revisões ficam preservadas. | PROVEN (`research/inspection.py:106-114`) |

## 3. Evidências e citações (item 3)

| Pergunta | Resposta | Classe |
|---|---|---|
| A resposta pode citar algo não persistido? | No caminho de pesquisa, **não**. `analyze_text` exige `source_ids` presentes no mapa de evidências; referência desconhecida é erro. Relações de `entities` exigem `quote in evidence[ref]` (`analysis.py:149`). O caminho de conversa geral (`/run`, `chat`) **não** tem citação estruturada. | PROVEN (pesquisa) |
| Citação com trecho literal + offset + hash | **Parcial.** (1) Na importação, cada evidência do Snapshot tem `text`, `start`/`end` em code points Unicode, `locator` e `sha256` **do trecho** (não do documento inteiro); o contrato recusa offset incoerente ou hash divergente. (2) `cards()` seleciona trechos exatos com offsets. (3) A validação da proposta do modelo (`validate_proposal`) confere **substring com espaços normalizados em qualquer lugar do trecho**, não `doc[start:end]` exato, e exige ≥ 12 caracteres. | (1)(2) PROVEN; (3) PROVEN, mas mais fraca que o Prompt 3 pede (`grounded_analysis.py:105-137`) |
| Números sem fonte | `unsupported_numbers` recusa números da análise que nenhum trecho citado, contexto ou registro contém (PR #44, 24/09); a revisão marca `release_status = withheld_pending_external_review` | PROVEN (`analysis.py:156`, `answer_review.py:76-131`) |
| Objeto Claim com status | **AUSENTE.** `claim_tables.py` só transcreve tabelas de claims da fonte (`literal-claim-table/1`), sem estado nem verificador. | — |

## 4. Workflows (item 4)

| Pergunta | Resposta | Classe |
|---|---|---|
| Retomada | Durável em SQLite: cada etapa concluída vira `agent_steps`; `advance` retoma da próxima; *lease* de 600 s com `recover` explícito; falha exige `recover` ou `abstain` (registrado); cancelamento. Trabalho preso ao corpus (`fingerprint`), ao modelo (`model_identity`) e ao protocolo (`research-workflow/19`). | PROVEN (`workflows.py:168-235`) |
| Pausa para aprovação humana | **Parcial e não durável como decisão.** Etapas de geração exigem `approve_generation=True` na chamada; sem isso volta `awaiting_generation_approval`, mas esse estado **não é gravado** (o job fica `ready`). Não há registro de quem aprovou, quando ou o quê. **A web sempre envia `approve_generation:true`** (botões "Executar próxima etapa" e "Executar etapas restantes"). | PROVEN como código; como governança, DECLARED (`workflows.py:178-179`, `web/app.js:724,730`) |
| Ramificar a partir do passo N | **AUSENTE.** Um `run_id` fica preso ao pedido e ao corpus; não há `parent_run_id`/`fork_point`. | — |
| Etapas idempotentes | Resultado aceito só com a *claim* do lease ainda válida; conflito concorrente → erro; tentativas registradas | PROVEN |

## 5. Reprodutibilidade de inferência (item 5)

| Registrado por chamada | Onde | Observação |
|---|---|---|
| `model`, `done_reason`, contagem de tokens de prompt e saída, `total/load/eval_duration`, `input_bytes`, `num_ctx`, `num_batch`, `think`, `structured_output` | `llm/__init__.py:153-160` (`last_metadata`) | em toda chamada Ollama |
| `temperature`, `seed` (padrão 0,0 e 42), `num_ctx`, `num_predict` | enviados em `options` (`llm/__init__.py:110`); **gravados** só nos recibos do historiador e do workflow | não em toda chamada |
| digest do modelo (Ollama `/api/tags`) | `workflows.model_identity` (`workflows.py:21`), `evaluation/functional.py:81-98`, embeddings (obrigatório) | não na conversa geral (`/run`) |
| hash do prompt | `analysis.py:152` (`instruction + prompt`), `historian.py:215`, `streaming.py:101` (`input_sha256`) | não é o prompt **renderizado pelo template do runtime**, e sim o texto enviado |
| hash da saída | `DecisionRecord.response_hash` | no log de decisões |
| saída estruturada pelo runtime | Ollama `format` = schema; llama.cpp `json_schema` | PROVEN como código |
| **não registrado** | quantização, hash do GGUF, versão/build do runtime (exceto `backend_version` no avaliador funcional), backend CPU/GPU, hash de tokenizer e template, `top_p/top_k/min_p`, ordem dos samplers, nº de slots/paralelismo, commit do CAIN e lockfile por chamada, cache de geração com replay | AUSENTE |
| replay | `evaluation/v2_replay.py`: reenvia requisições **capturadas** ao backend, só como diagnóstico. Não é cache de replay. | PROVEN (diagnóstico) |

Nada foi medido aqui: sem modelo local no PC 2.

## 6. Capacidades

| Capacidade | Runtime real? | Evidência |
|---|---|---|
| Log de decisões append-only com hash encadeado e verificação | **PROVEN** (sha256 de `previous\ndecision_id\nrun_id\nrecord_json`, com `json.dumps(sort_keys=True)`, **não JCS**) | `persistence/adapters/sqlite.py:253-372` |
| Acervo imutável + projeções reconstruíveis (`verify --rebuild`) | **PROVEN** | `research/schema.py:9`, `research/service.py:463-520` |
| Datas de evento/registro/disponibilidade nos registros | **PROVEN** (dados) | contrato `research_snapshot`, `research/inspection.py:10` |
| Consulta `as_of` (memória, acervo, vetor) | **AUSENTE** | `research/service.py:152-250` |
| Fatos com `valid_from/valid_to/superseded_at` | **AUSENTE** | — |
| Evidência com offset + sha256 do trecho | **PROVEN** (na importação) | contrato `research_snapshot` |
| Citação literal por offset exato na resposta do modelo | **parcial** (substring normalizada) | `grounded_analysis.py:105-137` |
| Bloqueio de número sem fonte | **PROVEN** (léxico; retém, não bloqueia a gravação) | `analysis.py:156`, `answer_review.py:123` |
| Claim com estados e verificadores (HHEM/MiniCheck) | **AUSENTE** | — |
| Workflow durável e retomável | **PROVEN** | `research/workflows.py` |
| Aprovação humana durável com registro | **AUSENTE** (gate por argumento; a web aprova sempre) | `workflows.py:178`, `web/app.js:724` |
| Fork de run | **AUSENTE** | — |
| Manifesto de inferência completo | **parcial** (ver seção 5) | — |
| Cache/replay de geração | **AUSENTE** (só replay diagnóstico) | `evaluation/v2_replay.py` |
| Harness de avaliação de modelos | **PROVEN como código** (`python -m cain.evaluation`: smoke, quality, v2); tabelas de resultado com modelo real **não reproduzidas aqui** | `evaluation/` |
| Trace no formato OTLP | **PROVEN** (JSON; sem exportador nem convenções `gen_ai.*`) | `workflows.py:150` |
| MCP local somente leitura | **PROVEN** | `mcp.py:15` |
| Integração com predictors fora da V1 | **AUSENTE** (V1 inalcançável; V2 = Etapa B) | `research_tasks.py`, `research_results.py` |
| Agente autônomo | **AUSENTE** | — |

## 7. Premissas dos prompts seguintes que não batem com o código

1. **`predictor_core` não tem `RunManifest`, `TrialLedger`, `DecisionPolicy`, `Episode`, `EvaluationReport` nem
   `GovernanceTransition`** (0 ocorrências em `src/` no `main` 5a08415). "Evaluator" só aparece como
   `PrequentialEvaluator`, uma classe abstrata em `predictor_core.testing`. O que existe e dá para reaproveitar:
   `JsonlStore` (JSONL append-only, sem cadeia de hash nem forma canônica), `TrialRegistryV2` (append-only por `trial_id`,
   reescreve o arquivo, sem cadeia), `DatasetFreeze`, `dataset_fingerprint`, `config_hash`, `measurement.replay`.
   **Os prompts 6 e 7 do CAIN dependem do Prompt 2 do `01-core.md`.** Isso bate com a ordem recomendada (core antes do CAIN).
2. **`core-predictor` está congelado pela qualificação** (Etapas A/B). Todo contrato novo no core vira release nova +
   `STACK_BASELINE_V1.<n>` + C14 nas três missões. Hoje o CAIN nem depende do `predictor-core`.
3. **O "log com hash encadeado" do Prompt 2 já existe em parte** (`SQLiteDecisionLog`). Mas ele não é JCS e só cobre
   decisões da conversa. Estender ou reaproveitar esse padrão é melhor que criar um segundo.
4. **"Evidence" do Prompt 3 já existe em parte** no contrato Snapshot (trecho, offsets, sha256 do trecho). Faltam o sha256 do
   documento inteiro e a validação `doc[char_start:char_end] == quote` exata na resposta do modelo.
5. **Aprovação do Prompt 4:** o motor atual já é durável; falta só a primitiva. É um argumento a favor de "manter o motor e
   adicionar as primitivas".
6. **Ciclo real com predictor (Prompts 6 e 7):** hoje não há caminho CAIN → predictor fora da V1 (D-13). O caminho novo é a
   Etapa B: `predictor-research-protocol` 2.0.0rc1 (envelope V2, publicado em 24/09) + adapters. Um "ciclo real ponta a ponta"
   antes da Etapa B só daria para fazer lendo resultados já publicados (Snapshot/Bundle), não disparando experimentos.
7. **Etapa B × estes prompts:** a Etapa B (qualificação) exige baseline do `cain` antes de qualquer mudança da missão, e
   depois disso toda mudança no `cain` = C14 das fases da integração. Mudanças grandes dos prompts 2–10 no `cain` **antes**
   do baseline da Etapa B entram no baseline; **depois**, obrigam a refazer fases. Isso é decisão de sequência para o dono.
8. **Harness do Prompt 5:** já existe `cain.evaluation` (smoke, quality, v2, replay). O Prompt 5 deve estender, não criar
   outro. Os números reais precisam de uma máquina com Ollama (o PC 2 não tem).

## 8. Lacunas (resumo)

`as_of` inexistente; memória de identidade sobrescrita (com histórico); sem Claim/status/verificador; citação literal
normalizada em vez de por offset; sem hash do documento inteiro; aprovação humana sem registro e sempre concedida pela web; sem
fork; manifesto de inferência parcial e desigual entre caminhos; sem cache de geração; trace sem exportador; sem ciclo com
predictor fora da V1; nenhuma inferência verificada nesta máquina.

## 9. Plano em etapas pequenas

Cada etapa: um PR, teste que falha antes e passa depois, caminho de runtime, relatório em `docs/evidence/`.

**(a) Memória bitemporal + `as_of`**
1. `as_of` no acervo L0 primeiro: filtro `recorded_at <= T` (e `available_at <= T` quando existir) em `query`/`search`/`inspect`,
   usando os campos que o contrato Snapshot já valida. Teste de vazamento com registro futuro. Reaproveita a importação existente.
2. Tabela `facts` bitemporal só para memória **derivada** (texto livre), com `superseded_at` no lugar de update. Toda leitura
   passa por um `as_of` obrigatório (assinatura sem padrão).
3. `received_at`/`published_at` nos documentos do projeto e filtro no `HybridDocumentRetriever` **antes** da busca vetorial.
4. Log de eventos: estender o padrão do `SQLiteDecisionLog` para JCS (RFC 8785) e para eventos de memória; `rebuild-index`
   generalizando o `verify --rebuild` que já existe.

**(b) Evidence/Claim + verificação**
1. `doc_sha256` + validação exata `doc[start:end] == quote` no caminho do modelo (hoje é substring normalizada).
2. Objeto `Claim` com estados e `kind` (TEXTUAL_SUPPORT × EMPIRICAL_PROOF); o `unsupported_numbers` vira o linter que bloqueia publicação.
3. Verificadores locais (HHEM-2.1-Open; MiniCheck-Flan-T5 depois de conferir a licença) só numa máquina com os pesos, com
   golden set congelado e acurácia medida (inclusive em português).

**(c) Aprovação humana durável + fork**
1. Manter o motor atual (já é durável em SQLite, com lease e tentativas). A comparação com DBOS/LangGraph fica para o Prompt 4.
2. `ApprovalRequest` gravado quando a etapa pede aprovação; `HumanApproval` como evento imutável; a web deixa de mandar
   `approve_generation:true` automaticamente.
3. Fork: `parent_run_id` + `fork_point`, copiando as etapas `< N` por referência.

**(d) Manifesto de inferência local**
1. Um único `InferenceManifest` montado em `OllamaLLM._generate`/`LocalLlamaCppLLM._generate` (hoje os campos estão espalhados
   entre `last_metadata`, `model_identity` e recibos): digest (`/api/tags`), `/api/show` (quantização, template, parâmetros),
   versão do runtime (`/api/version`), opções efetivas, hash do corpo exato enviado, hash da saída, commit e lock.
2. Modo registro (1 requisição por vez) e cache por chave com replay, que é a reprodutibilidade real.

**(e) Harness de avaliação de modelos locais**
1. Estender `cain.evaluation` com tarefas congeladas (extração, classificação de evidência, resumo com citação) e gabarito.
2. Rodar numa máquina com Ollama e os modelos candidatos (licenças conferidas no HF), com tabela real: acurácia, latência e RAM.

**Reaproveitar do `predictor_core`, sem duplicar:** `JsonlStore` como camada de eventos, se o CAIN passar a depender do core;
`dataset_fingerprint`/`config_hash` para hashes de entrada; `TrialRegistryV2` para pré-registro. `RunManifest`/`TrialLedger`
**não existem**: nascem do Prompt 2 do `01-core.md`, sujeitos ao congelamento da qualificação (seção 7, itens 1 e 2).

## 10. Evidência bruta desta auditoria

Logs brutos, sem edição, em `docs/evidence/2026-09-24-prompt1/`:

| Arquivo | sha256 |
|---|---|
| `testes-py3.14.log` | `abfe34f8c545f60954dd465b5d69ad476698d6cdcfe1e1ecd6118b9caf09b9db` |
| `testes-py3.13.log` | `f1869f205ed6c896340c8d45d603c1e43c97dbaf46710470a46d8dd357d5f62b` |

A auditoria foi somente leitura. Este relatório foi commitado depois, junto com o Prompt 2, porque o procedimento guarda
cada relatório de etapa em `docs/evidence/`.
