# Instalação local em C:/CAIN

## Instalação vigente — revisão dfabf6d

Instalado em 13/09/2026, código `dfabf6dab05df1662e9882ebe1091236daa14724`, versão nominal **0.4.12**, ambiente `C:/CAIN/.venv`, serviço http://127.0.0.1:8877/. Inclui a proteção de análise e o protocolo research-workflow/10. A versão nominal não mudou; o commit e o hash abaixo distinguem este pacote do anterior.

Wheel: `C:/CAIN/work/install-dfabf6d-20260913/release/cain_research-0.4.12-py3-none-any.whl`. SHA256: `d32089be517207ea04f405924b0394391aed68febdd58f71f8ed6788b753a520`.

Health OK; pip check aprovado; 62 arquivos iguais a fonte/wheel/instalação; 20 testes de análise passaram contra o pacote instalado, com 2 avisos. Configurações, dependências de terceiros e todas as linhas preexistentes dos dois bancos preservadas; integridade SQLite OK. Não foi rodada nova certificação semântica com modelo nesta instalação.

Backup consistente dos bancos, configurações e wheel anterior em `C:/CAIN/work/install-dfabf6d-20260913/baseline`. Recibos no diretório pai: `verification.json`, `health.json`, `install.log`, `pip-check.log`, `restart.log`, `tests-installed.log`. Não restaurar bancos antigos sobre dados posteriores. Para recuperação do software, usar o wheel anterior preservado, sem sobrescrever bancos/configurações.

## Registro histórico — primeira instalação 0.4.12

Versão **0.4.12**, código `5364c3b1de5d01c1cf6747b9eed52e562e1a63cd`. Serviço http://127.0.0.1:8877/; ambiente não editável `C:/CAIN/.venv`.

O checkout main recebeu depois a [proteção de análise](ANALYSIS_GUARD_20260913.md), ainda não instalada. A comparação de 62 arquivos abaixo corresponde à fonte do commit instalado acima, não à fonte atual de main.

Wheel: `C:/CAIN/work/coverage-projects-20260913/release/cain_research-0.4.12-py3-none-any.whl`.
SHA256: `20bf092380eb9f2a62fee9cf19975dd3586766309b9c99d0c00f60b0edea73f9`. Os 62 arquivos conferem com fonte/wheel/instalação; pip check aprovado. Somente cain-research foi atualizado.

Backup anterior à atualização: `C:/CAIN/work/coverage-projects-20260913/baseline`, com bancos, configuração, política, atalhos e wheel 0.4.11. Não restaurar bancos antigos sobre o uso atual. Dados e configuração continuam nos mesmos caminhos; o inicializador padrão mantém as variáveis da instalação principal.

A política principal continua com os seis acervos anteriores. As importações dos três Bundles adicionais ocorreram somente em `bundle-candidates`, banco de QA. [Cobertura real e limitações](COBERTURA_PROJETOS_20260913.md).

Recibos de instalação, API, CLI, interface e preservação estão no diretório desta rodada. Publicação/CI ficam em `git-publication.json` e `ci-final.json`; eles identificam a referência documental final, separada do código instalado.

## Registro anterior — 0.4.11

Versão instalada: **0.4.11**, código **b8bed8fd103d265f3158d5dde5fd32895ca8f439**. Ambiente não editável `C:/CAIN/.venv`; serviço http://127.0.0.1:8877/; modelo `qwen3.5:4b`, configuração e dependências de terceiros preservados. [Resultados reais](LLM_REAL_20260913.md).

Wheel instalado: `C:/CAIN/work/qa-real-20260913/release/cain_research-0.4.11-py3-none-any.whl`.
SHA256: `9bcb2031bff243c7349ba03cb4f5cee8783939e932346d8d085323506812b727`.

Backup inicial em `C:/CAIN/work/qa-real-20260913/promotion-backup`; backup anterior à primeira atualização da rodada em `pre-install-backup`, no mesmo diretório. Incluem bancos via SQLite backup, configurações, atalhos e wheel 0.4.10. O arquivo `intermediate-before-memory-fix.whl` não é o release final.

Os 61 arquivos instalados foram comparados com a fonte e o wheel final. A atualização usou `pip install --no-deps --no-index --force-reinstall`; `pip check` passou. Serviço reiniciado pelo inicializador padrão, mantendo `CAIN_DB`, `CAIN_RESEARCH_DB` e `CAIN_RESEARCH_POLICY` nos caminhos existentes. Apenas `cain-research` mudou na lista de dependências.

Recibos: `primary-health.json`, `installed-api.json`, `installed-delivery-english.json`, `installed-format-retest.json`, `installed-cli.log`, `primary-ui-final.json`, `preservation-0.4.11.json`, `wheel-check.json` e `git-publication.json` no diretório da rodada. Não apagar esse diretório nem restaurar seus bancos sobre o uso atual.

O backup `refinement-backup` preserva também a primeira instalação candidata 0.4.11, anterior ao ajuste de aprofundamento. O arquivo `first-installed-0.4.11.whl` é intermediário; o wheel final é somente o de `release`, com o hash acima. O wheel e o backup da 0.4.10 continuam em `C:/CAIN/work/qa-llm-fix-20260913`; o relatório daquela versão é histórico.

Os backups `literal-backup`, `format-backup`, `language-backup` e `schema-backup` preservam os candidatos posteriores e seus dados. `schema-backup` é o imediatamente anterior à instalação final. Os arquivos `second-installed-0.4.11.whl` até `fifth-installed-0.4.11.whl` são intermediários. O hash do wheel em `release` acima identifica a entrega final.

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
O serviço temporário da rodada anterior em 8891 usou cópias isoladas e foi encerrado; não substitui a principal.
Antes de restaurar, verificar a identidade do snapshot e ensaiar em destino novo. Preservar dados posteriores ao backup.
Leia [estado atual](../ESTADO_DO_PROJETO.md) para a referência instalada e [continuidade](../CONTINUIDADE.md) para os comandos de conferência.
