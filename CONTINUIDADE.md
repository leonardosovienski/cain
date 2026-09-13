# Continuidade do CAIN

Reteste posterior: [4/6 inferências aprovadas, 2 falhas reproduzidas](docs/LLM_RETESTE_20260912.md). “Explique melhor” e cópia exata continuam limitados; código e configuração inalterados.

Atualização 0.4.9: código instalado **cba4b5b0d1c0b3dd7dcbbfbaa2a22a1647ad5a20**, modelo padrão **qwen3.5:4b**, porta 8877. Leia [avaliação real da LLM](docs/LLM_CORRECOES_20260912.md). Contexto recente e roteamento de continuações corrigidos; formato estrito e cautela excessiva ainda falham em alguns casos. Backup e recibos em `C:/CAIN/work/qa-llm-20260912`. Somente o modelo mudou nas configurações.

## Registro anterior da 0.4.8 (histórico)

Comece pelo [estado verificado](ESTADO_DO_PROJETO.md). O código operacional de referência é 92b6428 (0.4.8); a branch atual é main.
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

A rodada de [teste integral](docs/TESTE_INTEGRAL_20260912.md) corrigiu conversa cotidiana, aritmética simples
e citações de histórico irrelevante. Fonte final: 624 testes aprovados, um skip e dois avisos.
A instalação principal foi atualizada e reiniciada na 8877, com reteste por interface, API e CLI.
Recibos: `C:/CAIN/work/qa-full-20260912`; backup pré-promoção: `promotion-backup` nesse diretório.
O perfil `qa-cain-20260912` contém apenas testes sintéticos e foi mantido separado.
O modelo livre ainda falhou em seguir pedidos de formato/conteúdo no laboratório; não declarar qualidade semântica geral aprovada.

As correções de Historian a613050 e a integração de contratos já estavam na referência anterior d604a0e e permanecem integradas.
A tarefa real H4 por API e CLI foi executada; não é mais uma pendência de promoção.
O teste confirma campos do relatório congelado, não a interpretação geral do modelo nem o estado atual do produtor.
Auditorias completas, testes de modelos e candidatos Supply continuam disponíveis como [histórico](docs/historico/README.md).

Backup da promoção: `C:/CAIN/work/CAIN-PROMOTION-20260912-210027/backup`.
Backup/restore da integração Stocks: `C:/CAIN/entregas/stocks-main-integration-20260912`.
Uma restauração deve ir primeiro para destino novo; não sobrescrever bancos de uso com snapshots antigos.
