# CAIN — conversa, memória e pesquisa local

CAIN 0.4.8 é um assistente local com projetos, preferências, documentos, consulta de evidências e workflows retomáveis.
A branch de trabalho e publicação é **main**. As correções de Historian e os contratos Snapshot/Bundle estão integrados e instalados.
Consulte o [estado verificado](ESTADO_DO_PROJETO.md), a [continuidade](CONTINUIDADE.md) e o [índice documental](docs/README.md).

## Abrir nesta máquina

Execute `C:\CAIN\ABRIR_CAIN.cmd` ou abra http://127.0.0.1:8877/.
O projeto atual fica em `C:\CAIN\projeto`; a instalação não editável fica em `C:\CAIN\.venv`.
Os atalhos na raiz `C:\CAIN` usam os bancos existentes. Previews antigos, incluindo a porta 8884, não são a instalação principal.

```powershell
C:\CAIN\CAIN.cmd run "oi" --user leo
C:\CAIN\CAIN_RESEARCH.cmd query --source-id H4
```

Na interface de Pesquisa, selecione H4 no acervo crypto e consulte:
“Explique a decisão documentada de H4, incluindo estado, trial, motivo e tamanho da amostra.”
No relatório congelado validado, estado e trial têm fonte; motivo e amostra são explicitamente não localizados no recorte.
Isso não afirma inexistência na fonte completa nem estado atual do produtor.

## Capacidades e limites

- Conversas, projetos, documentos, histórico, feedback e preferências por usuário, projeto, conversa ou resposta.
- Conversa cotidiana com o modelo local (`--intent conversa` na CLI; `conversa` ou `chat` na API). Cálculos simples como “Quanto é 2 + 2?” usam aritmética limitada e exata, sem geração; frações são exibidas sem arredondamento.
- Busca lexical/híbrida, citações, inspeção de fontes e recebimento de Snapshot e Bundle com autorização por operação.
- Historian: campos literais completos para listas explícitas; citações estruturadas limitadas aos trechos disponíveis quando o conjunto cabe no orçamento.
- Workflows com checkpoints, cancelamento e retomada; API, CLI, web e MCP locais.
- Texto e visão com modelos locais quando configurados; resultados de modelo continuam sujeitos a falhas e validação.

A precedência das preferências é resposta → conversa → projeto → usuário. Feedback não altera fatos automaticamente.
Extração literal não é interpretação causal. Perguntas abertas, comparação semântica e resumos livres não têm confiabilidade geral certificada.
Testes técnicos não validam lucro, apostas, conclusões científicas ou utilidade humana independente.

## Instalar um checkout separado

Python 3.11+ é necessário. Os contratos estão em `vendor`; dependências opcionais e pesos de modelos são separados.
Não execute uma instalação de desenvolvimento sobre o ambiente principal apenas para ler a documentação.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --find-links vendor -e ".[api]"
.\ABRIR_CAIN.cmd
```

O inicializador do checkout usa a porta 8000 por padrão; o atalho da instalação principal usa 8877.
Para terminal, use `INICIAR_CAIN.cmd`. A configuração vem de `cain.toml` e dos overrides locais.
O modelo configurado é `qwen3.5:0.8b`; embeddings usam `qwen3-embedding:0.6b` com digest verificado.
Pesos não acompanham o pacote. Inferência requer Ollama disponível; ajuda e consulta determinística não requerem modelo.

## Desenvolvimento e API

Em um ambiente de desenvolvimento separado:

```powershell
python -m pip install --find-links vendor -e ".[dev,vision]"
python -m ruff check .
python -m pytest -q
python -m cain --help
```

A [CI](.github/workflows/ci.yml) verifica Python 3.11–3.14, lint, testes, build e instalação não editável fora do checkout.
`/openapi.json` descreve a API. `/run` exige `user_id`, `session_id` e `payload`.
Em `/research/explain`, `session_id` é opcional; quando informado, deve identificar uma conversa existente no projeto.
O perfil por nome é local, não autenticação. O serviço usa loopback e controles Host/Origin.

Leia [operação local](docs/LOCAL_INSTALLATION.md) para pastas e recuperação, [Pesquisa L0](docs/RESEARCH_L0.md) para contratos
e [histórico documental](docs/historico/README.md) para estados anteriores. Relatórios datados conservam seu escopo original.
