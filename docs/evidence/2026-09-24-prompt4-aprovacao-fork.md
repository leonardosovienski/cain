# CAIN — Prompt 4: aprovação humana durável e fork de runs (2026-09-24)

Branch `melhorias/p4-aprovacao-fork`, cumulativa sobre o Prompt 3. Tudo local; nenhum segredo. A demo roda com o
modelo real `qwen3.5:4b` (Ollama 127.0.0.1 no WSL2, na GPU NVIDIA RTX 2060 6 GB via CUDA, com todas as camadas na
VRAM; CPU i7-12700F, 16 GB de RAM).

## Antes de codar: qual motor

O motor atual já era durável: SQLite, etapas explícitas (`advance`), resultado persistido uma vez por posição, lease
de 600 s com `claim` e recuperação explícita (`recover`). Faltavam duas primitivas: a espera por decisão humana e o
fork. Comparação pelo peso operacional para uma pessoa rodando local:

| Opção | O que traz | Custo para este caso |
|---|---|---|
| **DBOS Transact Python** | Workflows duráveis como biblioteca; banco de sistema Postgres ou SQLite (SQLite é suportado e é o padrão sem configuração, mas a própria documentação recomenda Postgres em produção). Espera durável por evento. | Tabelas de sistema próprias, em paralelo às do CAIN; funções de workflow precisam ser determinísticas; os runs e a trilha existentes teriam de migrar. Duas fontes de verdade para o estado de um run. |
| **LangGraph + `SqliteSaver` + `interrupt()`/`Command(resume=…)`** | Checkpoint por thread, pausa e retomada, "time travel" por checkpoint. | Ao retomar, **o nó reexecuta desde o início**. Todo efeito colateral antes do `interrupt()` precisa ser idempotente, senão roda de novo. Dependência grande (langchain-core) e outro modelo de estado (grafo × tabela de etapas). |
| **Manter o motor e adicionar as primitivas** | Aprovação e fork como eventos no mesmo SQLite, com a mesma disciplina de lease e persistência única. | Código próprio a manter (≈260 linhas a mais em `workflows.py`; 544 inserções no total, contando API, CLI, web e testes). |

**Recomendação: manter o motor atual e só adicionar as primitivas.** Nenhuma das bibliotecas resolve algo que o motor
não resolva, e as duas trazem um segundo lugar onde o estado do run vive. A semântica de retomada do LangGraph (o nó
reexecuta) é o contrário do que o prompt pede: efeito colateral só depois da aprovação, e uma vez. Fontes consultadas
em 2026-09-24: documentação de configuração do DBOS (`system_database_url`, Postgres ou SQLite) e a página de
interrupts do LangGraph ("the runtime restarts the entire node from the beginning").

## O que foi feito

| Item do prompt | Implementação | Arquivo |
|---|---|---|
| 1. ApprovalRequest(run_id, step, proposta, evidence_ids, diff, requested_at); suspensão durável até APPROVE / REJECT / EDIT via CLI e web | Uma etapa de geração sem decisão registra `approval.requested` (posição, etapa, proposta com pergunta, modelo e digest, `evidence_ids` da busca, `diff`, `recorded_at`) e deixa o run em `awaiting_generation_approval`, estado persistido no SQLite que sobrevive à morte do processo. `decide` por `cain research decide`, `POST /research/jobs/{id}/decision` e botões na interface. | `src/cain/research/workflows.py`, `agent_api.py`, `cli.py`, `web/app.js` |
| 2. Decisão como evento HumanApproval imutável (quem, quando, o que mudou) | `approval.decided` em `workflow_events`: append-only, JSON RFC 8785 encadeado por sha256, com triggers contra UPDATE e DELETE. Registra `by`, `recorded_at`, `note`, `request_event_id` e, no EDIT, `edit` e `diff` (pergunta antes e depois). `verify_events()` detecta adulteração. | `workflows.py` |
| 3. Efeitos colaterais só depois da aprovação | A chamada ao modelo e a gravação do resultado vêm depois da checagem da decisão. REJECT é terminal: nada depois dele roda, nem com `approve_generation=true` ou `recover`. A interface nunca aprova implicitamente (`approve_generation:false`). A flag explícita da API/CLI registra um APPROVE atribuído ao usuário do escopo. | `workflows.py`, `web/app.js` |
| 4. Fork com `parent_run_id` e `fork_point`; "ramificar daqui" na web | `fork(run, from_step, provider, prompt_version, new_run_id)`: o filho copia os resultados das etapas anteriores ao ponto de fork (`inherited_from = "pai:posição"`) e só executa dali em diante, com outro modelo se pedido. Recusa fork se o acervo mudou (fingerprint), se o protocolo de prompt não confere ou se a posição é inválida. Evento `run.forked`. As aprovações do pai não autorizam o filho. Na web: botão "Ramificar daqui" em cada etapa. | `workflows.py`, `agent_api.py`, `cli.py`, `web/app.js` |
| 5. Etapas idempotentes; documentar as que não são | `inspect` e `search` são leituras determinísticas de um acervo com fingerprint. As etapas de geração não são (o modelo pode responder diferente), mas o resultado é gravado no máximo uma vez por posição (lease + claim): um crash antes da gravação pode repetir a chamada ao modelo, nunca um resultado gravado. Decisões são eventos append-only; repetir `advance` não duplica decisão. Documentado no docstring do módulo. | `workflows.py` |

**Desvio de nome:** o prompt fala em `cain run fork`. No CAIN, `cain run` já é o comando de um pedido único de
conversa; os runs com etapas são os workflows de pesquisa. Por isso o fork ficou em
`cain research fork <run_id> --from <posição> [--model X] [--prompt-version Y] [--run-id Z]`, ao lado de
`cain research decide`.

## Testes obrigatórios

`tests/integration/test_workflow_approval.py` (8 testes, modelo de fixture):

| Teste do prompt | Teste | Resultado |
|---|---|---|
| Matar o processo com run esperando aprovação, reiniciar, aprovar, e o run termina | `test_run_waiting_for_approval_survives_a_killed_process`: um subprocesso deixa o run em aprovação e recebe SIGKILL. Um objeto novo lê só o que foi persistido, aprova as 4 etapas e completa (4 chamadas ao modelo); a cadeia de eventos fica íntegra; o pedido mostra as evidências da busca. | passou |
| Fork reaproveita passos anteriores e só reexecuta a partir do fork_point | `test_fork_reuses_earlier_steps_and_reexecutes_only_from_the_fork_point`: filho com outro modelo; posições 0–2 herdadas com resultado idêntico; o modelo do filho é chamado 3 vezes e o do pai continua com 4. | passou |
| Rejeição não executa efeitos colaterais | `test_rejection_executes_no_side_effects`: depois do REJECT, `advance` (inclusive com `approve_generation` e `recover`) não chama o modelo nem grava etapa. | passou |

Extras: EDIT registra o diff e a etapa usa a pergunta editada; a flag explícita é registrada e atribuída; fork recusa
acervo alterado; adulteração da cadeia de eventos é detectada; rotas da API de decisão e fork.

Suíte completa (Python 3.13.15, venv do `uv.lock`): **1216 passed, 2 skipped, 0 failed** (1218 casos no junit).
Cobertura total **87%**; `research/workflows.py` 91%, `agent_api.py` 94%, `research/cli.py` 97%.
`ruff check src tests`: ok. Os 63 `ResourceWarning` que aparecem sob `--cov` são os mesmos do `main`: medi
63 no `main` base. Três a mais vinham de testes do Prompt 2 e foram corrigidos no commit `6d3c58b`.

## Evidência de runtime com o modelo real (fora do pytest)

`2026-09-24-prompt4/runtime_demo.log`, script `runtime/cain-p4/demo_p4.py`. Acervo pequeno admitido pela política
(`cain research import`); pergunta sobre o relatório A; etapas `inspect, search, support, challenge, synthesis`.

1. **API real (uvicorn) morta com `kill -9` enquanto o run esperava um humano.** O run parou em
   `awaiting_generation_approval` na etapa `support` (posição 2), com 0 chamadas ao modelo, e o servidor recebeu
   SIGKILL (exit −9).
2. **Novo processo servidor:** `read` mostra o run ainda esperando, na mesma etapa. Três APPROVE pela API e o run
   completa com **3 chamadas ao qwen3.5:4b** (5,9 s, 2,4 s e 2,3 s por etapa). Cada pedido de aprovação mostra a
   evidência encontrada pela busca. A síntese final cita o relatório (S1) e repete os números dele.
3. **Run rejeitado:** REJECT na primeira aprovação → `rejected`, **0 chamadas ao modelo**, 2 etapas (só as de
   leitura). Um `advance` com `approve_generation=true` depois do REJECT continua `rejected`.
4. **Fork pela CLI** (`cain research fork demo --from 3`): o filho herda as posições 0–2 (`demo:0..2`) e executa só
   `challenge` e `synthesis`, com **2 chamadas ao modelo**. Cada uma espera uma decisão (`cain research decide`).
5. Cadeia de eventos: **13 entradas, `intact`**.

**Achados das execuções anteriores da demo** (logs brutos preservados fora do repositório, em
`runtime/cain-p4/raw/`):

- **1ª execução:** com a etapa `entities`, o qwen3.5:4b gerou relações e a guarda literal que já existia no CAIN
  recusou a saída ("Relation lacks exact source support"). O run ficou `failed`, falhando fechado, e nada foi
  gravado. O motor de aprovação funcionou (o run sobreviveu ao `kill -9` e a aprovação foi registrada); o que falhou
  foi a qualidade do modelo na extração de relações com citação literal. A demo final usa as etapas de revisão. A
  guarda não foi afrouxada.
- **2ª execução:** o pedido de aprovação saía com `evidence_ids: []`. O código lia `reference_id` da lista `results`
  da busca, mas as referências estão em `evidence`. Os testes com o modelo de fixture não conferiam isso. Corrigido
  no commit `c0e2a1b`: o teste agora exige a evidência no pedido, falha sem a correção (`len([]) == 1` falso) e
  passa com ela.

Logs brutos:

| Arquivo | sha256 |
|---|---|
| `2026-09-24-prompt4/runtime_demo.log` | `2ac4cb1a333a3070987179450a945d6946adef1cdf15963cea890ee1122afee6` |
| `2026-09-24-prompt4/suite.log` | `3f7cf247540076c545730d32c605a79859c0d0ed77e42dd06a07877f6c9613f5` |

## PROVEN × DECLARED

| Afirmação | Estado | Por quê |
|---|---|---|
| Run esperando aprovação sobrevive à morte do processo e continua depois | **PROVEN** | teste com SIGKILL + demo com `kill -9` do servidor real |
| Decisão como evento imutável encadeado, com quem, quando e diff | **PROVEN** | testes (inclui adulteração) + demo (`intact`) |
| REJECT sem efeitos colaterais | **PROVEN** | teste + demo (0 chamadas ao modelo) |
| Fork reaproveita etapas e só reexecuta do ponto de fork, com outro modelo se pedido | **PROVEN** (mesmo modelo na demo; modelo diferente no teste) | teste + demo pela CLI |
| Botões de aprovação e "ramificar daqui" na interface web | **DECLARED** | código em `app.js` e rotas testadas pela API; a interface não foi exercitada num navegador neste PR |
| Escolha de motor | recomendação argumentada | comparação acima; nenhuma medição de DBOS ou LangGraph foi feita |
| Etapa `entities` com o qwen3.5:4b | **falha fechado** | guarda literal existente; modelo pequeno não passa. Não é regressão deste PR |

## O que ficou de fora e por quê

- A identidade de quem aprova é o nome do perfil local (`user_id`). É registro, não autenticação: o serviço é
  local-only. Autenticação fica para quando houver mais de uma pessoa.
- As aprovações não expiram. Um run pode esperar indefinidamente, e é isso que se quer de uma espera durável.
- A etapa `entities` com modelos pequenos precisa de outra estratégia (prompt ou modelo). É assunto do Prompt 5
  (escolha de modelo por medição), não deste.
