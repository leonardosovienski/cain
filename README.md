# CAIN — acervo Stocks e leitura verificável

Nova rodada em QA: [campanha de conversa H1–H22](docs/STOCKS_CONVERSATION_CAMPAIGN_20260916.md).
Correções de contexto e inferência real são avaliadas separadamente das reproduções históricas.

Rodada atual: [campanha Stocks no CAIN](docs/STOCKS_CAMPAIGN_20260916.md).
Projeto local com 112 documentos, 22 jobs e reproduções históricas H21/H22 conferidas.
Validação econômica geral e interpretação autônoma continuam limitadas.

Consulte a [prontidão Stocks](docs/STOCKS_STUDY_READINESS_20260915.md) para código,
acervo, instalação, testes e limites de interpretação. As correções anteriores
estão integradas pelas [PR #4](https://github.com/leonardosovienski/cain/pull/4) e
[PR #5](https://github.com/leonardosovienski/cain/pull/5).
O piloto real encerrou com três respostas e nenhuma aprovação semântica geral;
os motivos estão no relatório de prontidão.

O acervo principal recebeu 48 fontes e contém 88 registros Stocks: 87 admitidos
nesta rodada e o registro anterior preservado. A leitura literal de H1, das
duas revisões da H17 e dos critérios da H22 passou em QA e na instalação principal. Isso não certifica
interpretação livre do modelo nem executa um experimento científico.

Evidências e cópias de recuperação: `C:/CAIN/work/stocks-study-20260915`.
Nada foi apagado. Consulte os recibos de ativação para o caminho exato do runtime.

<details>
<summary>Histórico preservado — não representa o estado corrente</summary>

# CAIN — integração V8 e correções de pesquisa

Esta revisão concilia a main consolidada em `2bdb570` com as correções Stocks de
`f6c86d3`, pela [PR #3](https://github.com/leonardosovienski/cain/pull/3).
Preserva conversa e memória V8, tabelas literais, cobertura por identidade e
observações nativas; acrescenta listas JSON literais e abstenção para campos técnicos.

Consulte o [relatório da integração](docs/INTEGRACAO_STOCKS_MAIN_20260915.md), o
[estado atual](ESTADO_DO_PROJETO.md) e o [índice documental](docs/README.md).
A instalação principal permanece separada. Testes de software não certificam
interpretação geral do modelo nem conclusões científicas.



> Estado final desta cópia: V8 em QA isolado no workspace; 831 testes offline, sem confirmação com modelo e sem aprovação geral. Checkout canônico continua V7; instalação principal preservada. Veja [continuação V8](docs/CONTINUACAO_V8_20260915.md). O conteúdo anterior abaixo conserva o histórico.

# CAIN — conversa, memória e pesquisa local

CAIN 0.4.13rc4 é um assistente local com projetos, preferências, documentos, consulta de evidências e workflows retomáveis.
A referência de publicação é **main**. Este checkout está em `fix/readiness-main-20260914`: a V4 foi preservada no checkpoint local `ad21220`, seguido pelas alterações desta continuação. A candidata V6 está somente em QA não editável; não foi publicada nem instalada como principal. Veja a [continuação e seus limites](docs/CONTINUACAO_POS_V4_20260915.md).
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

Python 3.11+ e [uv](https://docs.astral.sh/uv/) são necessários. As dependências vêm do `uv.lock`
(pacotes de contrato publicados como releases do `ecosystem-predictor`, travados por hash); pesos de modelos são separados.
Não execute uma instalação de desenvolvimento sobre o ambiente principal apenas para ler a documentação.

```powershell
uv sync --locked --extra api
.\ABRIR_CAIN.cmd
```

`uv sync` cria `.venv` no checkout; o inicializador usa esse ambiente e só instala quando ele não existe.

O inicializador do checkout usa a porta 8000 por padrão; o atalho da instalação principal usa 8877.
Para terminal, use `INICIAR_CAIN.cmd`. A configuração vem de `cain.toml` e dos overrides locais.
O modelo configurado é `qwen3.5:4b`; embeddings usam `qwen3-embedding:0.6b` com digest verificado.
Pesos não acompanham o pacote. Inferência requer Ollama disponível; ajuda e consulta determinística não requerem modelo.

## Desenvolvimento e API

Em um ambiente de desenvolvimento separado:

```powershell
uv lock --check
uv sync --locked --extra dev --extra vision
uv run ruff check .
uv run pytest -q
uv run python -m cain --help
```

A [CI](.github/workflows/ci.yml) verifica Python 3.11–3.14, lint, testes, build e instalação não editável fora do checkout.
Um job fixo (Linux, Python 3.12) mede a cobertura com `uv run pytest -q --cov=cain` e falha abaixo do piso
(`--cov-fail-under`, hoje 84%, a baseline reproduzida). Para elevar o piso, meça na `main`, arredonde para baixo
e altere o valor no mesmo PR que subiu a cobertura; nunca reduza sem justificativa escrita.
`/openapi.json` descreve a API. `/run` exige `user_id`, `session_id` e `payload`.
Em `/research/explain`, `session_id` é opcional; quando informado, deve identificar uma conversa existente no projeto.
O perfil por nome é local, não autenticação. O serviço usa loopback e controles Host/Origin.

Leia [operação local](docs/LOCAL_INSTALLATION.md) para pastas e recuperação, [Pesquisa L0](docs/RESEARCH_L0.md) para contratos
e [histórico documental](docs/historico/README.md) para estados anteriores. Relatórios datados conservam seu escopo original.

A rodada da LLM está em [correções e limites observados](docs/LLM_CORRECOES_20260912.md). O 4B prioriza fidelidade e é lento em CPU com 8 GB de RAM.

Correções de idioma, roteamento de exercícios fictícios e preservação de contexto: [testes reais da 0.4.11](docs/LLM_REAL_20260913.md).
Cobertura de Crypto, Stocks e Brasileirão: [auditoria das conexões](docs/COBERTURA_PROJETOS_20260913.md). O CAIN recebe recortes publicados, não os projetos inteiros. Use **Cobertura do acervo** na interface ou `research ... coverage` para conferir Snapshot, Bundle e permissões separadamente.
Histórico de conversa e formato: [testes da 0.4.10](docs/LLM_FIX_20260913.md).

</details>
