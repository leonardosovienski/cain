# Continuidade do CAIN

Comece pelo [estado verificado](ESTADO_DO_PROJETO.md). O código operacional de referência é d604a0e; a branch atual é main.
O [manifesto operacional](operational-state.json) distingue commit de código, wheel instalado e CI.

## Onde trabalhar e abrir

- Código e documentação: `C:/CAIN/projeto`.
- Abrir: `C:/CAIN/ABRIR_CAIN.cmd`, porta 8877.
- CLI geral: `C:/CAIN/CAIN.cmd`; pesquisa: `C:/CAIN/CAIN_RESEARCH.cmd`.
- Ambiente principal: `C:/CAIN/.venv`; bancos: `C:/CAIN/dados`; política: `C:/CAIN/config/research-policy.json`.
- [Mapa da instalação](docs/LOCAL_INSTALLATION.md): responsabilidades das outras pastas.

Os worktrees em `work` preservam rodadas e evidências. Não substituir a main por um checkout histórico, mover dados ou reinstalar a partir de recibos antigos.
Snapshot/Bundle dos produtores são recebidos conforme grants; não se incorporam bancos científicos ao Git do CAIN.

## Retomar sem o chat

1. Conferir `git status --short --branch`, `git fetch origin --prune`, `git rev-parse HEAD` e `git ls-remote origin refs/heads/main` em `C:/CAIN/projeto`.
2. Verificar alterações concorrentes e ler o requisito da nova tarefa. A documentação histórica não autoriza operações novas.
3. Usar candidato e dados isolados para falhas induzidas, migrations, restore ou testes mutáveis; preservar a instalação em uso.
4. Testar no nível afetado. Distinguir fonte, pacote instalado, processo real, inferência e tarefa de produto.
5. Para promover código, registrar wheel, dependências, backup e processo reiniciado. Um commit só de Markdown não exige reinstalação.

## Entregas fechadas

As correções de Historian a613050 e a integração de contratos estão na main operacional d604a0e.
A tarefa real H4 por API e CLI foi executada; não é mais uma pendência de promoção.
O teste confirma campos do relatório congelado, não a interpretação geral do modelo nem o estado atual do produtor.
Auditorias completas, testes de modelos e candidatos Supply continuam disponíveis como [histórico](docs/historico/README.md).

Backup da promoção: `C:/CAIN/work/CAIN-PROMOTION-20260912-210027/backup`.
Backup/restore da integração Stocks: `C:/CAIN/entregas/stocks-main-integration-20260912`.
Uma restauração deve ir primeiro para destino novo; não sobrescrever bancos de uso com snapshots antigos.
