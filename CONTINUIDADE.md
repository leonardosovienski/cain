# Continuidade do CAIN

Versão instalada: **0.4.11**, código **b8bed8fd103d265f3158d5dde5fd32895ca8f439**, branch **main**. Commits posteriores de documentação não alteram o pacote. O SHA final publicado fica no recibo `C:/CAIN/work/qa-real-20260913/git-publication.json`; conferir novamente local/remoto antes de retomar.

Leia [estado atual](ESTADO_DO_PROJETO.md), [testes reais e limites desta rodada](docs/LLM_REAL_20260913.md) e [instalação](docs/LOCAL_INSTALLATION.md).

## Instalação e dados

- Checkout canônico: `C:/CAIN/projeto`; ambiente não editável: `C:/CAIN/.venv`.
- Interface principal: http://127.0.0.1:8877/; atalho `C:/CAIN/ABRIR_CAIN.cmd`.
- CLI: `C:/CAIN/CAIN.cmd` e `C:/CAIN/CAIN_RESEARCH.cmd`.
- Dados de uso: `C:/CAIN/dados`; política: `C:/CAIN/config/research-policy.json`.
- Modelo preservado: `qwen3.5:4b`, Ollama 0.34.0, CPU. Temperatura 0, seed 42, think=false, contexto 8192, geração 768, timeout 240 s.
- Recibos e scripts: `C:/CAIN/work/qa-real-20260913`.
- Backups: `promotion-backup` (início da rodada) e `pre-install-backup` (antes da atualização), nesse diretório. Ambos contêm bancos, configuração e wheel 0.4.10. Não restaurar snapshots antigos sobre dados atuais.
- `refinement-backup`, `literal-backup`, `format-backup`, `language-backup` e `schema-backup` preservam candidatos 0.4.11; `schema-backup` é o imediatamente anterior à instalação final. O wheel final é somente o de `release`, com hash no mapa da instalação.

## O que mudou

1. A pendência documentada de `language=en` foi reproduzida e corrigida nos casos retestados. A projeção do perfil e as instruções de conversa usam inglês quando ele está ativo; a entrada derivada da geração recebe um lembrete curto de idioma. O texto original fica no histórico. Não há tradução posterior nem retry automático.
2. Cabeçalhos de exercícios explicitamente fictícios/hipotéticos passam a selecionar conversa; o classificador recusava a comparação fornecida.
3. O filtro de memória não descarta mais um episódio só por conter “Responda em uma frase”. Isso eliminava os preços do contexto de “Explique melhor”. Preferências reconhecidas continuam filtradas para não reativar escopos antigos.
4. Continuações reconhecidas recebem uma instrução derivada para explicar o raciocínio e acrescentar um detalhe concreto, evitando apenas repetir a conclusão. O primeiro pacote candidato ainda repetia; o refinamento foi retestado com diferença de preço e custo por tarefa corretos.
5. Pedidos claros de cópia literal e JSON selecionam conversa diretamente. A cópia pela interface ainda falhava no classificador, embora a LLM passasse com intenção explícita; o roteamento foi corrigido e retestado sem intenção explícita.
6. O lembrete de idioma pede preservação de chaves e valores literais. Ele passou em contexto novo, mas não resolveu a tradução de chaves no histórico existente. Declarações explícitas e limitadas de chaves literais JSON agora usam o schema do provedor: as chaves e os tipos explicitamente declarados são restritos, os valores continuam gerados pela LLM. O mesmo histórico foi retestado em cópia isolada e na instalação principal.

As correções anteriores de cópia exata e JSON passaram novamente, inclusive com inglês ativo. A memória recuperou o fato de um exercício em outra sessão do mesmo usuário e não o revelou a outro usuário. O relatório distingue os testes com inferência real das rotinas determinísticas e dos testes simulados.

## Limites e próxima retomada

- Há verbosidade adicional: convites opcionais e orientações além do pedido. O refinamento de continuação acrescentou cálculos corretos, mas a interface extrapolou uma vantagem “a longo prazo” sem dados para isso. Aprofundamento semântico permanece parcial; não apresentar a continuação como integralmente certificada.
- Inferência local lenta; tempos desta rodada não são benchmark de desempenho isolado.
- Workflows verificados em `inspect/search`, checkpoint, leitura posterior, conclusão, cancelamento, trace e isolamento. A geração completa em seis etapas não foi repetida nesta rodada.
- Consulta Historian de H4 usou campos literais; não é certificação da síntese livre nem do produtor dos dados.
- CI remota desta referência e avaliação humana independente não verificadas. Não houve treino ou certificação geral da LLM.

Antes de retomar, executar `git status --short`, `git fetch origin --prune`, `git rev-parse HEAD` e `git ls-remote origin refs/heads/main`; conferir `/health` e o pacote instalado. Usar bancos e perfis QA isolados, preservar as preferências de `leo` e não apagar `work` indiscriminadamente.

Scripts reprodutíveis e recibos finais estão descritos no relatório. Não reclassificar falhas intermediárias como estado final: `semantic.json` conserva uma falha anterior de continuidade; consultar também `context-retest.json` e `primary-ui-final.json`.

Histórico: [0.4.10](docs/LLM_FIX_20260913.md), [0.4.9](docs/LLM_RETESTE_20260912.md), [teste integral anterior](docs/TESTE_INTEGRAL_20260912.md). Os recibos antigos em `C:/CAIN/work/qa-llm-fix-20260913` continuam preservados.
