# Calibração do embedding de paráfrase (stocks, 2026-09-28)

**Decisão do dono** (integration-stocks, "Calibrar embedding (Recomendado)"): o plano tinha quatro passos.

1. Enriquecer os enunciados das hipóteses encerradas.
2. Medir o embedding local num conjunto rotulado.
3. Mostrar a separação e um limiar.
4. O dono aprova o número pelo merge da findings-policy v3; só então o embedding decide.

**Resultado:** a medida não separa o suficiente pela regra fixada antes. Por isso este PR **não propõe a
findings-policy v3**, e o embedding continua só para revisão. O dono decide.

## Ordem dos commits (selo)

| Commit | Conteúdo |
| --- | --- |
| `d1d92b6` | `calibration-set.json` sozinho (sha256 `65a52c59…`), antes de qualquer embedding desses textos. A mensagem desse commit diz "17 hard"; o certo é 12, e a correção está no commit seguinte. |
| `84c20a1` | `ingest-state --describe` e `tools/calibrate_findings_embedding.py`, com a regra de escolha do limiar e a recomendação escritas antes de rodar. |
| este | `cain-embed.toml`, com modelo e digest fixados, e `run-1/calibration-result.json`, a medição única. |

## Conjunto

O conjunto tem 96 textos. As duas metades são fixas.

| Metade | Encerradas (paráfrase / reparametrização) | Novas (hard) |
| --- | --- | --- |
| calibração | 33 (30 / 3) | 15 (7) |
| validação | 33 (30 / 3) | 15 (5) |

- Encerradas: H1–H16, com duas paráfrases em português e duas em inglês para cada uma.
- Nenhum texto nomeia uma família nem um trial id. As rotas da política v2 não casaram nenhum dos 96 textos.

## Medição (run-1)

Condições:
- Modelo: `qwen3-embedding:0.6b`, digest `ac6da0df…`, na GPU do PC 2.
- Fontes: stocks-predictor `4c82885`, com os 35 achados negativos (19 hipóteses encerradas e 16 famílias).
- Escore de um texto: o maior cosseno contra os enunciados dos achados encerrados.

| Variante do enunciado encerrado | AUC calibração | AUC validação | topo = hipótese certa (cal / val) |
| --- | --- | --- | --- |
| estado (como nas rodadas de utilidade) | 0,548 | 0,687 | 10/33 · 10/33 |
| estado + registro (`--registry-path`) | **0,667** | 0,762 | 16/33 · 20/33 |
| descritivo (`--describe` + manifesto) | 0,630 | 0,735 | 13/33 · 13/33 |

A variante escolhida pela regra é a de maior AUC na calibração: **estado + registro**.

O limiar t* é o menor que não bloqueia nenhuma ideia nova da calibração: **0,650**.

| Limiar | Metade | Encerradas pegas | Novas bloqueadas |
| --- | --- | --- | --- |
| t* = 0,650 | calibração | 8/33 | 0/15 |
| t* = 0,650 | validação | **11/33** | **0/15** |
| t_J = 0,5995 (só comparação) | calibração | 15/33 | 1/15 (`C-N-dy-en`, dividend yield) |
| t_J = 0,5995 (só comparação) | validação | 20/33 | 1/15 (`V-N-monday-en`, efeito segunda-feira) |

A recomendação fixada antes pedia pelo menos metade das encerradas pegas na validação e nenhuma nova bloqueada. Deu
11/33, então fica `KEEP_REVIEW_ONLY`.

## Leitura

- **O idioma pesa mais que o conteúdo.** Pela variante escolhida:
  - paráfrases em português: média 0,478 (mínimo 0,268);
  - paráfrases em inglês: média 0,649;
  - ideias novas: 0,413 em português e 0,567 em inglês.

  Uma paráfrase em português de uma hipótese encerrada fica abaixo de uma ideia nova em inglês. Os enunciados
  encerrados são quase todos em inglês ou em nomes de parâmetros, e o modelo de 0,6B separa pouco entre idiomas.
- **O descritivo não ganhou do registro na calibração.** Na validação, com o próprio t* (0,632), ele pegaria 17/33
  sem bloquear nenhuma nova. A regra escolhe a variante pela calibração, então isso fica registrado e não muda a
  recomendação. Olhar a validação para trocar de variante seria escolher depois de ver.
- **Para revisão**, a ordem dos candidatos melhora com o registro: o topo acerta a hipótese em 16–20 de 33, contra
  10 só com o estado. A ingestão do stocks para revisão deve usar `--registry-path trials_v2.json`.

## O que não foi feito

- Nenhum outro modelo foi medido. Um modelo maior pediria um conjunto de validação novo, porque este já foi visto.
- Nenhum limiar entrou na política; a findings-policy continua na v2.

## Reproduzir

```
python tools/calibrate_findings_embedding.py --stocks-repo <clone do stocks-predictor> \
  --commit 4c82885eddab233f2b57442046875fdc2c8f0932 \
  --set docs/evidence/2026-09-28-findings-calibration/calibration-set.json \
  --config docs/evidence/2026-09-28-findings-calibration/cain-embed.toml --out <pasta nova>
```

O script precisa do Ollama local com o modelo desse digest; com outro digest, a configuração recusa.

O gravador de inferência do CAIN guardou as chamadas de embedding da run-1 em `data/inference.db`, ao lado da
configuração. Esse arquivo é ignorado pelo git e foi movido para fora do repositório, no PC 2:
`~/predictors/runtime/integration-stocks/calibration-run-1/inference.db`, sha256 `ee121c08…`.
