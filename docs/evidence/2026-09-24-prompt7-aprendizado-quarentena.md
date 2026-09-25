# CAIN — Prompt 7: CAIN aprende com os predictors, com quarentena (2026-09-24)

Branch `melhorias/p7-aprendizado-quarentena`, cumulativa sobre o Prompt 6. Tudo local e somente leitura nos
predictors: as fontes são lidas com `git show` num commit fixado, e nada é escrito nos repositórios deles. Nenhum
segredo; nenhum modelo gera conteúdo (a ingestão é determinística).

## Premissas que não conferem, e a adaptação

- **Não existe TrialLedger no `predictor_core`** (Prompt 6). A ingestão lê o que cada predictor mantém de fato:
  - o registro de tentativas: Brasileirão `data/trials.v2.json`, cripto `GarimpoInvestimentos/trials.json`,
    stocks `trials_v2.json`;
  - o estado científico do cripto (`charters/scientific_state.json`);
  - o ledger do loop do CAIN (Prompt 6).

  Cada achado guarda o repositório, o commit resolvido, o caminho, o sha256 da fonte, a identidade (`trial_id`,
  `hypothesis_id`), o `registered_at` e os hashes que a linha tiver.
- **Não existem EvaluationReport nem GovernanceTransition no ecossistema.** Pela regra do prompt, PROVEN exige os
  dois. Aqui isso quer dizer: um relatório de avaliação (artefato com sha256) **e** uma transição de governança
  (origem, sha256, estado de destino). Nenhuma fonte real tem os dois, então **todo achado real entra DECLARED, em
  quarentena**. O caminho para PROVEN está implementado e testado com fixtures; na prática, falta aos predictors
  publicar esses dois objetos.

## O que foi feito

Pacote `cain.findings` (arquivo, ingestão, CLI `cain findings`), sobre a memória bitemporal do Prompt 2: um cubo por
domínio, leitura sempre `as_of`, correção por supersessão.

| Item do prompt | Implementação | Arquivo |
|---|---|---|
| 1. Ingestão determinística, preservando run_id, hashes e ts_recorded | `ingest_trial_registry`, `ingest_scientific_state` e `ingest_loop`. Fonte lida em `commit:path`, com sha256. Identidade preservada: `trial_id`/`name`, `hypothesis_id`, `hypothesis_family`, e `registered_at` (também como `valid_from`). Idempotente. Mudança de status na fonte **supersede** o achado anterior, e a leitura `as_of` antiga continua mostrando o veredito antigo. | `src/cain/findings/ingest.py` |
| 2. Arquivo de achados DECLARED × PROVEN; quarentena | PROVEN só com relatório **e** transição com hash. A consulta padrão devolve **só PROVEN**. DECLARED aparece com `--include-quarantine`, sempre com `quarantine: true` e o motivo (`missing evaluation report and governance transition`). | `src/cain/findings/archive.py` |
| 3. Achados negativos impedem reteste com outro nome | `equivalent_closed`: mesma identidade (`trial_id`, `hypothesis_id` ou família congelada) ou enunciado semelhante acima do limiar. **O loop do Prompt 6 consulta o arquivo antes de rodar**: hipótese do world equivalente a uma encerrada → para com `equivalent_to_closed` e pede o gate humano `closed_hypothesis`, sem chamar o avaliador; proposta equivalente → `EQUIVALENT_TO_CLOSED`. Achados encerrados valem mesmo em quarentena: bloquear um reteste é o lado conservador. | `archive.py`, `src/cain/loop/engine.py`, `cain loop run --memory-db` |
| 4. Biblioteca de procedimentos | Entra só com relatório de testes aprovado (`failed = 0`, `passed > 0`, sha256) e walk-forward aprovado (referência + sha256), com hashes de código e de dados e as métricas. `sync_demotions`: um procedimento cuja tentativa de origem a fonte passou a rebaixar (`refutada`/`substituida`/…) vira DEMOTED. A consulta padrão esconde os DEMOTED; a leitura `as_of` anterior ainda o mostra ACTIVE. | `archive.py` |
| 5. Isolamento por domínio | Um cubo por domínio. `apply` de um achado noutro domínio exige uma hipótese **pré-registrada no domínio de destino** que diga de qual achado deriva; sem isso, `CROSS_DOMAIN_NEEDS_PREREGISTRATION`. | `archive.py` |

## Testes obrigatórios

`tests/integration/test_findings.py` (8 testes; a fonte é um repositório git temporário):

| Teste do prompt | Teste | Resultado |
|---|---|---|
| Achado DECLARED não aparece na consulta padrão | `test_declared_finding_is_quarantined_by_default` (+ `test_proven_needs_both_the_report_and_the_governance_transition`) | passou |
| Hipótese equivalente a uma NO-GO é sinalizada pelo loop antes de rodar | `test_loop_flags_a_hypothesis_equivalent_to_a_closed_one_before_running`: o avaliador nunca é chamado, 0 tentativas, gate `closed_hypothesis`; e a família congelada casa pela identidade | passou |
| Rebaixamento no core se reflete na biblioteca | `test_a_procedure_demoted_at_the_source_is_demoted_in_the_library`: `comprovada` não muda nada; `substituida` → DEMOTED, escondido por padrão, visível com flag, e ACTIVE no `as_of` anterior. Procedimento sem teste aprovado ou sem walk-forward é recusado. | passou |

Extras: ingestão idempotente pelo git com supersessão bitemporal; isolamento por domínio com pré-registro; ingestão
do estado científico e do resultado de um loop (DECLARED antes da decisão humana, PROVEN depois do gate decidido);
CLI.

Suíte completa: **1253 passed, 2 skipped, 0 failed** (1255 casos no junit). Cobertura total **87%**; `findings/`:
archive 95%, ingest 95%, cli 80%. `ruff check src tests loops`: ok.

## Evidência de runtime (fontes reais, `origin/main` de cada repositório local)

`2026-09-24-prompt7/runtime_demo.log` (todos os comandos e saídas) e `summary.json`:

| Fonte | Achados | Por tipo |
|---|---|---|
| Brasileirão `data/trials.v2.json` (29 linhas) | 29 | 6 negativos (`refutada`), 1 positivo (`comprovada`), 22 informativos |
| Cripto `GarimpoInvestimentos/trials.json` (26) | 26 | 26 informativos: as linhas **não têm campo de status**; o veredito está só no texto das notas |
| Cripto `charters/scientific_state.json` | 10 | 7 hipóteses encerradas (H1–H3, H5 NO_GO; H4, H6, H9 amostra insuficiente), 2 registradas e não ativadas (H7, H8), 1 família congelada (`funding_oi_hmm_v3`) |
| Stocks `trials_v2.json` (15) | 15 | 15 informativos: status só `JUDGED`/`UNKNOWN`; o veredito está nas notas e nos documentos de congelamento |
| Ledger do loop do Prompt 6 (2 loops) | 2 | 2 negativos (`NO_IMPROVEMENT_OVER_BASELINE`) |

- **Consulta padrão (só PROVEN): 0 achados nos três domínios.** Com `--include-quarantine`: 31 (Brasileirão), 36
  (cripto), 15 (stocks). É o resultado honesto: nenhuma fonte tem relatório e transição.
- Reingestão das mesmas fontes: tudo `unchanged`.
- **O loop aprendeu com o próprio resultado.** Rodar de novo o world do Prompt 6 com `--memory-db` **para antes da
  primeira tentativa** (`equivalent_to_closed`, 0 tentativas): a hipótese `CAIN-LOOP:BR-ELO-TUNING-DEV2022` é a
  mesma dos dois loops já encerrados sem melhora. Repetir essa exploração exige decisão humana.
- `check` da família `funding_oi_hmm_v3` casa **só** o achado da família congelada. Uma ideia nova ("liquidez de
  fim de semana de pares estáveis") não casa nada.
- Aplicar o achado do Brasileirão no cripto sem pré-registro é recusado (exit 1).
- **Procedimento real admitido.** `elo-goal-model-1x2-probabilities` do Brasileirão:
  - **testes:** a suíte do próprio predictor, rodada aqui no checkout rc3 `25cdf4d` somente leitura, deu **2349
    testes, 0 falhas, 1 pulado** (`brasileirao-tests-summary.txt`). O `worker.py` testado tem o mesmo sha256
    (`9b2b7a57…`) do que o avaliador do Prompt 6 fixa;
  - **walk-forward:** o evento do ledger do Prompt 6 (2022: RPS 0,20934 × 0,22337, IC do delta [−0,0214,
    −0,0068], abaixo de zero);
  - **escopo registrado:** procedimento de **previsão** (probabilidades melhores que a climatologia), **não** uma
    estratégia lucrativa: a economia deu NO_EDGE.

  A mesma especificação com uma falha nos testes é recusada (`PROCEDURE_NOT_TESTED`).
- `memory verify`: `intact`.

**Achado corrigido nesta etapa (commit `17863d0`).** Na primeira ingestão real, a família congelada do cripto foi
gravada como rótulo em cada hipótese, e a checagem de `funding_oi_hmm_v3` casava H1..H9, inclusive as hipóteses de
LLM (H4, H5). Agora ela é um achado próprio, e o teste cobre isso.

**Observação sobre similaridade** (`check-embedding.json`). Com o embedding local (qwen3-embedding:0.6b), o enunciado
"modelo HMM de 3 estados sobre funding e open interest" põe H1 em primeiro (0,75) e H9 (outro HMM) em segundo
(0,74). Mas **todas** as hipóteses encerradas do cripto ficam entre 0,65 e 0,75, inclusive as de LLM. A similaridade
ordena, mas não separa. O sinal confiável é a identidade (trial, hipótese, família). A similaridade serve de alerta
para revisão, e o limiar não foi mexido.

| Arquivo | sha256 |
|---|---|
| `2026-09-24-prompt7/runtime_demo.log` | `85727a4e5a7095a09eadaaab9f13df6d5263b20775d113b3d3e947b37774ea3b` |
| `2026-09-24-prompt7/summary.json` | `d4df00bbcda5a1487b2f278403f77805402d24fb9ac5bc4cef36e967cd49a168` |
| `2026-09-24-prompt7/procedure.json` | `94f334eb034d7ea3f7de939c2d2d3c172865b11631704ca4512ff6686a53ef67` |
| `2026-09-24-prompt7/brasileirao-tests-summary.txt` | `49a1227f04ee5c1ecf4f9b70c6a316fe4310aa5649bbed544ea14bf74ab8f9b3` |
| `2026-09-24-prompt7/check-embedding.json` | `be9c2f44a0590decae57e0fb845f92c12ef54fb427d52d362a9dcea3f1a60495` |
| `2026-09-24-prompt7/suite.log` | `b5518e491331c6138c6ce1c000777183978b5a845687601967de5c9d509a9300` |

## PROVEN × DECLARED

| Afirmação | Estado | Por quê |
|---|---|---|
| Ingestão determinística com identidade, hashes e `registered_at` preservados; idempotente; supersessão | **PROVEN** | testes + ingestão real de 3 predictors e do ledger |
| Quarentena: DECLARED fora da consulta padrão e sempre rotulado | **PROVEN** | teste + consulta real (0 por padrão) |
| PROVEN exige relatório e transição | **PROVEN** com fixtures; **não exercitado com fonte real** | nenhuma fonte real tem os dois objetos |
| Loop não retesta hipótese encerrada | **PROVEN** | teste + reexecução real parada com 0 tentativas |
| Biblioteca de procedimentos com testes e walk-forward reais | **PROVEN** | suíte real do predictor + evento do ledger; recusa sem teste |
| Rebaixamento no core refletido | **PROVEN com fixture** | nenhum procedimento real foi rebaixado na fonte |
| Isolamento por domínio | **PROVEN** | teste + recusa real |
| Negativos do cripto além do estado científico, e todos os de stocks | **não capturados** | o veredito está em texto livre; extraí-lo pede o caminho por modelo (sempre DECLARED), que não entrou aqui |

## O que fica para o dono

- Para ter achados PROVEN de verdade, os predictors precisam publicar um relatório de avaliação (artefato com
  sha256) e uma transição de governança (quem decidiu, de qual estado para qual, com hash). É o que o TrialLedger do
  core deveria carregar.
- Os registros do cripto e de stocks não têm status estruturado por tentativa. Um campo de veredito tornaria a
  ingestão determinística completa.

## Adendo da revisão final (2026-09-25)

Detalhes em `2026-09-25-revisao.md`.

- As NO-GO de **CS, LoL e F1**, citadas pelo prompt, tinham ficado de fora. Os repositórios não estavam neste PC.
- Agora: 5 NO-GO do F1 e 2 do LoL, lidas das notas por marcador fixo (`RESULTADO…:`), mais 1 do cripto (`VEREDITO FINAL…:`). O CS não tem tentativa refutada.
- A equivalência com hipótese encerrada segue a política versionada `findings-policy` (identidade, ou léxica ≥ 0,6). O embedding só ordena: ele casava todas as hipóteses do cripto.
- Os encerramentos de capital de CS, F1 e LoL (formatos diferentes) ficam pendentes.
