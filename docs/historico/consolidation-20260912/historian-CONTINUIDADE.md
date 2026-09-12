# Continuidade do Cain - 0.4.7

## Estado vigente — 12/09/2026

Correções do Historian, empacotamento e busca documental: código instalado
`0c8814901d3d365a2eec4b0c7386b59f460d349d`, antecedido por `6149526`.
Branch de publicação: `fix/historian-integrity-20260912`, repositório
[leonardosovienski/cain](https://github.com/leonardosovienski/cain/tree/fix/historian-integrity-20260912).
Checkout: `C:/CAIN/work/historian-operational-fix-20260912`.
Commits posteriores somente de Markdown não mudam o código instalado.

Wheel instalado SHA-256:
`a09b56c744260468702bd4a8ab71e132e8ede354f34e8c0ef491d5783ced2e1b`.
Runtime `C:/CAIN/.venv`, abrir `C:/CAIN/ABRIR_CAIN.cmd`, porta 8877.
Distribuição 0.4.7; não identificar o reparo somente pelo número da versão.

Leia [a auditoria ampliada](docs/research/AUDITORIA_OPERACIONAL_20260912.md)
e [o reparo anterior do Historian](docs/research/HISTORIAN_OPERACIONAL_20260912.md).
459 testes passaram, um skip Windows e 17 checks da API real passaram.
Resumos livres tiveram erros semânticos e continuam sem aprovação geral.
A busca operacional usa trechos literais; não reescreve citações para cumprir
preferências de estilo. Fontes dos produtores não foram alteradas.

Recibos e recuperação: `C:/CAIN/entregas/full-operational-audit-20260912`,
com `FINAL_VERIFICATION.json`, `final-wheel-suite.xml`, `real-api-extractive.json`,
`candidate/`, `rollback/` e `before-data/`. Os bancos e a política mantiveram seus
hashes durante a auditoria e instalação. Testes mutáveis usaram cópias.
Para reverter somente o código, usar o wheel em `rollback/`; não sobrescrever
bancos com cópias antigas após consultas novas. Tentativas e falhas intermediárias
estão em `C:/CAIN/work/full-operational-audit-20260912`.

Para conferir publicação: comparar `git rev-parse HEAD` com
`git ls-remote origin refs/heads/fix/historian-integrity-20260912`.
A aprovação local não afirma aprovação da CI remota. Não publicar bancos,
políticas locais, payloads ou respostas privadas. Não há merge implícito em main.

## Histórico anterior à auditoria de 12/09/2026


### Testes individuais posteriores à instalação anterior

Leia [o relatório dos modelos e relatos individuais](docs/research/TESTES_INDIVIDUAIS_20260911.md).
Correções e protocolo estão em `C:\CAIN\work\individual-model-tests-20260911`,
branch `validation/individual-models-20260911`; evidências em
`C:\CAIN\entregas\individual-models-20260911`. A instalação principal abaixo
foi preservada. Não confundir suíte técnica aprovada com interpretação validada:
há respostas reais dos modelos que não são sustentadas pelas fontes.
As correções usam `research-workflow/5` e `addressable-review/3`; tarefas antigas
permanecem consultáveis, mas uma tarefa pendente de protocolo anterior exige
um novo fluxo para continuar com os novos prompts.

Entrega atual: [integracao, extracao e debate](docs/DELIVERY_047.md).
Codigo: `C:\CAIN\work\research-capabilities-20260911`, branch
`feature/research-capabilities-20260911`. Arquitetura 2e9350c integrada.
Instalacao nao editavel em `C:\CAIN\.venv`; dados em `C:\CAIN\dados`.
Abra `C:\CAIN\ABRIR_CAIN.cmd`, porta 8877. Recibos em entregas/0.4.7.
Nao publicar bancos ou respostas privadas. Jobs novos usam protocolo /4;
jobs anteriores permanecem consultaveis/cancelaveis.

Os registros seguintes sao historicos.

## Entrega arquitetural 0.4.5 publicada — 11/09/2026

A implementação e a validação atuais estão em [ARCHITECTURE_IMPLEMENTATION.md](ARCHITECTURE_IMPLEMENTATION.md). [Release 0.4.5](https://github.com/leonardosovienski/cain/releases/tag/v0.4.5), fonte `37cdc604d4c3bbb66684c018c76a4ea38713ee2a`, passou na CI Python 3.11/3.12/3.13 e em instalação offline não editável. Factories saíram da CLI; admissão antecede leitura e revogação restringe histórico derivado. O intercâmbio com contrato produtor 1.0.1 e leitor 1.0.0 passou, incluindo backup/restore sem origem e referências por hash. A configuração, os modelos, os dados reais e os três produtores da entrega 0.4.4 foram preservados. Nenhum serviço ou modelo foi iniciado por esta revisão.

Atualizado em 11/09/2026. Leia [DELIVERY_044](docs/DELIVERY_044.md) para usar,
reproduzir, conferir limites e recuperar a instalação sem este chat.

[Publicação, CI e alterações concorrentes](docs/PUBLICATION_044.md) delimitam o
commit instalado. Há trabalho local concorrente preservado fora desta entrega;
não presuma que a árvore inteira é igual ao wheel validado.

Instalação principal: C:\CAIN; abrir ABRIR_CAIN.cmd, http://127.0.0.1:8877.
Pacote 0.4.4 instalado por wheel em .venv; fontes em projeto, branch local/l0-historian.
O contrato independente continua em contrato, branch local/l0-contract, sem alteração.
Bancos próprios em dados/workspace.db e dados/research.db; política v2 em
config/research-policy.json. Nenhum banco científico foi incorporado.

Acervos reais: crypto (15 registros/7 evidências), stocks (1/1), brasileirao (3/3).
São publicações limitadas de relatórios, com fontes, estados, offsets, hashes e lacunas.
heterogeneous anterior permanece preservado. A consulta funciona sem os produtores,
Ollama ou embeddings. Novas publicações exigem exportação e importação explícitas.
Cada produtor guarda publicações em sua própria raiz; veja a política e a entrega.

Nesta rodada: 381 testes aprovados, um skip Windows, lint e wheel offline aprovados;
CLI, API e interface real; reimportação, referências, reconstrução e restauração;
consulta instalada com raízes produtoras indisponíveis. Doze perguntas PT/EN passaram
nos dois modos de recuperação. Não houve superioridade demonstrada nem inferência real.
Ollama indisponível na porta local padrão; avaliação humana/held-out segue pendente.

Novos comandos cain archive backup/restore incluem bancos, knowledge e política.
Snapshots são consistentes por banco, não globalmente atômicos. Backup anterior em
C:\CAIN\work\before-044-backup, restauração ensaiada em before-044-restored.
Wheel e recibos em C:\CAIN\entregas\0.4.4. Logs/XML em C:\CAIN\work.
Não enviar bancos, publicações locais ou configurações privadas ao GitHub.

[Comparação de sistemas](docs/research/market-comparison-20260911.md) registra decisões
adotar/adaptar/avaliar/adiar/rejeitar. [ADR 0013](docs/adr/0013-three-producers-and-complete-backup.md)
explica a ampliação dos exemplos para produtores reais e a política compatível.
As correções de arquitetura 0.4.3 permanecem; relatórios anteriores são históricos.

Para retomar: conferir Git, HEAD e remoto, ler a entrega; executar testes proporcionais
em ambiente separado. Não instalar runtimes científicos Stocks/BR no Cain nem ativar
pesquisa, modelos, capital, apostas ou agendamentos por inferência deste documento.
Rollback 0.4.3 requer política v1 preservada; não apagar o acervo nem reescrever fontes.
