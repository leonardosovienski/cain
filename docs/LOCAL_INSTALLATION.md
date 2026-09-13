# Instalação local em C:/CAIN

Versão instalada: **0.4.10**, código **dcde48490a15af33048b764cfdb952af7599c3a8**. Modelo e configurações preservados. [Correções e teste real](LLM_FIX_20260913.md). Wheel final e backup prévio em `C:/CAIN/work/qa-llm-fix-20260913`; a instalação usa `C:/CAIN/.venv` e a porta 8877.

## Mapa e registros anteriores

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

O backup da promoção 0.4.8 está em `C:/CAIN/work/qa-full-20260912/promotion-backup` (bancos, documentos e pacote anterior).
As cópias de configuração e o baseline estão em `C:/CAIN/work/qa-full-20260912/backup`.
O backup anterior permanece em `C:/CAIN/work/CAIN-PROMOTION-20260912-210027/backup`.
O wheel 0.4.8 está em `C:/CAIN/work/qa-full-20260912/release`; não foi instalado em modo editável.
O serviço foi reiniciado pelo inicializador padrão, com `CAIN_DB`, `CAIN_RESEARCH_DB` e `CAIN_RESEARCH_POLICY`
apontando para os mesmos caminhos de dados/configuração. Dependências, modelos e política foram preservados.
O serviço temporário de teste 8891 usa cópias isoladas e não substitui a principal.
Antes de restaurar, verificar a identidade do snapshot e ensaiar em destino novo. Preservar dados posteriores ao backup.
Leia [estado atual](../ESTADO_DO_PROJETO.md) para a referência instalada e [continuidade](../CONTINUIDADE.md) para os comandos de conferência.
