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
COOLDOWN`, com a regra que disparou (R01–R15, ordem na docstring do módulo). Nenhum resultado aumenta budget,
prioridade ou escopo; nada lê estado econômico como sinal; não existe caminho de capital.

v2 (2026-09-28) acrescenta a **R15**: se o domínio já recusou a hipótese com o código `HYPOTHESIS_NOT_ADMITTED`,
uma nova proposta dela vira `REQUIRE_HUMAN HYPOTHESIS_NOT_ADMITTED_BY_DOMAIN` (sem task). A memória guarda o motivo
da recusa só quando é um código fechado (`[A-Z][A-Z0-9_]{2,63}`); texto livre continua fora da memória (FUTURE_CANARY).
Achado na primeira campanha com modelo local: o CAIN propôs três vezes uma hipótese que a admissão do operador não
aceita.

## Propostas por modelo local (`cain research explain --propose-for-domain`)

O modelo escolhe só a hipótese e a justificativa; não escolhe semente, handler, budget, prioridade, custos, dados nem
capital, e a proposta passa pela mesma DecisionPolicy. A semente do placebo é do CAIN: derivada do ID da proposta,
nunca uma já usada no domínio (na primeira campanha o modelo repetia sementes, e a mesma semente repete o mesmo
placebo). Antes de perguntar, o CAIN testa cada hipótese configurada na própria política sobre a visão atual:
só as que seriam `ALLOW` entram no enum do schema (as em `COOLDOWN`, recusadas pelo domínio ou retidas ficam de fora),
e sem nenhuma elegível ele responde `NO_ELIGIBLE_HYPOTHESIS` em vez de chamar o modelo. O prompt leva um resumo por
hipótese (resultados, estados científicos, códigos de recusa, por que não é elegível). A auditoria
(`cain-llm-proposal-audit/2`) grava a elegibilidade e a checagem da justificativa: hipóteses citadas sem resultado
nem recusa na memória (checagem por nome, de melhor esforço; a justificativa nunca decide nada).

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

Acrescentar `stocks` ou `brasileirao` = um arquivo de configuração novo + o adapter do domínio (no repositório do
domínio) + a entrada do adapter na allowlist do transporte. O framework não muda.

## Loop do PR #50 (execução direta do avaliador)

O `cain loop` rodava o avaliador do predictor direto do CAIN, fora do circuito do domínio (admission → Ops → Core).
Ele saiu do console script `cain` e ficou como ferramenta de laboratório: `python -m cain.loop …` (mesmos argumentos
e saídas). As medidas de similaridade foram para `cain.loop.similarity` para que `cain review`/`cain findings` não
alcancem `cain.loop.engine`/`cain.loop.evaluator`. `tests/unit/test_loop_fenced.py` prova, pelo fecho estático de
imports, que nenhum console script alcança o avaliador direto nem um pacote de domínio.

## Leitura de registros de predictor (PR #51)

`cain findings ingest-*` lê arquivos versionados de um predictor por `git show` num commit, só leitura. Para o
cripto, o commit tem de ser um SHA completo de 40 hex (nunca um ref móvel como `origin/main`).
