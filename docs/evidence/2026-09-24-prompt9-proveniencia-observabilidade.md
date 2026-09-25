# CAIN — Prompt 9: proveniência tipada e observabilidade (2026-09-24)

Branch `melhorias/p9-proveniencia-observabilidade`, cumulativa sobre o Prompt 8. Tudo local; nenhum segredo.

- **Modelo:** qwen3.5:4b no Ollama (GPU RTX 2060).
- **MLflow:** 3.16.1 local, com backend SQLite, instalado no seu próprio venv (`tools/mlflow-venv`), fora das
  dependências do CAIN.

## O que foi feito

| Item do prompt | Implementação | Arquivo |
|---|---|---|
| 1. Relações tipadas entre objetos, como eventos | SUPPORTS, CONTRADICTS, DERIVED_FROM, INVALIDATES, USED, TRIGGERED, UPDATED. **Derivadas** do que a memória já guarda (lidas `as_of`): evidência DERIVED_FROM documento; evidência SUPPORTS o claim que a cita; claim DERIVED_FROM documento (e o run, se EMPIRICAL_PROOF); avaliação UPDATED/USED claim e USED evidências; achado DERIVED_FROM fonte e USED relatório/transição; item de revisão SUPPORTED pela referência que o responde. **Explícitas**: `relate`, gravadas como eventos no cubo `provenance`. Nenhuma relação é UPDATE. | `src/cain/provenance/graph.py` |
| 2. `trace`, `why`, `impact` (+ `claims --unsupported`) | `cain trace` (ancestralidade completa), `cain why` (evidências, claims, documentos e runs de uma decisão), `cain impact` (o que cai junto) e `cain relate`. `cain claims list --unsupported` já existia (Prompt 3). Cada relação tem uma direção de dependência fixa. | `src/cain/provenance/cli.py` |
| 3. Invalidação em cascata sinaliza, não apaga | `cain invalidate`: grava `INVALIDATES`; para cada dependente, claims recebem uma avaliação INCONCLUSIVE / `needs_human_review` (evento), e o resto recebe um evento `prov:FLAGGED`. Nada é apagado, e a leitura `as_of` anterior continua mostrando o estado de antes. | `graph.py` |
| 4. OpenTelemetry com `gen_ai.*`, exportado para MLflow local (SQLite); nomes isolados | Span por chamada de modelo (no gravador de inferência: operação, provedor, modelo, temperatura, seed, max_tokens, motivo de término, tokens, id da chamada, cache, sha256 do GGUF). Span por tentativa do loop, e span `execute_tool` por estágio do avaliador, filho da tentativa. **Todos os nomes de atributo ficam em `semconv.py`** (convenção ainda "Development"). Extra opcional `observability` (opentelemetry-sdk + exportador OTLP/HTTP); sem configuração nada acontece. `CAIN_OTEL_ENDPOINT` aponta para o `/v1/traces` do MLflow (≥ 3.6, backend SQL), com `x-mlflow-experiment-id` no header. | `src/cain/observability/{semconv,tracing}.py` |
| 5. Avaliação contínua: amostra mensal rotulada à mão e fidelidade com IC | Amostra mensal determinística (sha256 de mês e claim), auditável. Duas estimativas: clássica (só a amostra humana, Wilson 95%) e **prediction-powered** (PPI, Angelopoulos et al. 2023): rótulos automáticos dos verificadores em todos os claims, corrigidos pela diferença humano − automático na amostra, com IC normal. `cain claims faithfulness-sample` e `cain claims faithfulness`. | `src/cain/claims/faithfulness.py` |

## Testes obrigatórios

`tests/integration/test_provenance.py` (6 testes):

| Teste do prompt | Teste | Resultado |
|---|---|---|
| Invalidar uma evidência sinaliza os dependentes | `test_invalidating_an_evidence_flags_every_dependent_and_deletes_nothing`: claims → `needs_human_review`; avaliações e a decisão registrada → FLAGGED; o claim que não depende fica intocado; o estado anterior continua legível `as_of`; `memory verify` intacto | passou |
| `why` devolve a cadeia completa | `test_why_returns_the_complete_chain_of_a_decision` (revisão humana → claim → 2 evidências → documento; decisão explícita → claim → evidência) + caso real abaixo | passou |
| O trace aparece no MLflow | `test_model_and_tool_calls_become_gen_ai_spans` (atributos `gen_ai.*`, spans de ferramenta filhos da tentativa) + **MLflow real** abaixo | passou |

Extras: duração do span sobrevive a um recuo do relógio de parede; a PPI cobre o valor verdadeiro com proxy bom e
com proxy ruim (e estreita o intervalo só quando o proxy é bom); CLI completa.

Suíte completa: **1265 passed, 2 skipped, 0 failed** (1267 casos no junit). Cobertura total **87%**; `provenance/`:
cli 100%, graph 83%; `observability/`: semconv 100%, tracing 81%; `claims/faithfulness` 88%. `ruff`: ok.

## Evidência de runtime

### Proveniência num caso real (`provenance_demo.log`, `provenance-summary.json`)

Uma **cópia** da memória da demo do Prompt 3: relatório de backtest real, 3 evidências literais, 8 claims (5
extraídos pelo qwen3.5:4b), avaliações dos dois verificadores reais e uma revisão humana de demonstração.

- `cain why <revisão humana>` → claim "o IC inclui zero" → evidência do IC → documento (8 arestas).
- `cain impact <evidência "49 períodos">` → **12 dependentes**: 6 claims (o manual e os 5 extraídos, que foram
  verificados contra as três evidências) e 6 avaliações.
- `cain relate decision:p3-backtest-report-published USED <claim>`, e `why` dessa decisão → claim → evidência →
  documento.
- `cain invalidate <evidência "49 períodos">` → **6 claims** passam a `needs_human_review`; **6 avaliações e a
  decisão** recebem `prov:FLAGGED`. `claims list --unsupported` mostra os 6. O `trace` da decisão agora inclui a
  invalidação. `memory verify`: `intact`.

### Traces no MLflow local (`mlflow-traces.json`)

`mlflow server` com backend `sqlite:///…/mlflow.db` e experimento `cain-p9-otel`. O CAIN exporta por OTLP/HTTP
para `/v1/traces`:

- `cain inference repeat --n 2` com o qwen3.5:4b: 2 chamadas, 1 saída distinta;
- `cain loop run` do world do Brasileirão (proponente `neighbor`): 6 tentativas, parada por estagnação.

O MLflow devolveu (`mlflow.search_traces`) **8 traces e 20 spans**:

- 2 `text_completion qwen3.5:4b`, com os atributos `gen_ai.*` e `cain.*`;
- 6 `loop attempt`;
- 12 `execute_tool evaluator.{sanity,in_sample,walk_forward}`, **todos filhos da tentativa**;
- **0 durações negativas**.

**Achado corrigido (commit `036ee30`).** Na primeira execução, um span de avaliador apareceu no MLflow com duração
**negativa** (−397,6 ms): o relógio de parede do WSL2 voltou dentro do span. Agora a duração vem do relógio
monotônico, com teste (`test_span_duration_survives_a_wall_clock_step_back`). O traço da primeira execução está
preservado fora do repositório.

### Fidelidade com IC no golden set (`faithfulness-golden.json`), DECLARED

- **Rótulo automático:** a regra combinada dos dois verificadores reais (Prompt 3); SUPPORTED = 1.
- **Rótulo "humano":** o do golden set, **escrito pelo agente** (revisão humana pendente), usado como amostra mensal
  de 16 dos 48 pares.

| | Estimativa | IC 95% |
|---|---|---|
| Valor com os 48 rótulos | 0,500 | — |
| Proxy sozinho (verificadores) | 0,375 | viés conservador |
| Clássica (16 da amostra) | 0,313 | [0,142; 0,556] |
| PPI (32 automáticos + 16 da amostra) | 0,594 | [0,351; 0,836] |

As duas estimativas cobrem o valor com os 48 rótulos. A PPI corrige o viés do proxy, mas **não estreitou** o
intervalo aqui: 48 pares e concordância de 87,5% são pouco. Ela estreita quando o proxy é bom e a população sem
rótulo é grande, como mostra o teste. É uma demonstração do estimador, não uma medida de fidelidade.

| Arquivo | sha256 |
|---|---|
| `2026-09-24-prompt9/provenance_demo.log` | `83f483c169fef89c1fa25d54c375d849f316968cea56970e91aceebbe73c72dd` |
| `2026-09-24-prompt9/provenance-summary.json` | `4729e4df07666da8567fbd4acf9c35539650abf73ffbae65ac61c627c780dd3a` |
| `2026-09-24-prompt9/mlflow-traces.json` | `b26c89a75a81e10262061657e613ea6ff2fb573a28c38ebfeabad37a4f3303b1` |
| `2026-09-24-prompt9/faithfulness-golden.json` | `9dd90e0e0961a5545ad4db9f67d7d816553aa2056b96edf220bbfdb78573b4a8` |
| `2026-09-24-prompt9/suite.log` | `81c66750000de5d2d5a537fd4726201a15406253c5afaef85d716ad66a0ad536` |

## PROVEN × DECLARED

| Afirmação | Estado | Por quê |
|---|---|---|
| Relações tipadas como eventos; `trace`, `why`, `impact` | **PROVEN** | testes + caso real |
| Invalidação em cascata sinaliza sem apagar | **PROVEN** | teste + caso real (6 claims, 6 avaliações, 1 decisão) |
| Spans `gen_ai.*` de modelo e ferramenta no MLflow local (SQLite) | **PROVEN** | 8 traces e 20 spans consultados de volta no MLflow |
| Nomes de atributo isolados | **PROVEN** | um módulo, `semconv.py` |
| Estimador de fidelidade com IC (clássico e PPI) | **PROVEN** (estimador) | teste com verdade conhecida |
| Fidelidade real do pipeline | **DECLARED** | falta a amostra mensal rotulada por um humano |
| Proveniência de workflows (P4) e do ledger do loop dentro do mesmo grafo | **parcial** | achados de loop entram; eventos de aprovação dos workflows ainda não viram arestas |

## O que fica para o dono

- Rotular à mão a amostra mensal (`cain claims faithfulness-sample --month 2026-09 --n 30`) para a primeira medida
  real de fidelidade.
- Ligar `CAIN_OTEL_ENDPOINT` no ambiente em que o CAIN roda, se quiser traces contínuos no MLflow.

## Adendo da revisão final (2026-09-25)

Detalhes em `2026-09-25-revisao.md`.

- A linha "parcial" foi resolvida: o grafo lê o ledger do loop (tentativas, chamadas do proponente, estágios do avaliador com o mesmo id dos spans, gates, holdout) e os eventos dos workflows (aprovações, forks).
- `cain trace | why | impact | invalidate --loop-db --workflow-db`. O `why` agora lista decisões, chamadas de modelo e de ferramenta.
- A correção de CI deste PR (extra `observability`) usava `importorskip`, que mascara a falta do extra. Ele saiu e o README instala o mesmo que o CI.
