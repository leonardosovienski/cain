# Publicação verificada — Cain 0.4.4

Conferência em 11/09/2026. Escopo e uso em [DELIVERY_044.md](DELIVERY_044.md).

| Repositório | Branch | Commit entregue e conferido local/remoto | CI |
|---|---|---|---|
| Cain | local/l0-historian | 68e52b7fd7475c5b976faf5598b6d04d486fa9ad (implementação; fechamento documental posterior) | [CI aprovada](https://github.com/leonardosovienski/cain/actions/runs/34621030704), Python 3.11/3.12/3.13 |
| Stocks | integration/cain-status-20260911 | 5d27efdb00dd44bc4ce777383a3c2e7587e3bad3 | [CI completa aprovada](https://github.com/leonardosovienski/stocks-predictor/actions/runs/34621171855), [exportador](https://github.com/leonardosovienski/stocks-predictor/actions/runs/34621167684) |
| Brasileirão | integration/cain-status-20260911 | 78cbe4dc2d02b1670149204e939ae2bd6e93ddac | [CI delimitada aprovada](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/34620562548), Python 3.12/3.13/3.14 |
| Crypto exportador | local/l0-exporter | f1052d0d3ce834a25f92582fc9aed3dc4d03ecc3 | Sem alteração de código nesta rodada; exportação real exercitada |
| Crypto pesquisa | research/aave-validation-20260910 | 39b0f57496cee06e6f8841c2476f8428210aaf76 | Sem alteração nesta rodada |
| Contrato | local/l0-contract | 1ddc9a51ce14339559e9a57fe6a6760a2cac2e62 | Sem alteração por esta execução |

Stocks tem [PR83 em rascunho](https://github.com/leonardosovienski/stocks-predictor/pull/83).
Não houve merge em main. O primeiro CI completo detectou a população de código R8
sem os dois novos tools. Conferidos todos os hashes antigos sem alteração, o inventário
corrente recebeu somente as duas entradas novas; históricos, pacote e recibos científicos
permaneceram. A repetição aprovou Python 3.13/3.14, testes, integridade, build e wheel.
A CI global Brasileirão não foi acionada, pois inclui avaliadores protegidos.

O wheel final instalado tem SHA-256
10b1857f028bc82fbc148ed2d62f98b7473b512c8f0c9f3c64a01ef5adcd7cfc.
Arquivo: C:\CAIN\entregas\0.4.4\cain_research-0.4.4-py3-none-any.whl.
Código instalado foi comparado ao wheel e ao commit Cain acima; o fechamento
documental posterior não altera o wheel. O candidato intermediário está preservado
em work/cain_research-0.4.4-before-policy-check.whl e não é a distribuição final.
Suite final local: 381 aprovados, um skip Windows.

Publicações adicionais geradas com exportadores commitados:
Stocks 0a3d1e593069a35e1dd4351c19c11fad9df7271a6b961cf579abf55dd17fe5a5;
Brasileirão e138737a1135f7b0426f119254e2ffa3fa5f54714dbe68670473aa9edbcc0666.
Foram importadas sem duplicar revisões. Histórico Stocks reaberto na interface depois
do reinício; estados e referências continuaram disponíveis.
Recibos locais em entregas/0.4.4/installed-code-receipt.json e final-installed-verification/.

## Alterações concorrentes preservadas

Depois da publicação da implementação surgiram mudanças locais de outra execução:
extração de providers no Cain; registry/publication no contrato; seleção de datasets
no Stocks. Elas não foram criadas, revertidas, adicionadas aos commits ou instaladas
por esta tarefa. Por isso não se declara a árvore de trabalho inteira limpa nem
validada. Os SHAs e o wheel acima delimitam precisamente a entrega verificada.

Na retomada, conferir git status antes de qualquer build, commit ou atualização.
Não reinstalar a árvore atual como se fosse o código validado acima sem revisar essas
mudanças. Código do produtor segue na branch de integração; main não foi substituída.
Inferência real, avaliação humana e vantagem econômica permanecem não demonstradas.
