# CAIN — Prompt 5: inferência local reproduzível e escolha de modelo por medição (2026-09-24)

Branch `melhorias/p5-inferencia-reproduzivel`, cumulativa sobre os Prompts 3 e 4. Tudo local; nenhum segredo.

Ambiente medido (`2026-09-24-prompt5/environment.txt`):

- Ollama 0.34.4 em 127.0.0.1 no WSL2, com `OLLAMA_NUM_PARALLEL=1` e `OLLAMA_MAX_LOADED_MODELS=1`;
- **GPU NVIDIA RTX 2060 6 GB** (CUDA), com todas as camadas de cada modelo na VRAM;
- CPU i7-12700F, 16 GB de RAM.

Todo número abaixo vale para esta máquina, este build e estes parâmetros.

## O que foi feito

Pacote novo `cain.inference` e o comando `cain inference`. O gravador fica no transporte HTTP dos provedores locais,
então vê os bytes exatos do pedido e da resposta.

| Item do prompt | Implementação | Arquivo |
|---|---|---|
| 1. Manifesto por chamada: **modelo** | sha256 do blob GGUF (linha `FROM` do Modelfile), digest do Ollama, tamanho, formato, família, nº de parâmetros, quantização, sha256 do template de chat, do Modelfile e da licença, e parâmetros padrão do modelo. O tokenizer vai embutido no GGUF, então o sha256 do GGUF o cobre. No llama.cpp: sha256 do arquivo carregado (com cache por tamanho e mtime) e do template. | `src/cain/inference/recorder.py` |
| 1. **runtime** | Nome e versão (Ollama `/api/version`; llama.cpp `build_info`); backend real da chamada (`/api/ps`: `gpu` quando `size_vram > 0`), tamanho carregado e VRAM; SO, CPU, nº de CPUs, RAM, Python. | `recorder.py` |
| 1. **parâmetros** | Tudo o que foi pedido (seed, temperature, num_ctx, num_predict, num_batch…) e os padrões do modelo, mais stream, think, keep_alive e cache_prompt. A ordem dos samplers e o número de threads e de slots não são expostos pela API do Ollama; ficam registrados como "padrão do runtime", e `OLLAMA_NUM_PARALLEL=1` vem declarado pelo `serve.sh`. | `recorder.py` |
| 1. **entrada e saída** | sha256 do corpo exato do pedido, do prompt, do system, das mensagens e do schema; sha256 da resposta bruta e do texto gerado; tokens de entrada e saída; `done_reason`; durações. Retentativas: cada tentativa é uma chamada com manifesto próprio, ligada por `attempt_group`. | `recorder.py`, `structured.py` |
| 1. **contexto** | Versão do CAIN, commit do git e se a árvore está suja, sha256 do `uv.lock`, e o que o chamador anexar com `inference_context(...)` (hashes de evidência, versões de ferramenta). | `recorder.py` |
| 2. Modo "run de registro" | `record`: uma requisição por vez (lock de processo + lock de arquivo), exige temperatura 0 ou seed explícita e grava a resposta como a resposta em cache daquela chave. O servidor também roda com `OLLAMA_NUM_PARALLEL=1`. | `recorder.py`, `tools/ollama/serve.sh` |
| 3. Cache por chave sha256 e replay | Chave = sha256(JCS de {sha256 do GGUF, build do runtime, endpoint, sha256 do corpo do pedido}). O corpo já contém os parâmetros canônicos, o prompt, o system e o schema/gramática. `replay` devolve os bytes gravados e **nunca chama o modelo**; sem gravação, falha fechado (`ReplayMiss`). Com o runtime fora do ar, o replay serve a gravação dos mesmos bytes de pedido, marca `runtime_verified=false` e copia a identidade da chamada que gravou a resposta (`identity_from_call`). Tabelas append-only (triggers contra UPDATE e DELETE). | `recorder.py` |
| 4. Saída estruturada pelo runtime | O schema vai no `format` do Ollama ou no `json_schema` do llama.cpp (decodificação por gramática). O CAIN ainda valida o objeto contra o schema, falhando fechado em palavra-chave desconhecida. Cada tentativa inválida fica gravada (`inference_validations`, com o erro), e cada retentativa usa `seed + tentativa`. | `src/cain/inference/structured.py` |
| 5. Harness de modelos locais | 96 tarefas congeladas (`inference/data/harness-v1.json`, sha256 `765ae314…`): 48 de classificação de evidência (o golden set do Prompt 3), 24 de extração de fato com citação literal e 24 de verificabilidade, metade EN e metade PT. Mede acurácia por família e língua, validade da saída estruturada, latência e memória. **Os gabaritos foram escritos pelo agente; a revisão humana está pendente.** | `src/cain/inference/harness.py` |
| 6. Documentar honestamente | Docstring do módulo e este relatório: reprodutível = mesmo hardware + mesmo build + mesmos parâmetros; não há promessa bit a bit entre máquinas. O que torna um run passado repetível é o replay da saída gravada. | `recorder.py` |

Configuração: seção `[inference]` (`mode = disabled | manifest | record | cache | replay`, `store`) ou
`CAIN_INFERENCE_MODE` / `CAIN_INFERENCE_DB`. O padrão é `manifest`, então toda chamada do `configured_llm` ganha
manifesto. O store só é criado na primeira chamada; nada é escrito antes disso.

**Inspect AI não foi usado.** O harness tem cerca de 200 linhas e reaproveita o gravador (manifesto, record e replay).
O Inspect traria outro framework, com log e cache próprios, duplicando o que o manifesto já guarda.

## Testes obrigatórios

`tests/integration/test_inference_recorder.py` (15 testes) roda contra um servidor HTTP local que imita a API do Ollama:

| Teste do prompt | Teste | Resultado |
|---|---|---|
| Mesma chamada 20× em modo registro; quantas saídas distintas | `test_twenty_identical_calls_counted_and_replay_is_identical`: 1 texto distinto em 20, e 20 respostas brutas distintas (as durações mudam). `test_the_counter_sees_nondeterminism` mostra que o contador acusa 5 saídas distintas quando o servidor varia. | passou |
| Replay via cache idêntico | o mesmo teste: o replay devolve o texto gravado sem chamar o servidor. Também `test_offline_replay_…` (servidor desligado) e `test_replay_miss_fails_closed_and_model_change_misses` (outro GGUF sob a mesma tag → miss) | passou |
| Manifesto completo em toda chamada | `test_every_call_gets_a_complete_manifest` + `cain inference audit`, que confere os campos obrigatórios de todo manifesto gravado | passou |

Extras: modo registro serializa 6 chamadas concorrentes (máximo 1 ativa no servidor); modo registro recusa
amostragem sem seed; store append-only; saída estruturada guarda a tentativa inválida; seção `[inference]` e
`configured_llm`; o harness congelado pontua citação literal; o caminho completo pela CLI.

Suíte completa (Python 3.13.15): **1232 passed, 2 skipped, 0 failed** (1234 casos no junit). Cobertura total
**87%**; `inference/`: cli 96%, harness 90%, recorder 88%, structured 78%. `ruff check src tests`: ok.

## Evidência de runtime com modelos reais

`runtime/cain-p5/run_all_p5.sh` roda, a partir de um estado limpo: determinismo, harness, replay offline e auditoria.

### Mesma chamada 20 vezes em modo registro (temperatura 0, seed 42)

| Modelo (licença) | Chamadas | Saídas distintas (texto) | Replay online | Replay com o Ollama inacessível |
|---|---|---|---|---|
| qwen3.5:4b (Apache-2.0), 4.7B Q4_K_M | 20 | **1** | idêntico à 1ª gravação | idêntico, `runtime_verified=false` |
| granite4:micro (Apache-2.0), 3.4B Q4_K_M | 20 | **1** | idêntico | idêntico, `runtime_verified=false` |
| phi4-mini (MIT), 3.8B Q4_K_M | 20 | **1** | idêntico | idêntico, `runtime_verified=false` |

Isso mede determinismo **em série** (`NUM_PARALLEL=1`, uma requisição por vez). Não mede invariância a batch: com
vários slots ou requisições concorrentes o resultado pode mudar, e isso não foi testado aqui.

### Harness (96 tarefas por modelo, modo registro)

| Modelo | Evidência (48) | Extração com citação (24) | Verificabilidade (24) | Total | EN / PT | Latência p50 / p95 por tarefa | Memória do modelo |
|---|---|---|---|---|---|---|---|
| qwen3.5:4b | 48/48 (100%) | 21/24 (87,5%) | 24/24 (100%) | **93/96 (96,9%)** | 47/48 / 46/48 | 0,32 s / 0,66 s | 3,27 GB, tudo na VRAM |
| granite4:micro | 47/48 (97,9%) | 22/24 (91,7%) | 24/24 (100%) | **93/96 (96,9%)** | 47/48 / 46/48 | 0,17 s / 0,49 s | 2,92 GB, tudo na VRAM |
| phi4-mini | 47/48 (97,9%) | 21/24 (87,5%) | 24/24 (100%) | **92/96 (95,8%)** | 46/48 / 46/48 | 0,17 s / 0,50 s | 3,63 GB, tudo na VRAM |

- **Saída estruturada:** válida na primeira tentativa em 288 de 288 chamadas; nenhuma retentativa.
- **RAM do host:** os processos do Ollama ficaram em ≈35 MB de RSS, porque o modelo está na GPU. A "memória do
  modelo" é o `/api/ps` do Ollama.
- **Replay offline:** reproduziu **96/96 linhas idênticas** para os três modelos (rótulo, resposta, citação), em
  0,6 s por modelo e sem nenhuma chamada ao modelo.
- **Auditoria:** **642 de 642 manifestos completos**: 60 chamadas + 6 replays no store de determinismo, e 288
  chamadas + 288 replays offline no store do harness.
- **Estabilidade:** os números de qwen3.5:4b e granite4:micro são os mesmos em três execuções independentes
  (preliminar, segunda e final).

Leitura honesta:

- **As falhas de extração são todas de citação não literal; o valor estava certo em todas.**
  - granite4:micro troca acentos do português: "Tietê" vira "Tieté", "metrô" vira "metró".
  - phi4-mini reescreve palavras ("dirigido" → "direcionada"; "The company employs" → "He employs").
  - qwen3.5:4b põe chaves ou aspas em volta do número (`{240}`).

  A regra de citação literal do CAIN rejeita as três formas, como deve.
- **O harness está perto do teto** em classificação de evidência e verificabilidade: os três modelos acertam quase
  tudo. Só a extração com citação separa os modelos. Um harness v2 precisaria de tarefas mais difíceis, como
  documentos longos, números próximos e negações.
- **Latência é GPU.** Na CPU deste PC (i7-12700F) os números seriam outros, e não foram medidos.
- **Não comparar com o Prompt 3.** O qwen3.5:4b acerta os 48 pares do golden set, inclusive os dois aritméticos que
  os verificadores NLI erram, mas com outra formulação de prompt. Isso sugere um terceiro verificador; não é uma
  medida do verificador.

**Escolha de modelo:** por esta medição, não há motivo para trocar o padrão do `cain.toml` (qwen3.5:4b). Ele empata
no total com o granite4:micro e é o único com 48/48 em evidência. O granite4:micro tem metade da latência e usa
0,35 GB a menos de VRAM, e é a alternativa se velocidade importar mais. Trocar o padrão é decisão do dono.
Gemma 4 E4B e Qwen3.5 9B não foram testados, por causa do download de ≈1 MB/s. Três modelos cumprem o "3–4" do
prompt.

**Achados desta etapa, corrigidos** (runs anteriores preservados fora do repositório, em `runtime/cain-p5/raw/`):

1. A primeira chamada em modo registro num store novo falhava: o arquivo de lock era aberto antes de o diretório
   existir. Commit `c5f371a`, com teste.
2. A auditoria dos manifestos reais mostrou que o replay com o runtime fora do ar ficava sem a identidade do modelo,
   e que um conjunto vazio de parâmetros padrão era contado como ausente. Corrigido: identidade vinda da gravação,
   `identity_from_call`.
3. O RSS do Ollama não vê um modelo que está na GPU. O harness agora registra tamanho e VRAM via `/api/ps`.
4. Hardware: os relatórios dos Prompts 3 e 4 diziam que o qwen3.5:4b rodou na CPU. Rodou na GPU, e os dois foram
   corrigidos. O manifesto deste prompt registra o backend de cada chamada, e foi ele que expôs o erro.

Logs brutos:

| Arquivo | sha256 |
|---|---|
| `2026-09-24-prompt5/environment.txt` | `f59d6ceab50e386535293dabf801c1afbaf35beb4cdcf39f9bed997fc3fea6e1` |
| `2026-09-24-prompt5/determinism.log` | `e670cde7e304aa6977593412758ca48ca0ad33319035954d8dfd8ba3efe445b9` |
| `2026-09-24-prompt5/repeat-qwen3_5_4b.json` | `f7278da79825087955d6a1122c9255efc430a76e8105690efa71be561707f7fd` |
| `2026-09-24-prompt5/repeat-granite4_micro.json` | `16c432a57bd8bab670fb0b21de733e572bb23e108760b18a110c196644c96e04` |
| `2026-09-24-prompt5/repeat-phi4-mini_latest.json` | `27793a2f3256a54994785b98735510826714b1acfbf2636e09f15a93a56bb13a` |
| `2026-09-24-prompt5/replay-qwen3_5_4b.json` | `46643ae3a779ca43548951f4f6e6d065821b2250a301991eeb11ab4097e94d8c` |
| `2026-09-24-prompt5/replay-granite4_micro.json` | `ac7ccf70b95297f4a17c3851569d25ce9a8f72adaf45675c84487d924999ba76` |
| `2026-09-24-prompt5/replay-phi4-mini_latest.json` | `1a4300506a67f9bb150b2fb7ef38af603a484887a2b232b3f7412fd9f39e7f9a` |
| `2026-09-24-prompt5/replay-offline-qwen3_5_4b.json` | `51666a5eeee8f9e92ccf1d70e6b5df744dbe41350b6c8bca937ca01280be03d7` |
| `2026-09-24-prompt5/replay-offline-granite4_micro.json` | `05011894ce31f2ea302dd7b696086b6114412aa1f24907d576c13fb82b234bbe` |
| `2026-09-24-prompt5/replay-offline-phi4-mini_latest.json` | `492db8478abf5056736e4e750e522fc3d2dce62ef3ee2c719574e9b5a2551ab2` |
| `2026-09-24-prompt5/harness-qwen3_5_4b-granite4_micro-phi4-mini_latest.json` | `b2880e91f96aedf4f37250da58998d05ed588f4998f8bb5ec9cae78719d08037` |
| `2026-09-24-prompt5/harness-qwen3_5_4b-granite4_micro-phi4-mini_latest.log` | `d213a57e645c073c78b1d91216ebd700e1ab5869d6905ad23cde005f64d8133c` |
| `2026-09-24-prompt5/harness-qwen3_5_4b-granite4_micro-phi4-mini_latest.summary.json` | `e12c81e3093c013a926a3d19a6a8a15d2da91199c8eecc2fbc499d9f98521cf5` |
| `2026-09-24-prompt5/harness-replay-qwen3_5_4b-granite4_micro-phi4-mini_latest.json` | `25940c25029d4c82a398ba580755b8982cb7747a88ce63e58516f99eb20aacd1` |
| `2026-09-24-prompt5/harness-replay-qwen3_5_4b-granite4_micro-phi4-mini_latest.log` | `d9cf7ef41c3f2e1fa9a7745a4276ab06a5d0fc7bf563ec1fef7ee77acb94b052` |
| `2026-09-24-prompt5/harness-replay-qwen3_5_4b-granite4_micro-phi4-mini_latest.summary.json` | `9e6bb43f5bec6daa1438323ae8b0d9bb307cbdb29dc25fc370e9f3daeeb288f3` |
| `2026-09-24-prompt5/replay-comparison.txt` | `8e04e25b20c46d3a54bf1297af15b971165134bcc39254cee1da4cc77b44065c` |
| `2026-09-24-prompt5/audit-determinism.json` | `afac54a17d5987e6976e1194e8fef698d1598d8edd9f2409d6025c1c639ae2ca` |
| `2026-09-24-prompt5/audit-harness.json` | `f47d872884579fe2ac62d768b722f42472f250f413ac27b70ad4ddedf3948058` |
| `2026-09-24-prompt5/suite.log` | `febcd5c612ce95b2452b67f4fad01c28e6928ea854373f6f99151131703bd46e` |

Os stores SQLite (`runtime/cain-p5/run/state/inference.db` e `harness.db`), com os bytes de cada pedido e resposta,
ficam fora do repositório. O replay offline depende deles.

## PROVEN × DECLARED

| Afirmação | Estado | Por quê |
|---|---|---|
| Manifesto completo em toda chamada ao Ollama | **PROVEN** | teste + auditoria de 642 manifestos reais |
| Modo registro: uma requisição por vez, seed ou temperatura 0 exigida | **PROVEN** | testes (concorrência, recusa) + runs reais com `NUM_PARALLEL=1` |
| 20 chamadas idênticas → 1 saída distinta (3 modelos, GPU, em série) | **PROVEN** neste hardware/build | medição real |
| Replay idêntico, inclusive com o runtime inacessível, sem chamar o modelo | **PROVEN** | 3 × 96 linhas idênticas + 3 replays de chamada única |
| Cache falha fechado em miss e com GGUF diferente sob a mesma tag | **PROVEN** | teste |
| Saída estruturada pelo runtime, tentativas inválidas gravadas | **PROVEN** (runtime real: 0 inválidas em 288; a gravação de inválidas está provada no teste) | teste + harness |
| Tabela do harness | **PROVEN contra gabaritos DECLARED** | medição real; gabaritos escritos pelo agente |
| Caminho do llama.cpp (`/completion`, hash do GGUF, prompt renderizado pelo cliente) | **DECLARED** | código e teste de unidade existentes; não há servidor llama.cpp neste PC |
| Hash do prompt **já renderizado** no Ollama | **não disponível** | o Ollama renderiza o template no servidor e a API não devolve o texto renderizado; o manifesto registra o sha256 do template + system + prompt, que o determinam |
| Streaming (`cain.llm.streaming`) com manifesto | **não coberto** | o streaming não passa pelo gravador; fica para um PR próprio |
| Versões de ferramentas/servidores MCP no contexto | **DECLARED** | o mecanismo (`inference_context`) existe; nenhum chamador o preenche ainda |
| Invariância a batch / mais de um slot | **não testado** | medido só em série |
