# CAIN — Prompt 6: loop de pesquisa governado sobre um predictor (2026-09-24)

Branch `melhorias/p6-loop-pesquisa`, cumulativa sobre os Prompts 3 a 5. Tudo local; nenhum segredo; nenhuma
conexão com casa de aposta, exchange ou API. O predictor é o **Brasileirão**, rodando sobre um snapshot local imutável
e sem rede. O modelo que propõe mudanças é o qwen3.5:4b no Ollama (GPU RTX 2060).

## Premissa do prompt que não confere, e a adaptação

O prompt diz que o `predictor_core` "já tem RunManifest, TrialLedger, Evaluator e DecisionPolicy". **Não tem.** No
`main` do core (`5a08415`) não existe nenhum desses nomes. Existem:

- `measurement/trials.py`: Experiment Registry com DSR e atestado de poder;
- `contracts/trial_v2.py`: `TrialRegistryV2`;
- `contracts/scientific.py`: máquina de estados científica;
- `testing/prequential.py`: `PrequentialEvaluator`, uma classe abstrata.

Por isso, explicitamente:

- **Ledger:** é do CAIN (`cain.loop.ledger`), append-only, JCS e cadeia sha256, no mesmo formato dos outros logs.
  Cada evento guarda o predictor, o sha256 do world file e o sha256 de cada arquivo do avaliador, para poder ser
  exportado a um TrialLedger do core quando ele existir.
- **Avaliador imutável:** é o **avaliador congelado do próprio predictor**, que usa o `replay` do core. São as
  funções puras `walkforward` e `evaluate` do worker de pesquisa do Brasileirão (wheel 0.3.0rc3, predictor-core
  3.2.1), chamadas por um adaptador. O adaptador, o worker, o `replay` do core, a config do modelo e os pedidos
  ficam fixados por sha256 no world file.
- **O loop não escreve nos registros do predictor** (`trials.json`, `TrialRegistryV2`). Uma tentativa exploratória
  não é um trial pré-registrado. O registro dela é o ledger do CAIN.

## O que foi feito

Pacote `cain.loop`, comando `cain loop` e o mundo `loops/brasileirao/`.

| Item do prompt | Implementação | Arquivo |
|---|---|---|
| 1. World file versionado por predictor | Dados permitidos (snapshot com sha256), holdout, métrica primária e direção, **superfície editável** (parâmetros com tipo, faixa e passo; arquivos: nenhum), orçamento por tentativa e total, nº máximo de variantes por hipótese, estagnação, gates humanos, cascata e avaliador fixado. **TOML, não YAML**: o CAIN já lê `cain.toml` pela biblioteca padrão, e YAML seria dependência nova para o mesmo conteúdo. | `src/cain/loop/world.py`, `loops/brasileirao/research_world.toml` |
| 2. Avaliador imutável, hash conferido antes de cada tentativa | `verify_evaluator` refaz o sha256 de cada arquivo fixado no início do loop e antes de cada tentativa; qualquer diferença para o loop (`evaluator_changed`). O avaliador roda em outro processo, com ambiente mínimo e timeout. O loop nunca abre os dados; só passa os caminhos permitidos. | `world.py`, `src/cain/loop/evaluator.py` |
| 3. Toda tentativa vira Hipótese → Experimento → Feedback, inclusive descarte e crash | Eventos `hypothesis.registered`, `experiment.proposed`, e uma das saídas: `experiment.finished` (feedback), `.discarded`, `.blocked` ou `.crashed`; mais `gate.requested` / `gate.decided`, `holdout.evaluated` e `loop.stopped`. Crash e timeout contam como tentativa. | `src/cain/loop/ledger.py`, `engine.py` |
| 4. Filtros de redundância e de novidade antes de gastar backtest | **Redundância**: o estágio de sanidade devolve um sinal barato (p_casa − p_fora nas últimas 60 partidas de 2021); se ele coincide com o de um candidato anterior, o candidato é descartado **antes** do in-sample e do walk-forward. A medida vem do world: `correlation` ≥ 0,99 (padrão, a regra do RD-Agent para fatores novos) ou `max_abs_diff`. **Novidade**: similaridade da descrição (cosseno do qwen3-embedding:0.6b, ou léxica) ≥ limiar significa mesma hipótese, e a tentativa conta como variante até `max_variants_per_hypothesis`. Proposta idêntica a uma anterior: `DUPLICATE`, sem chamar o avaliador. | `engine.py` |
| 5. Cascata | sanidade e vazamento (sha256 do snapshot confere; `max_used_minus_cutoff_seconds ≤ 0`, isto é, nenhuma informação depois do corte; todas as partidas previstas) → in-sample (2021) → walk-forward (2022, temporada de desenvolvimento) → holdout **só com HumanApproval**. Um candidato que supera o baseline no walk-forward pede o gate `holdout` e o loop para ali. `run_holdout` exige APPROVE registrado e roda uma vez só. **O adaptador do Brasileirão recusa o holdout mesmo assim**: 2025 está lacrado pela política do predictor, e só o processo governado do próprio predictor pode abrir. | `engine.py`, `loops/brasileirao/evaluator.py` |
| 6. O loop para | Orçamento de tentativas, orçamento de tempo, estagnação (N tentativas sem melhora ≥ `min_improvement`), ou gate humano (`holdout`; `new_hypothesis` se o world pedir). | `engine.py` |
| 7. Próximo passo simples | Round-robin entre "features" (parâmetros de Elo) e "model" (modelo de gols). Proponentes: `neighbor` (determinístico) e `local-model` (qwen3.5:4b com saída estruturada do Prompt 5; cada proposta tem manifesto de inferência, e o id da chamada fica no evento). O bandit (Thompson sampling) é a extensão documentada, não a primeira versão. | `src/cain/loop/proposers.py` |
| 8. `cain loop run --predictor X --world …` e `cain loop status` | Também `decide`, `holdout` e `verify`. | `src/cain/loop/cli.py` |

Não chamo isto de "agente autônomo". É um loop com orçamento, parada e gates. O modelo só propõe; quem decide o que
roda é a regra, e quem decide o holdout é um humano.

## Testes obrigatórios

`tests/integration/test_research_loop.py` (13 testes; avaliador real em subprocesso, script congelado em tmp):

| Teste do prompt | Teste | Resultado |
|---|---|---|
| Tentativa que mexe fora da superfície editável é bloqueada e registrada | `test_proposal_outside_the_editable_surface_is_blocked_and_recorded`: arquivo `../evaluator.py` e parâmetro inexistente → `experiment.blocked` com as violações; contam como tentativas | passou |
| Estagnação e orçamento param o loop | `test_stagnation_and_budget_stop_the_loop`: estagnação, orçamento de tentativas e orçamento de tempo (relógio injetado) | passou |
| Crash aparece no ledger e na contagem | `test_crash_and_timeout_are_in_the_ledger_and_in_the_attempt_count`: exit ≠ 0 e timeout → `experiment.crashed` e tentativas = 3 | passou |
| Um ciclo real ponta a ponta | ciclos reais abaixo | feito |

Extras: redundante descartado sem backtest; avaliador adulterado durante o loop o para; holdout só com APPROVE e uma
vez só; gate de hipótese nova; world validado (sem gate de holdout, ou cascata fora de ordem, é recusado); ledger
append-only com adulteração detectada; `DUPLICATE`; medida `max_abs_diff`; proponente por modelo que vê todas as
tentativas e cujas propostas fora da faixa são bloqueadas; CLI completa.

Suíte completa: **1245 passed, 2 skipped, 0 failed** (1247 casos no junit). Cobertura total **87%**; `loop/`: ledger
96%, proposers 93%, engine 90%, evaluator 82%, world 82%, cli 72%. `ruff check src tests loops`: ok.

## Ciclos reais (log completo em `2026-09-24-prompt6/`)

O avaliador foi conferido antes: com os parâmetros de serving, o walk-forward de 2022 reproduz exatamente o resultado
gravado no Brasileirão.

| | RPS do modelo | RPS climatologia | delta | IC 95% |
|---|---|---|---|---|
| 2022, 1X2 | 0,209340 | 0,223370 | −0,014030 | [−0,02141, −0,00683] |

`result_state` = NO_EDGE: ciência SUPPORTED, economia NO_EDGE.

### Ciclo 1 (world v1: redundância por correlação ≥ 0,99)

6 tentativas em 52 s; parou por **estagnação**; ledger `intact`; 5 chamadas ao qwen3.5:4b, com os 5 manifestos
completos. **Todas as 5 propostas foram descartadas como REDUNDANT, e o ciclo expôs dois defeitos reais:**

1. O modelo propôs `form_half_life 4→5` três vezes e `calibration_window 4→5` duas. A temperatura 0, ele só via as
   tentativas concluídas, não as descartadas.
2. A correlação ≥ 0,99 descarta **qualquer** variante de parâmetro do mesmo modelo: meia-vida 4→5 deu correlação
   0,999996 entre as previsões. A regra do RD-Agent é para fatores novos; para ajuste de parâmetro de um mesmo modelo
   ela bloqueia tudo.

Correções (commit `48e4ef6`, com testes):

- o proponente passa a ver todas as tentativas e o resultado de cada uma;
- proposta repetida vira `DUPLICATE` sem chamar o avaliador;
- a medida de redundância passou a ser configurável no world. `correlation` continua o padrão; o world **v2** do
  Brasileirão usa `max_abs_diff ≤ 0,001` (previsões praticamente idênticas).

O v1 fica nas evidências (`cycle1-research_world-v1.toml`). A mudança é de filtro de custo computacional, não de
limiar de aceitação científica, e está registrada no próprio world v2.

### Ciclo 2 (world v2)

6 tentativas em 66 s (69 s dentro do loop); parou por **estagnação** (5 tentativas sem melhora ≥ 0,0005 de RPS);
ledger `intact` com 37 eventos nos dois ciclos; 5 chamadas ao modelo, manifestos completos (10/10 somando os dois
ciclos).

| # | Tipo | Mudança proposta pelo qwen3.5:4b | Resultado | RPS in-sample 2021 | RPS walk-forward 2022 |
|---|---|---|---|---|---|
| 1 | baseline | parâmetros de serving | finished (melhor) | 0,209830 | **0,209340** |
| 2 | features | meia-vida da forma 4 → 5 | finished, sem melhora ≥ 0,0005 | 0,209826 | 0,209319 |
| 3 | model | max_goals 12 → 13 | **REDUNDANT** (diferença máxima 2,3e-8) | — | — |
| 4 | features | meia-vida 5 → 3,5 | finished, sem melhora | 0,209833 | 0,209356 |
| 5 | model | max_goals → 14 | **REDUNDANT** (2,6e-8) | — | — |
| 6 | features | meia-vida → 3 | finished, sem melhora | 0,209837 | 0,209378 |

Leitura honesta:

- **Nenhuma mudança melhorou o RPS em pelo menos 0,0005.** O melhor foi −0,00002, com meia-vida 5. O baseline de
  serving continua o melhor, e **nenhum gate de holdout foi pedido**. É um resultado negativo, registrado como tal.
- O filtro de redundância poupou dois backtests. `max_goals` não altera a margem casa − fora do 1X2: 2e-8 de
  diferença.
- As hipóteses do modelo (5 registradas, similaridade de embedding 0,52 a 0,83 com a mais próxima, abaixo de 0,85)
  são reformulações da mesma ideia. A 0,85, a novidade por embedding trata como novas frases que um humano chamaria
  de variantes. O limiar é do world e foi deixado como estava.
- O ajuste foi feito em 2022, a temporada de **desenvolvimento**. Qualquer "melhora" encontrada ali seria
  exploratória e multiteste. O caminho para uma conclusão é o holdout 2025 do próprio predictor, pelo processo
  governado dele e com decisão humana.

Arquivos e hashes:

| Arquivo | sha256 |
|---|---|
| `2026-09-24-prompt6/cycle1-research_world-v1.toml` | `08949ca83c1ef296884159a9d2370bb188cd602502bf01c2cb5c2c1eae50a56a` |
| `2026-09-24-prompt6/cycle1-cycle-status.json` (= `cycle1-cycle-run.json`) | `bd4c7cf1c931b084a9729b1bdcca8f9db58949dcd1bb8851e0a48845421c3cd3` |
| `2026-09-24-prompt6/cycle1-cycle-run.log` | `9eeb49f28a0bda131a7dafea4666ba26d0ecc9ed8e663aec20bf0e51389655ed` |
| `2026-09-24-prompt6/cycle1-ledger-verify.json` | `944bd4c14160c786fad698939a3ef04a6fa5a3306c6902da6ea548a2a8256703` |
| `2026-09-24-prompt6/cycle1-inference-audit.json` | `5e354e54b6e046aec33d5a6428ce092dfeef4c566107fe41bcdd3ec06ca51fea` |
| `2026-09-24-prompt6/cycle2-cycle-status.json` (= `cycle2-cycle-run.json`) | `cf372ce52ead6fc821a1d68d4357f85321d08b9276f80940e5a553e268063c1d` |
| `2026-09-24-prompt6/cycle2-cycle-run.log` | `1801c602055172a15fcd8493b2e74f3ba32e8ac00339898168c4dfdabafd68cb` |
| `2026-09-24-prompt6/cycle2-ledger-verify.json` | `a3880a6acc07183a90f9db42203fdd7745ec38f7afd373b90a3c52252c98b7f5` |
| `2026-09-24-prompt6/cycle2-inference-audit.json` | `65362438d264a01ccbe788bc21435921393f496cc96b8b66a7d56d496e39ff19` |
| `2026-09-24-prompt6/ledger-events.jsonl` (os 37 eventos dos dois ciclos) | `6ac593b80a5d31cfa1cde94bc82ce66c4c3ba950c5530fe1a8be35dfe22bc91f` |
| `2026-09-24-prompt6/suite.log` | `0e7ba8ebc09f111ee881273b546f5ff48ef42f6e39c171b73a3db6680a5cc141` |

## PROVEN × DECLARED

| Afirmação | Estado | Por quê |
|---|---|---|
| Loop Hipótese → Experimento → Feedback com ledger append-only encadeado | **PROVEN** | testes + 2 ciclos reais (`intact`) |
| Avaliador imutável conferido por sha256 antes de cada tentativa | **PROVEN** | teste de adulteração + ciclos reais (6 arquivos fixados) |
| Bloqueio fora da superfície editável; estagnação e orçamento param; crash contado | **PROVEN** | testes obrigatórios |
| Filtro de redundância antes do backtest | **PROVEN** | teste + ciclo 2 (2 descartes reais) |
| Filtro de novidade por embedding | **PROVEN que roda; calibração DECLARED** | o limiar 0,85 separou frases que são variantes da mesma ideia |
| Holdout só com HumanApproval | **PROVEN** (fixture); no Brasileirão, o holdout é recusado pelo adaptador | teste + adaptador |
| Um ciclo real ponta a ponta com um predictor | **PROVEN** | Brasileirão 2021/2022, avaliador que reproduz o resultado gravado |
| "Melhora" do modelo do Brasileirão | **não encontrada** | nenhuma mudança ≥ 0,0005 de RPS |
| Integração com TrialLedger/Evaluator/DecisionPolicy do core | **não existe no core** | o ledger do CAIN guarda o necessário para exportar depois |
| Isolamento do avaliador (rede, sistema de arquivos) | **não feito aqui** | processo separado, ambiente mínimo e timeout; o sandbox é o Prompt 10 |
| Bandit para escolher o próximo passo | **DECLARED** (extensão documentada) | round-robin nesta versão |

## O que fica para o dono

- Rodar o loop em outro predictor (cripto ou stocks) só faz sentido com uma hipótese de verdade. Hoje os dois só têm
  sondas de qualificação locais, e os dados das hipóteses encerradas do cripto não estão neste PC.
- O world do Brasileirão tem caminhos absolutos deste PC. Em outra máquina é preciso gerar um novo, com os mesmos
  pins; o sha256 confere a identidade.
- O limiar de novidade (0,85) e a escolha `max_abs_diff ≤ 0,001` são valores de política do world, e mudá-los segue
  a regra dos limiares: aprovação humana registrada.
