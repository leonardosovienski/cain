# Retomada após encerramento do chat — Stocks/CAIN

Checkpoint documental de 16/09/2026. O código e os relatórios anteriores estavam
publicados na main `4af00eace4d2f1c4b606cf7f3d0f28b8762f0f40` e o checkout desta
entrega estava limpo antes deste checkpoint. Nenhum arquivo foi apagado.

## Tarefa que continua

A tarefa Codex **Validar CAIN com todas as hipóteses Stocks** já foi criada e
estava ativa na conferência deste checkpoint. ID:
`01a0ac76-3412-75e2-9e39-ebcba853416d` (host local).
Ela recebeu o mandato completo e os caminhos de retomada; não depende de manter
aberto o chat anterior. Seu trabalho em andamento não é declarado concluído ou
incluído neste checkpoint.

O objetivo autorizado é criar uma conversa dedicada dentro do CAIN, testar
respostas reais sobre H1–H22, corrigir falhas de recuperação/contexto/interpretação,
executar os testes viáveis de cada protocolo e registrar resultados e motivos.
Não substituir inferência real por respostas escritas pelo avaliador. Avaliar todas
não obriga aprovação: preservar veredictos históricos, hipóteses refutadas,
inconclusivas, bloqueios e tentativas inválidas no denominador.

## O que já foi entregue

- [Campanha realizada](STOCKS_CAMPAIGN_20260916.md): projeto CAIN com 112 documentos,
  22 jobs, testes locais e reproduções históricas H21/H22 verificadas.
- [Correções, instalação e limites semânticos](STOCKS_STUDY_READINESS_20260915.md).
- Ferramenta versionada: `tools/run_stocks_campaign.py` e suas regressões.
- PRs #3–#6 integradas. As conferências Git confirmaram main no SHA acima antes
  da inclusão deste documento; para o estado posterior, consultar o remoto.

O piloto livre anterior não aprovou semanticamente H1/H17/H22: omissão da
confiabilidade em H1, perda de revisão/contexto em H17 e confusão de critérios
causais em H22. A nova tarefa deve enfrentar essas falhas. Os 22 jobs da campanha
anterior foram 15 leituras literais e 7 buscas, não 22 experimentos econômicos novos.

## Entrega local preservada

- Checkout da tarefa seguinte: `C:/CAIN/work/stocks-study-20260915/checkout`.
- Runtime: `C:/CAIN/work/stocks-study-20260915/runtime-r3/Scripts/python.exe`.
- Bancos principais: `C:/CAIN/dados/research.db` e `C:/CAIN/dados/workspace.db`.
- Política: `C:/CAIN/config/research-policy.json`.
- Projeto CAIN: **Stocks — pesquisa e validação**, id
  `4c57f901-f8fb-455e-ad5b-453a6f41b9e0`, usuário local `leo`.
- Pesquisa: coleção `stocks`, projeto vazio; não confundir com o UUID dos documentos.
- Recibos e dossiês: `C:/STOCKS/work/cain-campaign-20260916-primary` e
  `C:/STOCKS/work/cain-campaign-20260916-qa`.
- Scripts auxiliares, pilotos e recibos de instalação:
  `C:/CAIN/work/stocks-study-20260915`.
- Cópias de recuperação: `activation-backup`, `activation-r3-backup` nesse
  diretório, e `workspace-before.db` na campanha principal.

Código, testes e Markdown de continuidade estão no GitHub. Bancos, modelos,
fontes volumosas, dossiês privados, logs e scripts temporários de execução
permanecem locais. GitHub não é uma cópia integral desses dados. Apagar o chat
não autoriza apagar diretórios, documentos do CAIN, backups ou a tarefa seguinte.

## Regras de continuação

Ler AGENTS e os documentos exigidos no Stocks; trabalhar sozinho. Preservar os
12 bancos, fontes, protocolos, configurações, resultados negativos e trabalho
concorrente. Não resetar o checkout original `C:/CAIN/projeto`. Usar QA consistente
antes de mudanças principais, mantendo evidências. Nada de operações financeiras,
contas, ordens ou automações recorrentes. Não instalar Stocks/Core no Windows;
runtime completo em Linux CI e somente verificadores stdlib documentados localmente.
Não transformar repetição histórica em evidência independente nem antecipar a
janela prospectiva de 2027. Publicar apenas código/documentação e recibos públicos.
