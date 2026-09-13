# Continuidade do CAIN

Instalado **0.4.12**, código `5364c3b1de5d01c1cf6747b9eed52e562e1a63cd`, branch **main**, ambiente não editável `C:/CAIN/.venv`. Checkout: `C:/CAIN/projeto`; interface http://127.0.0.1:8877/; atalho `C:/CAIN/ABRIR_CAIN.cmd`. Commits posteriores de documentação não alteram o pacote.

Leia [estado](ESTADO_DO_PROJETO.md), [cobertura dos projetos](docs/COBERTURA_PROJETOS_20260913.md) e [instalação](docs/LOCAL_INSTALLATION.md).

## Resultado vigente

O CAIN **não recebe os projetos inteiros**. Crypto tem 15 registros de dois arquivos; Stocks, um status e um acervo Bundle com um pacote/duas entidades; Brasileirão, três registros de um relatório. Existem acervos adicionais com sobreposição. As contagens e todos os itens desses seis acervos foram auditados. A interface, API `/research/coverage` e CLI `research ... coverage` agora separam Snapshot, Bundle, conteúdo recebido, referências e geração permitida.

Três Bundles adicionais foram importados somente em QA: 36 entidades, 19 artefatos, 14 materializados com hashes corretos e cinco somente referenciados. Não foram conectados à política principal. Os próprios manifestos são parciais e restringem geração. Nenhum produtor foi alterado.

Três workflows de seis etapas concluíram e reabriram os checkpoints. A redação não foi inteiramente aprovada: Crypto e Stocks tiveram extrapolações; Brasileirão tratou o texto de uma hipótese como resultado estabelecido apesar do estado bloqueado. Essa falha permanece aberta. Nove inferências redigiram as etapas; outras três explicações selecionaram trechos, sem síntese livre irrestrita. Os módulos de geração permaneceram byte a byte iguais entre 0.4.11 e 0.4.12.

## Preservação e evidências

Dados em `C:/CAIN/dados`; política `C:/CAIN/config/research-policy.json`; configuração `C:/CAIN/projeto/cain.toml`. Modelo qwen3.5:4b, Ollama 0.34.0, temperatura 0, seed 42, think=false, contexto 8192, num_predict 768 e timeout 240 s preservados. As preferências de leo foram mantidas.

Rodada atual: `C:/CAIN/work/coverage-projects-20260913`. Backup de bancos/configuração/wheel 0.4.11 em `baseline`; ensaios separados em `isolated`, `audit` e `bundle-candidates`. Não restaurar esses snapshots sobre dados atuais. O wheel final está em `release`, com hash no mapa de instalação.

Recibos principais: `coverage-audit.json`, `bundle-candidates/report.json`, `full-workflows.json`, `semantic-review.json`, `workflow-installed-readback.json`, `installed-api.json`, `installed-cli.json`, `ui-verification.json`, `preservation.json`, `git-publication.json` e `ci-final.json`.

Antes de retomar, conferir Git local/remoto e `/health`. Para ampliar acesso aos produtores, definir os novos artefatos/exportações; leitura de um recorte não significa acesso aos bancos ou compreensão de todo o projeto. Não alterar lacres, restrições ou hipóteses para obter aprovação. Para corrigir a redação, usar o caso Brasileirão já registrado como regressão semântica.

Histórico: [0.4.11](docs/LLM_REAL_20260913.md) e [0.4.10](docs/LLM_FIX_20260913.md). Recibos anteriores em `C:/CAIN/work/qa-real-20260913` permanecem preservados. A antiga contagem de “dois Bundles” foi corrigida para duas entidades de um pacote. Testes técnicos não certificam conclusões científicas/econômicas.
