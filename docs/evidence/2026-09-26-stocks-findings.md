# CAIN — achados do stocks lidos num commit fixado (2026-09-26)

Branch `feature/stocks-findings-20260926`, a partir do `main` `4fe4019`. Par do PR do `stocks-predictor` que
publica `research/scientific_state.json`. A CAIN só lê arquivos versionados do stocks por `git show`, num commit
fixado. Não abre banco, não executa código do stocks e não recebe preços.

## Problema medido antes da mudança

Medido com o código do `main`, num banco de memória novo, sobre o estado real do stocks:

- `ingest_scientific_state` gravou as 22 hipóteses como `informative`, porque o vocabulário embutido era só o do
  Cripto (`CLOSED_NO_GO`, `CLOSED_INSUFFICIENT_SAMPLE`, `REGISTERED_NOT_ACTIVATED`).
- `closed("stocks")` devolveu 0, e o reteste de H11 pela identidade não foi bloqueado.
- As 15 linhas do `trials.json` do stocks entram como `UNLABELLED`: não têm status nem marcador de veredito.

Um estado desconhecido virava informativo por padrão e, com isso, parava de bloquear reteste em silêncio.

## O que mudou

| Arquivo | Mudança |
|---|---|
| `src/cain/findings/data/state-vocabulary.json` (novo) | Política versionada `findings-state-vocabulary` v1: a leitura de cada estado por domínio (`kind` e `verdict`). O Cripto fica igual ao que era embutido (`CLOSED_NO_GO` continua com o rótulo `NO_GO`). No stocks, todo `CLOSED_*` é negativo; `PAUSED*` é informativo. Mudar uma leitura exige arquivo de versão nova, aprovado pelo merge do dono. |
| `src/cain/findings/ingest.py` | `ingest_scientific_state` passa a ler pela política. Antes de gravar qualquer coisa, recusa: estado não listado, domínio sem vocabulário, arquivo que declara outro domínio e schema desconhecido. Cada achado grava a política usada (id, versão, sha256). A reavaliação por hipótese entra em `details`, e a `reopen_policy` literal vira um achado informativo. `ingest_ledger_index` é novo e lê o `stocks-trial-ledger-index/1` (detalhes abaixo). |
| `src/cain/findings/cli.py` | Comando `cain findings ingest-ledger-index --domain --repo --commit --path`. |
| `tests/integration/test_findings_stocks.py` (novo) | 11 testes: bloqueio de reteste por identidade e família, estado literal, pausada não bloqueia, recusas antes de gravar, isolamento de domínio, índice do ledger (cadeia, contagens, idempotência) e a CLI num repositório Git real. |

`ingest_ledger_index`:
- confere a cadeia de hashes antes de gravar: `seq` contíguo, cada `prev` igual ao `hash` anterior, `head`, total e
  contagens;
- grava um achado por execução, com o desfecho (`COMPLETED`/`FAILED`/`ABANDONED`/`OPEN`) e o digest do resultado;
- grava também um achado por decisão, reavaliação, pré-registro e holdout (só o estado mais recente), mais um
  resumo;
- tudo entra informativo e `DECLARED`;
- reingerir o mesmo índice não muda nada.

O vocabulário vai no wheel pelo glob `findings/data/*.json` que já existia; isso foi conferido no `uv build`.

## Validação

- `pytest tests/integration/test_findings.py tests/integration/test_findings_stocks.py`: 21 passed. Os 10 testes
  anteriores, inclusive o do estado do Cripto, passam sem mudança. `ruff check .`: sem achados.
- **E2E real:** CAIN desta branch, venv do `uv.lock` em `~/predictors/runtime`, banco novo, lendo o `stocks-predictor`
  no commit `ddbdaab`:

| Comando | Resultado |
|---|---|
| `ingest-state --path research/scientific_state.json` | 35 negativos (19 hipóteses encerradas + 16 famílias) e 4 informativos (H17, H18, H19 e a `reopen_policy`) |
| `ingest-registry --path trials_v2.json` | 15 tentativas informativas (o status no registro é `UNKNOWN`/`JUDGED`) |
| `ingest-ledger-index` | 16 execuções, 8 decisões (`NO_DECISION`), 15 reavaliações, 1 holdout `HOLDOUT_SEALED` (2026-09-10 a 2027-09-10, selo `d2fc50e7…`) e o resumo |
| `check --hypothesis-id` H11 / H22 / H3 | bloqueado / bloqueado / bloqueado |
| `check --hypothesis-id H17` | não bloqueado (pausada) |
| `check --hypothesis-family quality_roe_leverage_intersection` | bloqueado (o nome da H10 no `trials_v2.json`) |
| domínio `crypto` no mesmo banco | 0 achados |

## Limites

- **Paráfrase livre não é pega.** "momentum 12-1 com retorno total em small caps brasileiras" não casa com H11. A
  equivalência lexical (Jaccard ≥ 0,6, sem calibração) compara com enunciados curtos, e passar `--registry-path
  trials_v2.json` também não resolve. O bloqueio vale por identidade e por família, que é o que a revisão
  adversarial usa ("já está encerrada?", pela identidade e pela linhagem `derived_from`). Calibrar a equivalência é
  mudança de política, decisão do dono.
- **Tudo entra `DECLARED`.** `PROVEN` exige relatório de avaliação e transição de governança com hash; o estado do
  stocks cita os relatórios e seus sha256, mas ligar isso ao `PROVEN` fica para depois.
- **Não é a Etapa B.** A CAIN não propõe nem executa nada no stocks. A leitura por `git show` num commit fixado é o
  mesmo padrão do PR #51 e vai precisar do parecer do `CAIN_CONTAINMENT` na `integration-stocks`.
- **Preços não entram** (ADR 0020: licença UNKNOWN).
