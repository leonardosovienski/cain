# CAIN — Prompt 2: memória bitemporal e consulta `as_of` (2026-09-24)

Branch `melhorias/p2-memoria-bitemporal`, a partir do `main` `5d55732`. Tudo local; nenhum segredo; nenhum modelo real
(o PC 2 não tem Ollama nem llama.cpp).

## O que foi feito

Pacote novo `cain.memory` e o comando `cain memory`:

| Item do prompt | Implementação | Arquivo |
|---|---|---|
| 1. Log append-only com hash encadeado, JSON canônico JCS | `memory_events`: cada evento é canonicalizado por RFC 8785 e encadeado por sha256 (`previous_hash` → `entry_hash`); triggers recusam UPDATE, DELETE e REPLACE. `verify()` recalcula a cadeia e compara as projeções com um replay. | `src/cain/memory/jcs.py`, `src/cain/memory/store.py` |
| (reuso do `predictor_core`) | **Não houve.** O `predictor_core` (5a08415) não tem log com cadeia de hash nem JCS: o `JsonlStore` é JSONL append-only sem cadeia e sem forma canônica. O padrão foi portado do `SQLiteDecisionLog` do próprio CAIN, trocando o `json.dumps` pelo JCS. | — |
| 2. Tabela de fatos | `memory_facts(id, cube, subject, predicate, object, valid_from, valid_to, recorded_at, superseded_at, supersedes, source_episode_id, source_hash, extractor_model, extractor_prompt_hash, extractor_version, status)` (+ `event_seq`) | `store.py` |
| 3. Nada é apagado | Correção = fato novo com `supersedes` e `superseded_at` no antigo; `correct_fact` e `cain memory correct`. Nenhum caminho apaga fato ou evento. | `store.py` |
| 4. `as_of(T)` obrigatório em toda leitura, antes da busca vetorial | `facts`, `documents`, `search` e `fact_history` exigem `as_of` (keyword sem padrão; a CLI exige `--as-of`, e `now` precisa ser digitado). Filtro: `recorded_at <= T AND (superseded_at IS NULL OR superseded_at > T)`; documentos também `published_at <= T`. A busca aplica o filtro em SQL e só depois calcula vetores dos candidatos visíveis. A visão `as_of` esconde um `superseded_at` posterior a T (senão revelaria que existe uma correção no futuro). | `store.py` |
| 5. Dados estruturados sem LLM; LLM só em texto livre, sempre DECLARED | `ingest_research`: transcrição determinística dos registros admitidos no acervo de pesquisa (Snapshot com hash), `status = PROVEN`, `extractor_version = deterministic:research-snapshot-record/1`, idempotente por `source_hash`; revisão com `supersedes` declarado substitui a anterior. `extract_facts`: modelo local propõe fatos; só entram os que citam o texto literalmente; todos `DECLARED`, com modelo@digest, hash do prompt e versão do extrator. `assert_fact` recusa `PROVEN` para fato extraído por modelo. | `src/cain/memory/ingest.py` |
| 6. Cubos por domínio | `cube` obrigatório em toda escrita e leitura; ler mais de um cubo exige `cross_cube=True` (`--cross-cube`); correção não atravessa cubos; ingestão recusa registro de outro domínio. | `store.py`, `ingest.py` |
| 7. Índices derivados reconstruíveis; `rebuild-index` | Fatos, documentos e vetores são projeções. `rebuild-index` apaga as três e refaz tudo a partir do log. Com o log quebrado, recusa (`CHAIN_BROKEN`). | `store.py`, `src/cain/memory/cli.py` |

## Como rodar

```sh
cain memory --db data/memory.db add-fact --cube stocks --subject QUAL-PIT-MOM-001 --predicate net_excess_bps --object 29
cain memory --db data/memory.db correct <fact_id> --object 31 --reason "releitura"
cain memory --db data/memory.db facts --as-of 2026-09-24T14:02:08Z --cube stocks
cain memory --db data/memory.db search "funding" --as-of now --cube crypto
cain memory --db data/memory.db ingest-research --cube crypto --research-db data/research.db --policy <policy.json>
cain memory --db data/memory.db verify
cain memory --db data/memory.db rebuild-index
# com modelo local (cain.toml): --vectors para o índice vetorial; extract para texto livre
```

## Testes (obrigatórios do prompt e extras)

`tests/unit/test_memory_jcs.py` (vetores da RFC 8785) e `tests/integration/test_memory_bitemporal.py`:

| Teste obrigatório | Teste | Resultado |
|---|---|---|
| Fato com `recorded_at` no futuro fica invisível a `as_of` anterior, inclusive na busca vetorial | `test_future_recorded_fact_is_invisible_to_earlier_as_of_including_vector_search`: o fato futuro é o melhor casamento léxico e vetorial e mesmo assim não aparece; o vetor dele nem é calculado antes de ficar visível | passou |
| Fato corrigido: antes da correção, valor antigo; depois, o novo | `test_corrected_fact_before_and_after_the_correction` (inclui: a visão antiga não mostra `superseded_at` futuro) | passou |
| Adulterar evento antigo quebra a verificação | `test_tampering_with_an_old_event_breaks_the_chain`: os triggers recusam UPDATE/DELETE; derrubando o trigger e reescrevendo o evento 1, `verify` acusa `broken_at=1`; re-hashear o evento só move a quebra para o elo seguinte; `rebuild-index` recusa | passou |
| `rebuild-index` gera o mesmo resultado de busca | `test_rebuild_index_reproduces_the_same_search` (busca híbrida com embedding determinístico de teste: resultado idêntico antes e depois) | passou |

Extras: `as_of` obrigatório em toda leitura; instante sem fuso recusado; cubos isolados; documentos exigem publicação e
registro até T; relógio que volta é recusado; regras de `PROVEN`/`DECLARED`; extração literal; ingestão determinística
idempotente com revisão; projeção adulterada detectada e reconstruída; caminho completo pela CLI (`cain.cli.main`).

**Achado durante o desenvolvimento** (corrigido antes do commit): a primeira versão devolvia, numa leitura `as_of`
anterior à correção, o `superseded_at` do futuro. O valor era o antigo, mas a linha revelava que uma correção viria depois.
Os testes `test_corrected_fact…` e `test_documents_need_both…` agora exigem `superseded_at = null` nesse caso. Com a
máscara desligada em memória, os dois falham; com ela, passam.

Suíte completa (Python 3.13.15, venv do `uv.lock`): **1198 passed, 2 skipped, 0 failed**; cobertura total **87%**
(piso do CI: 86%); `memory/`: jcs 100%, store 92%, ingest 93%, cli 85%. `ruff check .`: ok.

## Evidência de runtime (console script `cain`, fora do pytest)

`docs/evidence/2026-09-24-prompt2/runtime_demo.log`:
`add-fact` → `correct` → `facts --as-of T1` devolve `[(29, None)]` → `facts --as-of now` devolve o valor corrigido →
`facts` sem `--as-of` sai com exit 2 → `verify` diz `intact consistent` → `rebuild-index` replaya 2 eventos →
adulteração do evento 1 fora da API → `verify` diz `broken broken_at=1` → `rebuild-index` recusa (`CHAIN_BROKEN`).

| Arquivo | sha256 |
|---|---|
| `2026-09-24-prompt2/suite.log` | `fd099ebb93c4ce24c2700691147a6ffa0b9f67542eccd0990982b7caa4a2ca29` |
| `2026-09-24-prompt2/runtime_demo.log` | `a20741cd4008b7b0c9c26f3992d83d1a5ae72f55442a3a33c23bfe3a3f311112` |

## PROVEN × DECLARED

| Afirmação | Estado | Por quê |
|---|---|---|
| Log append-only com cadeia sha256 sobre JCS, verificação e detecção de adulteração | **PROVEN** | código no caminho `cain memory`; testes + demo do console script |
| `as_of` obrigatório e sem vazamento em fatos, documentos e busca (léxica e híbrida) | **PROVEN** | testes de vazamento; demo |
| Correção sem apagar, com visão `as_of` correta | **PROVEN** | testes; demo |
| `rebuild-index` reconstrói projeções e vetores com o mesmo resultado | **PROVEN** (embedding determinístico de teste) | teste; demo sem vetores |
| Isolamento por cubo | **PROVEN** | testes; demo (`CROSS_CUBE_NOT_EXPLICIT`) |
| Ingestão determinística do acervo de pesquisa | **PROVEN** com acervo sintético pela CLI | teste pela `cain.cli.main`; nenhum acervo real neste PC |
| Índice vetorial com o modelo de embedding real (`--vectors`) | **DECLARED** | caminho de código existe; sem Ollama no PC 2 |
| Extração por LLM (`cain memory extract`) | **DECLARED** | testada com modelo falso; sem modelo real aqui |
| `as_of` na memória antiga de conversa (identidade, preferências, turnos, documentos do projeto) | **não feito** | fora deste PR; essas leituras continuam sem `as_of`, só a memória nova o exige |
| `as_of` no acervo L0 (`research query`) | **não feito** | o acervo já guarda `recorded_at`/`available_at` por registro; o filtro fica para um PR próprio |

## O que ficou de fora e por quê

- A memória de conversa do chat (`/run`, `chat`) não passa pela memória nova. Ligar as duas é mudança de comportamento do
  chat e fica para quando o loop (Prompt 6/7) precisar.
- Sem Ollama no PC 2: o índice vetorial real e a extração por LLM ficam DECLARED até rodarem numa máquina com modelo.
