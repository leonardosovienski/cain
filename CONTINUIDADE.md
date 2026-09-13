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
