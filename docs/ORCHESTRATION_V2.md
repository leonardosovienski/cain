# Orquestração de pesquisa por domínio (envelope V2, Etapa B)

Criada pela missão `integration-crypto` (primeira das três integrações, D-22). Cada domínio tem **uma**
orquestração; o framework é o mesmo para os três e o que muda é a configuração do domínio.

```text
proposta (cain-proposal/1)
  → DecisionPolicy (determinística, sem LLM) → receipt canônico
  → ResearchTaskV2 no TaskOutbox (orchestration.sqlite)
  → spool (predictor-research-transport) → consumidor do domínio → adapter → adapter_api do domínio
  → ResearchResultV2 no spool → ResultInbox (validação fail closed contra a task emitida)
  → memória bitemporal do domínio (cubo = domínio, PR #45) → retrieval → próxima decisão
```

## Comandos (`cain research …`)

| Comando | O que faz |
|---|---|
| `propose --domain D --state S --proposal F [--as-of T]` | decide, grava o episódio e, se ALLOW, a task no outbox |
| `decision-receipt --domain D --state S --proposal F --as-of T` | só calcula o receipt (bytes canônicos), sem gravar nada |
| `dispatch --domain D --state S --spool DIR [--resend]` | publica as tasks pendentes no spool (write-once) |
| `retry --domain D --state S --spool DIR --task-id ID` | pede reenvio de uma task cujo único resultado é RETRYABLE |
| `ingest --domain D --state S --spool DIR` | valida e ingere os resultados do domínio; grava fatos na memória |
| `episodes --domain D --state S` | episódios, outbox, inbox, rejeições e `verify` da memória |

Cada comando é um processo e cada passo é uma transação; os comandos são idempotentes (mesma proposta → mesmo episódio
e receipt; mesmos bytes → nada novo). Pontos de falha de qualificação: `CAIN_ORCHESTRATION_FAULT=<ponto>`.

## DecisionPolicy (`cain.orchestration.policy`)

Genérica, versionada (`cain-decision-policy` v2 + sha256 do código) e sem relógio: as entradas são a proposta, a
configuração do domínio e a visão do domínio no `as_of` (tasks emitidas + fatos de resultado recuperados da memória,
lidos na cabeça do log e válidos no `as_of`). Decisões: `ALLOW | BLOCK | ABSTAIN | REQUIRE_HUMAN | DUPLICATE |
COOLDOWN`, com a regra que disparou (R01–R17, ordem na docstring do módulo). Nenhum resultado aumenta budget,
prioridade ou escopo; nada lê estado econômico como sinal; não existe caminho de capital.

v2 (2026-09-28) acrescenta a **R15**: se o domínio já recusou a hipótese com o código `HYPOTHESIS_NOT_ADMITTED`,
uma nova proposta dela vira `REQUIRE_HUMAN HYPOTHESIS_NOT_ADMITTED_BY_DOMAIN` (sem task). A memória guarda o motivo
da recusa só quando é um código fechado (`[A-Z][A-Z0-9_]{2,63}`); texto livre continua fora da memória (FUTURE_CANARY).
Achado na primeira campanha com modelo local: o CAIN propôs três vezes uma hipótese que a admissão do operador não
aceita.

Custos na **R06**: o CAIN compara `costs` só quando a variante de `parameters` do pedido, no `request_schema`
congelado do domínio, declara as chaves de custo. No cripto, a única variante declara, então nada muda. No stocks, o
backtest declara e continua preso aos custos [H1-FROZEN]; a coleta de External Intelligence não declara e deixa de ser
bloqueada com `COST_MODEL_MISMATCH` (IS-F002 da integration-stocks). Se nenhuma variante aceitar os parâmetros, a
política é conservadora e compara os custos (a R02 já recusa o formato).

**R16** (logo depois da R05): um pedido que tocaria um escopo lacrado do domínio vira `REQUIRE_HUMAN SEALED_SCOPE`
(sem task). Os lacres ficam em `sealed_scopes` da configuração, gerados do `FROZEN_PARAMETERS` da integração, e
qualquer um que case retém o pedido:

| Lacre | Retém quando |
|---|---|
| `{"field": "season", "any_of": [2025, 2026]}` | o valor do campo está na lista |
| `{"window": {"from": "events.kickoff_from", "to": "events.kickoff_to"}, "intersects": [a, b]}` | `[from, to)` intersecta `[a, b)` |
| `{"field": "events.fixtures[].kickoff_at", "within": [a, b], "optional": true}` | algum instante está em `[a, b)` |

Fail closed: campo lacrado ausente, de tipo inesperado ou com janela invertida também retém; só um lacre
`"optional": true` ausente não retém. Caminhos são pontilhados; `nome[]` percorre cada elemento de uma lista; instantes
em UTC `YYYY-MM-DDTHH:MM:SSZ`. Criado para o holdout 2025 do Brasileirão (D-25 (2)); cripto e stocks não lacram nada.

**R17** (logo depois da R11): o mesmo experimento com outro nome vira `DUPLICATE EQUIVALENT_REQUEST` (sem task).
O experimento é o pedido sem `request_id`, `hypothesis_id` e `research_id` (`policy.experiment_digest`). Cada task da
visão leva esse digest. Contam as tasks que rodaram (`TERMINAL_RESULT`) ou estão pendentes; uma task que o domínio
recusou nunca rodou e não conta. Outro `as_of`, outros parâmetros ou outra semente de placebo são outro experimento.
Achado da rodada de utilidade com o Stocks: `QUAL-PIT-MOM-REAL-001/002/003` são um só experimento, e 12 backtests
deram o mesmo número.

## Propostas por modelo local (`cain research explain --propose-for-domain`)

O modelo escolhe só a hipótese e a justificativa; não escolhe semente, handler, budget, prioridade, custos, dados nem
capital, e a proposta passa pela mesma DecisionPolicy. A semente do placebo é do CAIN: derivada do ID da proposta,
nunca uma já usada no domínio (na primeira campanha o modelo repetia sementes, e a mesma semente repete o mesmo
placebo). O CAIN só grava `placebo_seed` onde o contrato do domínio declara esse parâmetro para o pedido. O cripto
declara; o stocks não, e antes toda proposta por modelo do stocks virava `SCHEMA_INVALID` (IS-F003). O resto do
pedido vem de um molde da hipótese escolhida: a última task emitida dela, senão a última task do tipo de pedido que a
configuração fixa para ela (`proposable_request_types`), nunca de outro tipo. Na rodada de utilidade com o Stocks, a
hipótese de coleta saía como backtest porque o molde era a última task do domínio. Hipótese sem molde fica fora das
opções (`NO_REQUEST_TEMPLATE`) até o operador emitir um pedido daquele tipo. Antes de perguntar, o CAIN testa cada
hipótese configurada na própria política sobre a visão atual:
só as que seriam `ALLOW` entram no enum do schema (as em `COOLDOWN`, recusadas pelo domínio ou retidas ficam de fora),
e sem nenhuma elegível ele responde `NO_ELIGIBLE_HYPOTHESIS` em vez de chamar o modelo. O prompt leva um resumo por
hipótese (resultados, estados científicos, códigos de recusa, por que não é elegível). A auditoria
(`cain-llm-proposal-audit/3`) grava a elegibilidade e a checagem da justificativa, que é de melhor esforço e nunca
decide nada:
- `without_evidence`: hipóteses citadas sem resultado nem recusa na memória;
- `count_mismatches`: frase sobre uma hipótese só (ou "esta hipótese", a escolhida) que cita um número de resultados
  ou episódios diferente do resumo que o modelo recebeu;
- `eligibility_mismatches`: frase que diz que a hipótese é (ou não é) elegível, quando a política diz o contrário.

Frases que citam várias hipóteses ficam de fora, porque parear números e nomes ali seria chute. Na rodada de
utilidade com o Stocks, 4 de 12 justificativas tinham erro desse tipo (por exemplo, "4 resultados" quando eram 3, e
"não é elegível" para uma hipótese elegível).

## Interface da configuração de domínio (`cain-domain-config/1`)

Um arquivo `src/cain/orchestration/data/<domínio>.json`, gerado por `tools/build_domain_config.py` a partir de
fontes fixadas (commit completo do repositório do domínio, contrato no `main` do predictor-qualification,
parâmetros congelados da missão), com sha256 de cada fonte:

| Campo | Significado |
|---|---|
| `domain`, `config_version`, `source`, `contract`, `frozen_parameters` | identidade e proveniência |
| `allowed_request_types` | as chaves da `handler_allowlist` do contrato (o CAIN nunca escolhe handler) |
| `closed_hypotheses`, `frozen_families` | nunca reabertas: proposta equivalente → BLOCK `HYPOTHESIS_CLOSED` |
| `proposable_hypotheses` | fora desta lista → REQUIRE_HUMAN `NEW_HYPOTHESIS` |
| `allowed_symbols`, `costs`, `allowed_references`, `max_priority_hint` | o que o pedido pode conter |
| `budget` (`max_open_tasks`, `max_tasks_per_research`, `max_tasks_total`) | constantes; resultados não as mudam |
| `cooldown`, `negative_result_states` | N negativos seguidos da mesma hipótese → K episódios sem task nova dela |
| `contradiction_pairs` | estados científicos em conflito → REQUIRE_HUMAN, nunca maioria |
| `sealed_scopes` | escopos lacrados (ex.: holdout) → REQUIRE_HUMAN `SEALED_SCOPE` (R16); lista vazia = nenhum lacre |
| `proposable_request_types` | tipo de pedido de cada hipótese proponível: pedido de outro tipo → BLOCK `REQUEST_TYPE_NOT_ALLOWED` (R04); molde do LLM. Com um tipo só no contrato, todas as hipóteses têm esse tipo; com vários (stocks), as fixtures de proposta congeladas da missão decidem |
| `proposal_overlays` (opcional; ausente = nenhum) | parâmetros próprios de uma hipótese proponível no molde de pedido do LLM (ex.: controle negativo com semente própria no stocks). Sem task própria, a hipótese pega a última task do tipo dela sem as chaves de overlay e aplica o seu overlay, então pede o seu experimento, e a R17 não a trata como repetição. Com task própria, o molde é a própria task (a R17 a segura). Nunca `fee_bps`, `slippage_bps` ou `placebo_seed`. O builder só emite a chave quando o `FROZEN_PARAMETERS` a tem, então as configurações sem ela mantêm os mesmos bytes |

Acrescentar `stocks` ou `brasileirao` = um arquivo de configuração novo + o adapter do domínio (no repositório do
domínio) + a entrada do adapter na allowlist do transporte. O framework não muda. As variantes de `parameters` do
contrato (custos, semente) vêm do `request_schema` congelado no registro V2, não da configuração. Um pedido sem
`parameters` (Brasileirão: o `request_schema` não tem a chave) continua sem eles no molde, na sonda de elegibilidade e
na proposta do LLM.

## Loop do PR #50 (execução direta do avaliador)

O `cain loop` rodava o avaliador do predictor direto do CAIN, fora do circuito do domínio (admission → Ops → Core).
Ele saiu do console script `cain` e ficou como ferramenta de laboratório: `python -m cain.loop …` (mesmos argumentos
e saídas). As medidas de similaridade foram para `cain.loop.similarity` para que `cain review`/`cain findings` não
alcancem `cain.loop.engine`/`cain.loop.evaluator`. `tests/unit/test_loop_fenced.py` prova, pelo fecho estático de
imports, que nenhum console script alcança o avaliador direto nem um pacote de domínio.

## Leitura de registros de predictor (PR #51)

`cain findings ingest-*` lê arquivos versionados de um predictor por `git show` num commit, só leitura. Para o
cripto, o commit tem de ser um SHA completo de 40 hex (nunca um ref móvel como `origin/main`).
