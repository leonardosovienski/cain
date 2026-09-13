# Instalação local em C:/CAIN

| Caminho | Finalidade |
|---|---|
| projeto | Checkout canônico do CAIN em main |
| .venv | Pacote instalado, separado da árvore de desenvolvimento |
| dados | workspace.db e research.db; conteúdo de uso, fora do Git |
| config | Política de acesso e configuração local; fora do Git |
| modelos / runtime | Pesos, Ollama e Python locais |
| work | Candidatos, worktrees históricos, scripts e recibos de rodadas |
| entregas | Distribuições, backups e evidências de entregas |
| historico | Materiais originais e cópias de documentos substituídos |
| contrato | Repositório independente de contratos; não é parte do Git do CAIN |

`ABRIR_CAIN.cmd`, `CAIN.cmd` e `CAIN_RESEARCH.cmd` na raiz apontam para projeto e preservam os bancos em dados.
Suas cópias versionadas estão em [installation/windows](../installation/windows/README.md).
O atalho principal abre http://127.0.0.1:8877/. O inicializador genérico dentro do checkout usa 8000 por padrão.
O arquivo ignorado `projeto/.cain.local.json` liga o inicializador ao Python local; não contém a identidade do código instalado.

As pastas work/entregas/historico não são lixo: podem conter fontes, backups ou recibos únicos.
A organização documental não removeu, moveu nem mesclou esses conteúdos. Não usar rotinas de limpeza indiscriminada.

O backup da última promoção está em `C:/CAIN/work/CAIN-PROMOTION-20260912-210027/backup`.
Antes de restaurar, verificar a identidade do snapshot e ensaiar em destino novo. Preservar dados posteriores ao backup.
Leia [estado atual](../ESTADO_DO_PROJETO.md) para a referência instalada e [continuidade](../CONTINUIDADE.md) para os comandos de conferência.
