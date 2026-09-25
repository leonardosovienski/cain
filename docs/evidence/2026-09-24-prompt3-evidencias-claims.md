# CAIN — Prompt 3: evidências e claims verificáveis (2026-09-24)

Branch `melhorias/p3-evidencias-claims`, empilhada sobre `melhorias/p2-memoria-bitemporal` (PR #45). Tudo local;
nenhum segredo. Os dois verificadores rodaram de verdade neste PC (CPU, i7-12700F, 16 GB, WSL2). Os pesos são de
snapshots fixados do Hugging Face, e o sha256 de cada um confere com o LFS do Hugging Face.

## O que foi feito

Evidências e claims são eventos do mesmo log com cadeia sha256 do Prompt 2 (`evidence.recorded`, `claim.recorded`,
`claim.assessed`). Toda leitura exige `as_of`. O pacote novo é `cain.claims`, com o comando `cain claims`.

| Item do prompt | Implementação | Arquivo |
|---|---|---|
| 1. Evidence(id, doc_hash, chunk_id, quote, char_start, char_end, page, published_at, query, summary, relevance_score, model_id, settings_hash) | Todos os campos. `doc_hash` é o `content_sha256` do documento guardado, e `published_at` vem do documento. Há também `cube` e `document_id`. | `src/cain/memory/store.py` (`record_evidence`) |
| 2. Citação literal, sem LLM | `doc[char_start:char_end] == quote`, uma comparação de string exata. Offsets fora do texto, quote normalizado (espaços, caixa, pontuação) ou inventado → `QUOTE_NOT_LITERAL`. | `store.py` |
| 3. Claim(id, text, source_span, status, evidence_ids, verifier_scores, kind) | Os cinco status (UNVERIFIABLE, AMBIGUOUS, SUPPORTED, CONTRADICTED, INCONCLUSIVE). Um claim novo só nasce UNVERIFIABLE, AMBIGUOUS ou INCONCLUSIVE; SUPPORTED e CONTRADICTED só vêm de uma avaliação registrada. O status de leitura é a última avaliação até `as_of`. `review_state` separa `pending_verification`, `needs_human_review` e `reviewed`. | `store.py` |
| 3. TEXTUAL_SUPPORT × EMPIRICAL_PROOF, nunca confundidos | Um EMPIRICAL_PROOF exige `run_ref {run_id, report_path, report_sha256}`, e um TEXTUAL_SUPPORT não pode ter `run_ref`. Os verificadores de texto recusam EMPIRICAL_PROOF. `assess_empirical` só dá SUPPORTED se o artefato existe, o sha256 confere e os números do claim aparecem no artefato. | `store.py`, `src/cain/claims/verify.py` |
| 4. Extração com modelo local (Claimify-lite) | O modelo seleciona o conteúdo verificável e decompõe em claims autocontidos com `source_quote`. Só entram claims cujo quote existe literalmente no documento, com o span achado por busca exata. Ambíguo → AMBIGUOUS, não verificável → UNVERIFIABLE. Saída estruturada por JSON Schema; o extrator é registrado (modelo, versão `claimify-lite/1`). | `src/cain/claims/extract.py` |
| 5. Dois verificadores locais de licença aberta | HHEM-2.1-Open (`vectara/hallucination_evaluation_model`, **Apache-2.0**, rev `8e4a2e6`) e MiniCheck-Flan-T5-Large (`lytang/MiniCheck-Flan-T5-Large`, **MIT**, rev `96eafd0`). As licenças foram conferidas no model card da revisão fixada; o tokenizer do HHEM (`google/flan-t5-base`, rev `7bcac57`) é Apache-2.0. O Bespoke-MiniCheck-7B (CC BY-NC) não é usado. Documento longo: janelas de 1500 caracteres com sobreposição de 200, score = máximo. Regra `two-verifiers-agree/1`: os dois acima do limiar → SUPPORTED; os dois abaixo → INCONCLUSIVE; desacordo → INCONCLUSIVE + `needs_human_review`. Cada avaliação registra verifier_id, revisão dos pesos, score, limiar, melhor janela e o sha256 da política. | `src/cain/claims/verifiers.py`, `verify.py` |
| (limiares) | Os limiares ficam no arquivo versionado `claims/data/verifier-policy.json` (v1: 0,5 e 0,5; sha256 `9bdcde22…`), referenciado em toda avaliação. Mudá-los exige aprovação humana registrada e só vale para hipóteses novas. | `src/cain/claims/data/verifier-policy.json` |
| (HHEM sem `trust_remote_code`) | O código remoto do HHEM (`modeling_hhem_v2.py`) não é executado. O classificador foi reimplementado com `T5ForTokenClassification` sobre o flan-t5-base e os mesmos pesos, prompt e softmax, e carrega com `trust_remote_code` desligado. | `verifiers.py` |
| 6. Linter de relatório | Todo número numa frase precisa de um marcador `[ev:ID]`, `[claim:ID]` ou `[run:ID@sha256]` cujo texto resolvido contenha aquele número. Caso contrário: `NO_PROVENANCE` (sem marcador) ou `NOT_IN_CITED_SOURCE` (o marcador não contém o número). Qualquer violação → `blocked`, e `cain claims lint` sai com exit 1. | `src/cain/claims/lint.py` |
| 7. `claims --unsupported`, `trace <claim_id>` | `cain claims list --unsupported` e `cain claims trace` (claim → avaliações → evidências → documento e hash). | `src/cain/claims/cli.py`, `store.py` |

Também: `cain claims review` registra a revisão humana como evento imutável (`assessed_by = human:<nome>`, com nota
obrigatória) e é o único caminho para CONTRADICTED; `review-queue` lista a fila de revisão; `golden` mede os
verificadores. O extra opcional `verify` (torch CPU + transformers) entrou no `uv.lock`; o torch vem do índice CPU do
PyTorch, sem CUDA.

## Testes obrigatórios

`tests/integration/test_claims.py` usa verificadores falsos e determinísticos, então a CI não precisa dos pesos:

| Teste do prompt | Teste | Resultado |
|---|---|---|
| Quote inventado é rejeitado | `test_invented_or_normalized_quote_is_rejected` (inventado, normalizado, offsets fora) | passou |
| Número sem proveniência bloqueia o relatório | `test_number_without_provenance_blocks_the_report` (sem marcador, marcador que não contém o número, marcador desconhecido) | passou |
| Desacordo dos verificadores vai para revisão | `test_verifier_disagreement_goes_to_the_human_review_queue` | passou |
| Golden set congelado | `test_golden_set_is_frozen_and_measured_by_the_runner` (sha256 congelado no teste; 48 pares, 24 EN + 24 PT, 12/12 por rótulo e língua) | passou |

Extras: acordo decide, e documentos longos usam a melhor janela; TEXTUAL_SUPPORT e EMPIRICAL_PROOF nunca se misturam;
a extração só guarda spans literais e não chuta; `trace` responde de onde veio um número; os caminhos da CLI passam
por `cain.cli.main`.

Suíte completa (Python 3.13.15, venv do `uv.lock` com o extra `verify`): **1209 passed, 2 skipped, 0 failed**
(1211 casos no junit; `suite.log` regenerado na cabeça `b8133bf`). Cobertura total **87%** (piso do CI: 86%); `claims/`: verify 91%, lint 95%, extract 92%,
golden 95%, cli 83%, verifiers 42%; `memory/ingest` 94%. O carregamento dos pesos não roda na CI e está coberto pela execução real abaixo.
`ruff check src tests`: ok.

## Acurácia real no golden set (não é estimativa)

`cain claims golden`, com os dois verificadores reais em CPU (torch 2.14.0+cpu, transformers 5.17.0), levou 14,6 s
para 48 pares (22,4 s de relógio com o carregamento, RSS máximo 3,98 GB). Resultado bruto em
`2026-09-24-prompt3/golden-v1-result.json`.

| Verificador | Todos | Inglês | Português |
|---|---|---|---|
| HHEM-2.1-Open (limiar 0,5) | 41/48 = **85,4%** | 21/24 = 87,5% | 20/24 = 83,3% |
| MiniCheck-Flan-T5-Large (limiar 0,5) | 43/48 = **89,6%** | 23/24 = 95,8% | 20/24 = 83,3% |

| Regra combinada (`two-verifiers-agree/1`) | Todos | Inglês | Português |
|---|---|---|---|
| Decididos | 40 | 22 | 18 |
| Enviados para revisão humana | 8 | 2 | 6 |
| Acertos entre os decididos | 38/40 = **95,0%** | 21/22 = 95,5% | 17/18 = 94,4% |
| Falsos SUPPORTED | **0** | 0 | 0 |

Leitura honesta:

- **Os dois erros da regra combinada são do mesmo tipo.** `en-03` e `pt-03` perguntam se "o intervalo de −43 a 95
  inclui zero". É aritmética, e nenhum dos dois verificadores a faz: os scores ficaram entre 0,03 e 0,11. A regra
  devolve INCONCLUSIVE, um falso negativo no sentido seguro, nunca um falso SUPPORTED.
- **Português:** os dois verificadores são treinados em inglês. Individualmente caem para 83,3% em PT. A regra
  combinada mantém 94,4% entre os decididos, mas manda 6 de 24 pares PT para revisão, contra 2 de 24 em EN. Em
  português, o custo aparece como fila de revisão maior, não como erro silencioso.
- **Desacordos típicos:** o HHEM aceita claims com número trocado (en-16: 3.222 × 2.322, HHEM 0,57) ou com fato
  negado (en-20, HHEM 0,85), e o MiniCheck recusa. Por isso o desacordo vai para humano, e não para o verificador
  "mais forte".
- **Limites do conjunto:** 48 pares são poucos, e **os rótulos foram escritos pelo agente que montou o conjunto; a
  revisão humana está pendente**. Os números acima medem os verificadores contra esses rótulos, não contra um
  gabarito auditado.

## Evidência de runtime (console script `cain`, fora do pytest)

`2026-09-24-prompt3/runtime_demo.log` roda o caminho completo pela CLI, com os verificadores reais e a partir de um
banco vazio:

1. `memory add-document` de um relatório de backtest.
2. Três `claims add-evidence` com offsets literais. Uma quarta, com offsets que não batem com o quote, é recusada
   (exit 1, `QUOTE_NOT_LITERAL`).
3. Três claims e `claims verify`:
   - "The backtest spans 49 rebalance periods." → **SUPPORTED** (HHEM 0,967; MiniCheck 0,977).
   - "…averaged 92 basis points…" (o relatório diz 29) → **INCONCLUSIVE** (0,410; 0,023).
   - "The confidence interval … includes zero." → **INCONCLUSIVE** (0,058; 0,162): o mesmo ponto cego aritmético
     do golden set.
4. `claims review` do claim aritmético como SUPPORTED, com nota. `list --unsupported` e `trace` mostram o evento de
   revisão humana e a cadeia até o documento.
5. `claims lint`:
   - relatório com cada número citado → `publishable` (exit 0);
   - relatório com "29 … above the 25 we needed" sem marcador → `blocked`, dois `NO_PROVENANCE` (exit 1).
6. `memory verify` → `intact`.

**Achado da primeira execução da demo** (log bruto preservado fora do repositório, em
`runtime/cain-melhorias/raw/runtime_demo_p3_first_run.log`): o relatório "bom" citava o run como `bt-2026-07`, e o
linter bloqueou os números 2026 e 07, porque a evidência citada não os contém. O linter está certo pela regra: um
identificador com dígitos conta como número. Mantive o linter estrito (a opção conservadora) e registro a limitação:
num relatório, identificadores com dígitos precisam ser citados, por exemplo como `[run:ID@sha256]`, ou ficar fora
da frase com números. A demo final escreve o relatório sem o identificador.

### Extração com o modelo local (qwen3.5:4b no Ollama 127.0.0.1, GPU)

Correção feita depois da primeira versão deste relatório: o Ollama roda na **GPU** desta máquina (NVIDIA RTX 2060
6 GB, CUDA no WSL2), com todas as camadas do qwen3.5:4b na VRAM. Os verificadores (torch CPU) rodaram na CPU, como
descrito acima. A versão anterior deste trecho dizia CPU, e estava errada.

Segunda etapa da mesma demo: `cain claims extract` sobre o relatório, com `qwen3.5:4b`
(digest `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`), temperatura 0, seed 42, `think=false`,
saída estruturada por JSON Schema (`format` do Ollama).

- 5 claims propostos, **5 com citação literal, 0 rejeitados**, todos INCONCLUSIVE (`pending_verification`). A
  linha de título ("Backtest report, run bt-2026-07.") não virou claim.
- Geração: 349 tokens em 5,9 s com o modelo já carregado. Numa execução anterior, com a mesma entrada e o
  modelo frio, a chamada levou 57,9 s, dos quais 29,0 s de carga. O log dessa execução foi sobrescrito pela
  demo final; os números vêm da saída dela.
- Cada claim extraído foi verificado pelos dois verificadores reais contra as três evidências registradas.
  **Os 5 ficaram SUPPORTED** (scores de 0,935 a 0,971):

| Claim extraído pelo modelo | HHEM | MiniCheck | Status |
|---|---|---|---|
| The backtest covered 49 rebalance periods. | 0,953 | 0,961 | SUPPORTED |
| The backtest period was between July 2022 and August 2025. | 0,958 | 0,971 | SUPPORTED |
| Net excess return averaged 29 basis points per period. | 0,958 | 0,935 | SUPPORTED |
| The 95% confidence interval for net excess return was from -43 to 95 basis points. | 0,959 | 0,958 | SUPPORTED |
| The strategy did not beat the benchmark with statistical confidence. | 0,970 | 0,971 | SUPPORTED |

Observação: a verificação usa o quote da evidência **e** as janelas do documento de onde ela vem, com score
máximo. Por isso o último claim, que não está em nenhum dos três quotes, é sustentado pelo documento citado. É o
comportamento pedido ("chunk e máximo de suporte"), e o `best_window` registrado mostra de onde veio o suporte.

**Achado corrigido nesta branch (commit `81aa836`).** A primeira execução real da extração registrou
`model_digest: null`, porque o `OllamaLLM` não tem atributo de digest. O mesmo defeito existia em
`cain memory extract` (Prompt 2), que gravava `modelo@unknown-digest`. Os dois extratores agora pegam o digest no
inventário local do Ollama (`/api/tags`, a mesma função dos workflows), e um modelo não instalado falha fechado
(`MODEL_UNKNOWN`). O teste novo `test_extraction_with_a_local_ollama_model_records_the_installed_digest` falha sem a
correção (`assert None == '9'*64`) e passa com ela. A demo final registra o digest real.

Logs brutos:

| Arquivo | sha256 |
|---|---|
| `2026-09-24-prompt3/golden-v1-result.json` | `96aba3900e2e0dd570f23cbc31ac513c1837c0b4a20f1f9ee3c01b0913f6e73c` |
| `2026-09-24-prompt3/golden-run.log` | `5bb6d3ed99f6182168afd6973632809c08a586f3bc72bd96fae7971f05af6011` |
| `2026-09-24-prompt3/runtime_demo.log` | `825618efbd5b5abb8304e6b7047033f6b402c3401f13422af4453930015e925c` |
| `2026-09-24-prompt3/suite.log` | `53e85e89fc429faf10766047c16353a66be1e25f907d9ab0b5e09736bf040123` |

## Commits depois da primeira versão deste relatório

- `6d3c58b test(memory)`: os testes do Prompt 2 fecham as conexões sqlite que abriam (`with sqlite3.connect` só faz
  commit). Com `--cov`, a contagem de `ResourceWarning` volta à do `main`.
- `b8133bf fix(memory,claims)`: `--as-of now` nunca lê antes da cabeça do log. Uma suíte completa falhou uma vez em
  `test_cli_paths`: o `lint --as-of now` não viu a revisão gravada instantes antes. A causa é um relógio de parede
  que volta (sincronização de tempo do WSL2); a escrita já recusava isso (`CLOCK_WENT_BACKWARDS`), mas a leitura
  não. `MemoryStore.now()` = máximo entre o relógio e o `recorded_at` da cabeça, com o teste
  `test_read_now_never_precedes_the_log_head`. A falha não se reproduziu isolada (0/40), e a causa é inferida, não
  observada diretamente.
- `5506376 docs(evidence)`: a extração rodou na GPU, não na CPU (seção de extração).

## PROVEN × DECLARED

| Afirmação | Estado | Por quê |
|---|---|---|
| Citação literal por comparação exata; quote inventado rejeitado | **PROVEN** | teste + demo (exit 1 no quote errado) |
| Claims com cinco status; SUPPORTED/CONTRADICTED só por avaliação; CONTRADICTED só por humano | **PROVEN** | testes + demo |
| TEXTUAL_SUPPORT × EMPIRICAL_PROOF separados; prova empírica pelo artefato e sha256 | **PROVEN** | teste `test_textual_support_and_empirical_proof_are_never_mixed` |
| Dois verificadores reais, pesos fixados e conferidos, sem `trust_remote_code` | **PROVEN** | golden + demo neste PC; sha256 dos pesos = LFS do HF |
| Acurácia medida: HHEM 85,4%, MiniCheck 89,6%, combinada 95,0% entre decididos, 0 falso SUPPORTED | **PROVEN contra rótulos DECLARED** | medição real; rótulos ainda sem revisão humana |
| Desempenho em português | **PROVEN (medido), fraco** | 83,3% por verificador; o combinado manda 25% dos pares PT para revisão |
| Linter bloqueia número sem proveniência | **PROVEN** | teste + demo (exit 1) |
| `claims --unsupported` e `trace` | **PROVEN** | teste + demo |
| Extração de claims com modelo local (qwen3.5:4b): só spans literais, digest registrado | **PROVEN** neste PC | demo real: 5/5 literais, 0 rejeitados; teste do digest |
| Qualidade da extração em geral | **DECLARED** | um relatório curto não mede recall nem precisão; o harness do Prompt 5 mede extração com citação |
| Verificação de claims que exigem aritmética ou comparação numérica | **não resolvido** | os dois verificadores falham, e a regra manda para INCONCLUSIVE; a revisão humana é o caminho |

## O que ficou de fora e por quê

- Os limiares (0,5) não foram calibrados no golden set. Calibrar no mesmo conjunto que mede a acurácia seria
  sobreajuste, e mudar limiar exige aprovação humana registrada. Ficam como estão, e o resultado mostra onde erram.
- A verificação numérica (o claim contém um número que a evidência contradiz) poderia ter um checador determinístico
  próprio, como o do linter. Não entrou: é uma decisão de regra (muda o que vira CONTRADICTED) e fica para o dono.
- Os rótulos do golden set precisam de revisão humana antes de os números acima virarem referência.

## Adendo da revisão final (2026-09-25)

Detalhes em `2026-09-25-revisao.md`.

- A frase "mudá-los exige aprovação humana registrada e só vale para hipóteses novas" descrevia uma regra que o código **não aplicava**: com limiar diferente, a decisão saía como `"custom"`.
- Agora a decisão usa a versão da política em vigor no registro do claim (`cain.policy`), e os verificadores da política com outro limiar são recusados (`POLICY_MISMATCH`).
- Uma mudança é um arquivo `verifier-policy-v<N>.json` novo, mergeado pelo dono.
