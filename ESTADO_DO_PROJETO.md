# Estado verificado do CAIN

CAIN **0.4.11**, código instalado **b8bed8fd103d265f3158d5dde5fd32895ca8f439**. Checkout em `C:/CAIN/projeto`, branch **main**; instalação não editável em `C:/CAIN/.venv`; interface http://127.0.0.1:8877/.

| Item | Verificação desta rodada |
|---|---|
| Modelo | qwen3.5:4b / Ollama 0.34.0; parâmetros e configuração preservados |
| Correções | Idioma inglês ativo; roteamento de exercícios, cópia e JSON; preservação dos fatos e instrução de aprofundamento |
| Engenharia | 673 testes na suíte completa; 174 afetados após a última proteção de entrada; 1 skip Windows na suíte completa, 2 avisos; Ruff aprovado |
| Wheel | Instalação offline nova, dependências válidas e 61 arquivos iguais à fonte e ao wheel |
| Inferência | Regressão de conversa, cópia, JSON, idioma por escopo, memória, resumo e código; limites de verbosidade registrados |
| Projetos/documentos | Criação, deduplicação, isolamento, preferências, idempotência, feedback e citações verificados em banco isolado |
| Pesquisa/workflows | Snapshot/Historian literal, dois Bundles; inspect/search, checkpoint, conclusão e cancelamento |
| Preservação | Bancos íntegros, todas as linhas preexistentes e configurações preservadas; só cain-research atualizado |
| Limites | CPU lenta, orientação extra e extrapolação sobre longo prazo na continuação da interface; aderência semântica parcial, sem certificação geral da LLM |

[Relatório completo](docs/LLM_REAL_20260913.md), [continuidade independente do chat](CONTINUIDADE.md), [instalação e backups](docs/LOCAL_INSTALLATION.md) e [manifesto](operational-state.json).

A falha de idioma da 0.4.10 é histórica e foi corrigida nos casos retestados; isso não prova aderência a qualquer pergunta. A geração completa dos workflows em seis etapas, CI remota desta referência e avaliação humana independente não foram verificadas nesta rodada.
