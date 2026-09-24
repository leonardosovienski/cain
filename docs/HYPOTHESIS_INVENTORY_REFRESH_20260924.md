# Atualização do inventário de hipóteses — 24/09/2026

Registro da atualização de `tools/hypothesis_sources.json` para os commits atuais dos três predictors,
com conferência em QA isolado (clones somente-leitura; nenhum produtor alterado; nada instalado na principal).

## Commits revisados

| Domínio | Commit anterior (15/09) | Commit atual (24/09) | Fontes | Alteradas desde 15/09 |
|---|---|---|---|---|
| brasileirao | `f87806900d2aa3c5e267259a67f27ce56e18dc03` | `e540f97a47fc09d3d6e17f0e0e536634e06d4739` | 22 | 2 |
| crypto | `4eb96e141389b8390536716af3c4a0cb46edab23` | `174573df4884b5455f9b38ecc933bf48c67ff4df` | 32 | 13 |
| stocks | `3066321e599ee15dd0ace4167d2791545ce6eb95` | `36081a66004a464d5e9c5ea4bc6e208d0fcb582e` | 48 | 18 |

Nenhuma fonte foi adicionada, removida ou reclassificada; só os hashes e os commits mudaram. Com o inventário
anterior, `prepare_hypothesis_catalog.py` recusava os três checkouts ("Source changed"), como previsto pelo desenho.

## Conferência em QA (receptor CAIN em `main`, 24/09/2026)

| Domínio | Publicações geradas | Registros | Importação | `verify` |
|---|---|---|---|---|
| brasileirao | 22 | 82 | 22 admitidas, 0 falhas | integrity verified |
| crypto | 32 | 89 | 32 admitidas, 0 falhas | integrity verified |
| stocks | 48 | 87 | 48 admitidas, 0 falhas | integrity verified |

Também exercitados no mesmo dia, fora do catálogo: exportador oficial do Crypto (15 registros H1–H9 e CLAIM-CR-*,
auditoria L0 5/5 no braço determinístico), runner de integração do Brasileirão (PASS, 3 claims, 7 casos negativos),
exportador de status do Stocks (1 registro, reimportação `duplicate`) e Bundles Crypto (18 entidades) e Stocks
(2 entidades, artefatos somente referência) aprovados e ingeridos.

## Limites

Contagens de publicações e ocorrências não são totais de hipóteses únicas. A conferência valida engenharia de
ingestão e leitura literal; não certifica interpretação de modelo nem conclusões científicas ou econômicas.
Os catálogos gerados ficaram apenas em QA; conectar à instalação principal é decisão separada.
