# Continuidade do CAIN

Versão local atual: **0.4.10**, código **dcde48490a15af33048b764cfdb952af7599c3a8**, branch **main**. Commits posteriores de documentação não mudam o pacote instalado.

Leia [estado atual](ESTADO_DO_PROJETO.md), [correções e testes reais](docs/LLM_FIX_20260913.md) e [mapa da instalação](docs/LOCAL_INSTALLATION.md).

## Instalação e preservação

- Checkout: C:/CAIN/projeto. Ambiente não editável: C:/CAIN/.venv.
- Interface: http://127.0.0.1:8877/; atalho C:/CAIN/ABRIR_CAIN.cmd.
- CLI: C:/CAIN/CAIN.cmd e C:/CAIN/CAIN_RESEARCH.cmd.
- Bancos de uso: C:/CAIN/dados; política: C:/CAIN/config/research-policy.json.
- Modelo: qwen3.5:4b. Configuração preservada nesta rodada; inferência em CPU continua lenta.
- Evidências e backup: C:/CAIN/work/qa-llm-fix-20260913. Manter dados QA separados; não apagar work indiscriminadamente.

## Retomar

1. Conferir git status, git fetch origin --prune, git rev-parse HEAD e git ls-remote origin refs/heads/main.
2. Ler o pedido atual e conferir alterações concorrentes antes de agir.
3. Usar dados isolados em testes mutáveis; não restaurar snapshots sobre bancos em uso.
4. Distinguir teste de engenharia, inferência real e aderência semântica. Saudação automática não comprova qualidade da LLM.
5. Após código, construir wheel, registrar backup e atualizar instalação; retestar o funcionamento real. Markdown sozinho não exige reinstalar.

As duas regressões anteriores eram continuação genérica e cópia exata. A nova instrução melhorou ambas; a bateria ampliada encontrou também JSON com Markdown, corrigido e retestado. Ainda há elaboração desnecessária em respostas sobre fontes incompletas. Consulte os resultados por camada no relatório; não declarar qualidade geral certificada.

Histórico: [teste integral](docs/TESTE_INTEGRAL_20260912.md), [comparação de modelos](docs/LLM_CORRECOES_20260912.md), [reteste da 0.4.9](docs/LLM_RETESTE_20260912.md). Esses relatórios preservam resultados das versões anteriores.

Pendência nova: preferência ativa de inglês não foi respeitada em uma pergunta portuguesa; tentativas sem melhora foram descartadas. Consulte o relatório antes de considerar idiomas aprovados.

## Retomada sem este chat — fechamento de 13/09/2026

O trabalho de código desta rodada está concluído e instalado; o próximo foco é a pendência de idioma, não refazer a instalação nem reabrir como falha os casos de continuação/cópia que passaram. O fechamento documental não executou nova inferência: conferiu serviço, pacote, dados e Git.

Reprodução observada: em um usuário QA novo, definir `language=en` por `PUT /profile/{user_id}/preferences/language`, com `{"value":"en","scope":"user"}`. Enviar a `/run` a pergunta `Explique em uma frase o que é uma lista de tarefas.`, com `intent=conversa`, `user_id` e uma sessão nova. A resposta saiu em português apesar de `preferences_used.language=en`. Reproduzir primeiro em dados isolados; não usar nem alterar as preferências de leo.

- Evidência instalada: `C:/CAIN/work/qa-llm-fix-20260913/primary-extra.json`.
- Tentativas descartadas: `language-final.json`, `language-v2.json`, `language-v3.json` e scripts correspondentes no mesmo diretório. Reforçar a instrução interna, trocar o idioma padrão da projeção ou prefixar o pedido não resolveu nos testes. Essas alterações não fazem parte da entrega.
- Código para investigar: `src/cain/agents/__init__.py` (ConversationAgent), `src/cain/identity/__init__.py` (perfil efetivo/contexto), `src/cain/llm/__init__.py` (Ollama), `src/cain/orchestrator/__init__.py` (metadados e registro).
- Outras limitações: orientação adicional sem base no trecho ao perguntar pela amostra ausente; latência alta em CPU/8 GB. Não houve treino de pesos ou certificação geral da LLM.
- Testes já feitos: `expanded-results.json`, `format-final.json`, `primary-ui.json`, `primary-cli.log`. Os recibos completos ficam fora do Git e permanecem em C:/CAIN/work; apagar o chat não os remove.

Prompt para uma nova tarefa:

```text
Leia C:/CAIN/projeto/CONTINUIDADE.md, ESTADO_DO_PROJETO.md e docs/LOCAL_INSTALLATION.md.
Confira main e a instalação 0.4.10. Retome a pendência de language=en descrita na continuidade.
Preserve dados e configurações; teste com usuários/bancos isolados e inferência real.
Não conte respostas automáticas como qualidade da LLM. Registre aprovações, falhas e limites.
Se corrigir código, atualize a instalação, reteste, atualize os Markdown e faça commit/push na main.
```
