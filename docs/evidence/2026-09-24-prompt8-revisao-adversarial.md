# CAIN — Prompt 8: revisão adversarial antes do pré-registro (2026-09-24)

Branch `melhorias/p8-revisao-adversarial`, cumulativa sobre o Prompt 7. Tudo local; nenhum segredo. O modelo é o
qwen3.5:4b no Ollama (GPU RTX 2060), e cada chamada tem manifesto de inferência (Prompt 5).

## Premissa que não confere, e a adaptação

O prompt pede "pré-registro no `predictor_core`". **O core não tem API de pré-registro.** O pré-registro, com
status `pre-registrada`, é hoje uma linha no registro de tentativas de cada predictor, escrita pelo próprio
predictor. O CAIN não escreve nos repositórios dos predictors. Aqui:

- o pré-registro fica no CAIN: arquivo de achados do Prompt 7, predicado `preregistered_hypothesis`, com o sha256 do
  checklist resolvido;
- o rascunho revisado é o artefato que o dono leva ao registro do predictor.

O exemplo pedido, "H11b", **não existe** no Brasileirão. Existem:

- **H11** (refit a cada rodada × a cada 100 jogos): `refutada`;
- **H11-v2** (releitura retrospectiva): `inconclusiva`;
- **H15**: a sucessora prospectiva, já `pre-registrada`.

O exemplo real é, então, um rascunho "H11b" que declara derivar de H11. É exatamente o caso que a revisão
adversarial deve pegar.

## O que foi feito

Pacote `cain.review` (quadro de revisão, CLI `cain review`, rotas da API) e a página `/review-map`.

| Item do prompt | Implementação | Arquivo |
|---|---|---|
| 1. Perspectivas configuráveis por domínio | Arquivo versionado com cinco perspectivas: cético de overfitting, vazamento temporal, custos e execução, mudança de regime (obrigatórias) e "o mercado já precifica isso?" (opcional; Brasileirão, cripto e stocks). Filtro por domínio. O sha256 do arquivo fica em cada item gerado. | `src/cain/review/data/perspectives-v1.toml` |
| 2. Cada perspectiva gera perguntas; cada pergunta vira item de checklist com teste, ou não testável com motivo | O modelo local responde com saída estruturada: até 3 perguntas, cada uma com teste (tipo, descrição, critério de aprovação) ou `testable=false` e motivo. Status: `TEST_PROPOSED` (teste do modelo), `NOT_TESTABLE`, `OPEN`. **Um teste proposto pelo modelo não resolve o item**: um humano nomeado precisa aceitá-lo (`accept`), reescrevê-lo (`define-test`) ou dispensar o item (`waive`). O arquivo de achados (Prompt 7) acrescenta o item obrigatório "já está encerrada?", checado por identidade e pela linhagem declarada (`derived_from`). | `src/cain/review/board.py` |
| 3. Mapa de perguntas persistente na memória | Cada item é um fato da memória bitemporal (cubo do domínio): pergunta → teste / evidência ou run que responde / dispensa → status. Toda mudança supersede, a leitura aceita `as_of`, e o mapa sobrevive a reinício. | `board.py` |
| 4. Pré-registro só com os obrigatórios resolvidos | `preregister` recusa (`CHECKLIST_UNRESOLVED`, com a lista) enquanto um item obrigatório não estiver `TEST_DEFINED`, `ANSWERED` ou `WAIVED`. Dispensa, aceite e definição de teste exigem uma pessoa nomeada; `model:*` e `cain*` são recusados. Ao aceitar, grava o sha256 do checklist. | `board.py`, `src/cain/review/cli.py` |
| 5. Modelo local com manifesto de inferência | `generate_structured` (Prompt 5), com o provedor configurado em modo `manifest`; cada item guarda o id da chamada. | `board.py` |
| (interface web) | `GET /review/{domínio}/{hipótese}` (JSON) e a página `/review-map`, montadas no `create_app` da API local. | `src/cain/review/api.py`, `src/cain/web/review.{html,js,css}` |

## Testes obrigatórios

`tests/integration/test_review.py` (5 testes):

| Teste do prompt | Teste | Resultado |
|---|---|---|
| Pré-registro sem checklist resolvido é recusado | `test_preregistration_is_refused_while_the_checklist_is_unresolved`. Recusa sem revisão; recusa com testes só propostos e com item não testável. Aceite e dispensa por "model:" são recusados. Depois do aceite humano e da dispensa com motivo, o pré-registro sai com o sha256 do checklist. | passou |
| O mapa sobrevive a reinício e aparece na interface web | `test_question_map_survives_a_restart_and_shows_in_the_web_interface`. Reabre o arquivo SQLite sem nada na memória do processo e obtém o mesmo mapa. `create_app` real: a rota JSON mostra os mesmos itens, e a página e os assets são servidos **sem código inline** (ver achado 3). | passou |

Extras: o item "já encerrada?" bloqueia até um humano decidir; linhagem declarada checada por identidade; CLI
completa (open, generate, map, accept, waive, preregister).

Suíte completa: **1259 passed, 2 skipped, 0 failed** (1261 casos no junit). Cobertura total **87%**; `review/`:
api 100%, board 92%, cli 95%; `memory/store` 92%. `ruff check src tests loops`: ok.

## Exemplo real: rascunho H11b do Brasileirão

`2026-09-24-prompt8/draft-H11b.json`:

- **enunciado:** refit do modelo de gols a cada rodada (≈10 jogos) em vez de a cada 100 baixa o RPS de 1X2;
- **métrica:** diferença pareada de RPS com IC de bootstrap por cluster;
- **dados:** painel 2021–2024, snapshot `31f30a4d`;
- **desenho:** walk-forward, corte 1 h antes, avaliação única;
- **linhagem:** `derived_from` = `brasileirao:trial:h11-refit-cadence-rodada-vs-100jogos`.

Pela CLI real (`runtime_demo.log`):

1. `findings ingest-registry` do `data/trials.v2.json` real do Brasileirão, para que H11 esteja no arquivo.
2. `review open` e `review generate` com o qwen3.5:4b: **15 perguntas** (5 perspectivas × 3), **0 falhas** de saída
   estruturada, em **62,5 s**. As mesmas 15 perguntas saíram numa execução anterior (temperatura 0). Os **5
   manifestos** estão completos (`inference audit`: 5/5).
3. **Item "já encerrada?" = OPEN:** equivalente a `brasileirao:trial:h11-refit-cadence-rodada-vs-100jogos`
   (**REFUTED**), pela identidade da linhagem. A similaridade de texto entre o rascunho em inglês e as notas em
   português do registro ficou em 0,02: sem a linhagem declarada, só o texto não teria pego.
4. `review map`: 16 itens: 15 `TEST_PROPOSED` e 1 `OPEN`. **13 obrigatórios bloqueiam** (os 3 de "já precifica?"
   são opcionais).
5. `review preregister` → **recusado** (`CHECKLIST_UNRESOLVED`, com os 13 itens).
6. API real (uvicorn): `GET /review/brasileirao/H11b` devolve os mesmos 16 itens da CLI, e a página é servida. No
   navegador (`browser-render.json`), a página mostra "H11b (UNDER_REVIEW): 13 item(ns) obrigatório(s) bloqueando;
   pré-registro recusado até resolver", 16 linhas, 13 destacadas, e a linha "equivalente a: …h11… (REFUTED)".
7. `memory verify`: `intact`.

**O agente não aceitou nenhum teste nem dispensou nada.** Isso é do dono: o pré-registro de H11b fica recusado
até ele decidir. O mais provável, pelo registro, é que H11b seja H11 com outro nome, e que a sucessora honesta já
seja H15.

**Qualidade das perguntas** (DECLARED, sem medição). Várias são pertinentes:

- vazamento: verificar, partida a partida, que o último refit usado é anterior ao corte;
- regime: diferença estratificada por temporada;
- múltiplos testes no overfitting.

Outras estão na perspectiva errada (perguntas de estabilidade de parâmetros em "custos e execução") ou têm
critério fraco (ICC < 0,8). Foi por isso que o teste proposto pelo modelo deixou de contar sozinho (achado 2).

## Achados desta etapa (corrigidos, com teste)

1. **Relógio do WSL2 voltou 1,4 s** entre dois comandos, e a memória recusou a escrita (`CLOCK_WENT_BACKWARDS`).
   Com o relógio real, a escrita agora espera até 5 s o relógio passar da cabeça do log. Um salto maior continua
   recusado. Commit `443943b`.
2. **Teste proposto pelo modelo contava como definido.** Na primeira execução real, as 15 perguntas vieram com
   teste e desbloqueariam o pré-registro sem ninguém olhar. Agora são `TEST_PROPOSED` até o aceite humano. Commit
   `6c7c635`; o log dessa execução está preservado fora do repositório (`runtime/cain-p8/raw/first-run/`).
3. **A página não renderizava no navegador.** A CSP da API (`script-src 'self'`) bloqueava o script inline. O
   teste com TestClient não executa JS e não pegou. Agora o script e o estilo estão em `/assets`, e o teste exige
   que não haja código inline (falha com a página antiga). Commit `567f76e`.

| Arquivo | sha256 |
|---|---|
| `2026-09-24-prompt8/runtime_demo.log` | `525b9a1eab263988ebc7930d250c0d18991548cf0cf4d91b2357890e8a2c7764` |
| `2026-09-24-prompt8/summary.json` | `36260041fa2409bdf44f6e38964ca28ceeb9ae918fb010b6dfec9c90efe52f33` |
| `2026-09-24-prompt8/draft-H11b.json` | `b6a6395bb0e291e6edb2fe14a1ac69c900694fcf0d100b25adf064b67e6fbc0e` |
| `2026-09-24-prompt8/browser-render.json` | `99e3bb022c444498a56f3dc39686ddc4c5bc744fa6130d09e335d3888bf1ef2e` |
| `2026-09-24-prompt8/suite.log` | `730ea3fdd0ef538ba8845a218038351e6803e093c2a47815e0f676c298bcbf28` |

## PROVEN × DECLARED

| Afirmação | Estado | Por quê |
|---|---|---|
| Perspectivas configuráveis geram perguntas que viram itens com teste ou motivo | **PROVEN** | teste + execução real (15 itens, 0 falhas) |
| Mapa persistente na memória, sobrevive a reinício | **PROVEN** | teste + SQLite real |
| Pré-registro recusado sem checklist resolvido; dispensa e aceite só humanos | **PROVEN** | testes + recusa real de H11b |
| Hipótese derivada de uma refutada é pega pelo arquivo | **PROVEN** | execução real (H11, REFUTED) |
| Modelo local com manifesto | **PROVEN** | 5/5 manifestos completos |
| Mapa na interface web | **PROVEN** | teste da API + página renderizada no navegador real (DOM lido) |
| Qualidade das perguntas do modelo | **DECLARED** | não medida; revisão humana obrigatória |
| Pré-registro no `predictor_core` | **não existe no core** | fica no CAIN, com o sha256 do checklist |

## Adendo da revisão final (2026-09-25)

Detalhes em `2026-09-25-revisao.md`.

- O item "já encerrada?" usa a política versionada de equivalência. `--closed-threshold` saiu; `--closed-rank-embedding` só ordena.
- Cada item gerado pelo modelo agora é aresta de proveniência para a chamada que o gerou.
