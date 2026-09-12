# Continuidade do Cain - 0.4.7

<!-- SUPPLY-GIT-DELIVERY-20260912 -->
**Continuidade atual desta branch:** [CAIN Supply — entrega e retomada](docs/supply/README.md). Código final materializado na árvore normal; candidato pronto para revisão de congelamento delimitada, sem implantação. As notas anteriores abaixo são históricas e não descrevem o novo checkout.
<!-- /SUPPLY-GIT-DELIVERY-20260912 -->


Leia primeiro o [encerramento da sessão CAIN Supply](docs/research/SESSION_HANDOFF_20260912.md), com decisões, erros, pendências e prompt de retomada.

<!-- DOC-SYNC-20260912 -->
> **Estado de publicação em 12/09/2026:** leia [a continuidade atual](PUBLICATION_STATUS_20260912.md). Branch `feature/research-bundle-v1`. O código deste projeto foi publicado na branch indicada. O candidato CAIN Supply permanece sem aprovação de estabilização. Afirmações anteriores de “sem push” descrevem a etapa histórica anterior à autorização.
<!-- /DOC-SYNC-20260912 -->


## Candidato local ResearchBundleV1

Leia [BUNDLE_REPORT](docs/research/BUNDLE_REPORT.md) e o baseline/ADR vinculados.
Worktree `C:/CAIN/work/research-bundle-v1`, base `780b020`, sem instalação operacional
ou publicação. Records/Objects/References/Lineage passaram no E2E de três recortes;
as lacunas temporais, de dados e de matriz estão explicitadas. Preserve o acervo.

**Atualização operacional autorizada:** a revisão foi instalada e publicada na branch
`review/individual-models-20260911`. Leia [o recibo de instalação](docs/research/INSTALACAO_REVISAO_20260911.md).
As afirmações de não instalação abaixo descrevem a etapa anterior à autorização.

## Revisão independente da entrega do outro chat

Leia [REVISAO_INDEPENDENTE_20260911](docs/research/REVISAO_INDEPENDENTE_20260911.md).
Código corrigido: `86c38f8a333f278084adac3abc2ebe40c48b616c`, branch local
`review/individual-models-20260911`, checkout `C:\CAIN\work\independent-review-20260911`.
Evidências privadas: `C:\CAIN\entregas\independent-review-20260911`.
O outro chat continua identificado pela branch `validation/individual-models-20260911`
e pelo commit publicado `e1786fe`; o código comparado foi `dc114fc`.
O trabalho anterior deste chat continua em `feature/research-capabilities-20260911`,
commit `231ffa8`. Seus arquivos e a instalação principal foram preservados.

A revisão usa `research-workflow/6`, `addressable-review/4` e preserva blocos
completos de contexto, incluindo negações. Jobs pendentes /4 e /5 ficam legíveis
e canceláveis, mas não avançam sob semântica nova. Não migrar jobs nem instalar
ou integrar automaticamente esta branch. As sínteses ainda têm erros semânticos.
Os registros abaixo descrevem entregas anteriores, não a promoção desta revisão.

## Testes individuais posteriores à instalação

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
