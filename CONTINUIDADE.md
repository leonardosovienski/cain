# Continuidade do Cain — 0.4.4

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
