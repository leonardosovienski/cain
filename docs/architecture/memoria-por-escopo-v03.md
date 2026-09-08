# Preferências e memória por escopo — implementação v0.3

Esta extensão adiciona endereços de preferência à política explícita da v0.2. Não aceita ADRs pendentes, não aprende preferências com LLM e não altera os princípios estáveis da personalidade. A fonte autoritativa continua no SQLite; o índice lexical continua descartável e reconstruível.

## Endereços e precedência

Cada chave tem no máximo um registro corrente em cada endereço. A precedência, por chave, é **turno > sessão > projeto > usuário**. Só os valores ativos participam da composição.

| Escopo da API | Endereço | Quando se aplica |
| --- | --- | --- |
| `user` | usuário | Em qualquer projeto/sessão do mesmo usuário |
| `project` | usuário + projeto | No projeto indicado |
| `session` | usuário + projeto opcional + sessão | Na sessão e no projeto exatos |
| `turn` | usuário + projeto opcional + sessão + turno | No turno exato |

Uma sessão chamada `s` no projeto `a` é diferente da sessão `s` no projeto `b`, ou de `s` sem projeto. Um turno exige sessão; o orquestrador pode usar o `decision_id` como `turn_id`. Os IDs fornecidos devem ser strings não vazias de até 200 caracteres. Escopo desconhecido, endereço incompleto e conflito entre escopo textual e escopo explícito de metadados geram `ValueError`; a declaração não é gravada como preferência global.

Remover uma preferência de um escopo cria um tombstone naquele endereço e revela a preferência ativa do escopo inferior. Por exemplo, remover `format=steps` da sessão deixa valer `format=paragraph` do projeto. Remover no escopo `user` deixa a chave sem valor global. A remoção não restaura versões antigas do mesmo endereço. `clear_preferences` remove as três chaves somente no escopo solicitado.

## Contratos de serviço

```python
inspect(user_id, *, project_id=None, session_id=None, turn_id=None) -> dict
context_for(user_id, query, *, exclude_decision_id=None,
            project_id=None, session_id=None, turn_id=None) -> str
set_preference(user_id, key, value, *, scope="user", project_id=None,
               session_id=None, turn_id=None, expires_at=None) -> IdentityState
forget_preference(user_id, key, *, scope="user", project_id=None,
                  session_id=None, turn_id=None) -> IdentityState
clear_preferences(user_id, *, scope="user", project_id=None,
                  session_id=None, turn_id=None) -> IdentityState
```

As chaves e valores continuam `format=bullets|paragraph|steps`, `verbosity=short|detailed` e `language=pt|en`. `PREFERENCE_SCOPES` enumera os quatro escopos; `PREFERENCE_KEYS` e `PREFERENCE_VALUES` permanecem exportados.

`get` devolve o estado global persistido. `observe`, `update` e os métodos de controle devolvem uma cópia com preferências efetivas para o contexto solicitado. Essa projeção nunca é gravada como perfil global. A revisão é um contador de alterações explícitas do usuário, inclusive alterações em escopos inferiores; uma observação sem alterações aceitas mantém a revisão.

`inspect` preserva os campos antigos (`user_id`, `personality`, `user_model`, `revision`) e acrescenta:

- `effective_preferences`: valores ativos após precedência e expiração.
- `effective_provenance`: procedência do valor vencedor de cada chave ativa.
- `scoped_preferences`: mapas `user`, `project`, `session`, `turn` apenas dos endereços aplicáveis à consulta. Cada entrada contém `value`, `status` (`active`, `expired`, `removed`), `scope`, os três IDs de contexto, `expires_at` e `provenance`.

Os campos antigos de `inspect` representam o estado global armazenado, inclusive o valor de uma preferência global que acabou de expirar. A interface deve usar `effective_preferences` para mostrar o que vale agora e o estado das entradas em `scoped_preferences` para explicar a expiração. Isso mantém o JSON global v0.2 legível sem confundir uma projeção temporal com uma escrita de usuário.

## Entrada explícita e duração

`observe` recebe `project_id`, `session_id` e `decision_id`/`turn_id` em `metadata`. `preference_scope=None` ou ausente permite que o parser escolha o escopo textual, com padrão `user`; outro valor deve ser um escopo válido. `preference_expires_at` é a duração opcional expressa como instante absoluto nos metadados. A API de controle usa o nome `expires_at`.

Exemplos reconhecidos:

```text
Prefiro respostas curtas.                       -> user
Neste projeto, prefiro respostas em passos.     -> project
Nesta conversa, prefiro um parágrafo.           -> session
Só nesta resposta, responda em inglês.          -> turn
```

O escopo é extraído apenas de declarações diretas. Textos citados, trechos de código, conteúdo depois de um marcador de documento e falas de terceiros permanecem dados. A negação remove apenas o mesmo valor já presente no endereço solicitado, sem inferir um valor oposto. Uma declaração de projeto sem `project_id` falha antes de qualquer preferência do lote ser salva. Um `decision_id` legado sem sessão continua válido para o filtro de histórico; ele não constitui um endereço de turno.

`strip_preference_scope_marks(text)` é um auxiliar de roteamento: normaliza acentos/caixa e remove apenas os marcadores de escopo reconhecidos. Não determina se o restante é uma preferência pura e não deve substituir a verificação de tarefa, citação ou instrução do roteador. `ExplicitPreferenceAdaptation.apply/apply_changes` recusam mudanças com escopos locais; sua aplicação exige os IDs disponíveis em `IdentityService`.

`observe` deve acontecer antes de `context_for`, para a preferência explícita orientar a primeira resposta. `update` registra o transcript; quando `preference_observed=True`, não aplica a declaração novamente. Mesmo nessa situação, marca o transcript como contendo preferências, para não recuperá-lo depois como memória de tarefa.

## Expiração e auditoria

`expires_at` aceita `datetime` com timezone ou string ISO 8601 com timezone, deve estar no futuro e é armazenado em UTC. Datas sem horário/fuso e instantes já vencidos são rejeitados. O construtor aceita `clock: Callable[[], datetime]`, permitindo testar a fronteira de validade com um relógio controlado. No instante `now >= expires_at`, a entrada deixa de participar da projeção. A leitura não modifica a revisão nem apaga registros. Uma declaração futura no mesmo endereço substitui o registro corrente, preservando a declaração anterior no histórico de sinais.

A procedência registra origem (`explicit_user_input` ou `explicit_service_command`), sinal, revisão, ação, evidência, instante observado, escopo, endereço e expiração. `supersedes_signal_id` aponta para o sinal anterior do mesmo endereço quando conhecido. A mudança e seu tombstone ficam no campo `scoped_preference_changes` do sinal canônico. Correções anteriores continuam acessíveis no histórico de sinais; não há exclusão definitiva de textos, snapshots, auditoria ou índices de outros consumidores nesta versão.

## Persistência e compatibilidade

A inicialização cria aditivamente a tabela `scoped_preferences`, sem reescrever identidades v0.2. Ela usa a chave composta usuário/escopo/projeto/sessão/turno/chave de preferência. Contextos ausentes são normalizados para string vazia apenas na chave SQL. Preferências globais de JSONs antigos são lidas como camada global; na falta de proveniência anterior recebem a indicação `legacy_global_profile` na projeção.

`IdentityStore.apply_signal` acrescenta o argumento nomeado opcional `scoped_preferences`. Na mesma transação `BEGIN IMMEDIATE`, grava revisão/perfil, snapshot, registros de escopo e sinal. Uma violação de unicidade do sinal ou revisão concorrente cancela o lote inteiro. A fonte é confirmada antes de atualizar o índice; se o índice falhar, o SQLite permite reconstrução posterior. `list_scoped_preferences` lê somente os endereços exatos da consulta. Adaptadores alternativos precisam implementar essa extensão da porta.

## Histórico no contexto

A recuperação filtra `user_id` **e** `project_id`. Sinais legados sem projeto são visíveis somente no contexto global sem projeto; não entram automaticamente em projetos. A sessão define a duração da preferência, mas os episódios de tarefa podem ser recuperados entre sessões do mesmo projeto. Preferências de outras sessões ou turnos não entram nessa recuperação: declarações e transcripts marcados como contendo preferências são excluídos. O contexto instrui o modelo a tratar episódios restantes como dados históricos e a usar o perfil efetivo como autoridade única para preferências.

Os limites existentes permanecem: no máximo `memory_top_k` episódios, trecho de até 1000 caracteres por episódio e `max_context_chars` total. Não há embeddings, recuperação semântica, fatos temporais gerais nem extração automática de preferências implícitas nesta versão.

## Verificação

Os testes novos cobrem precedência por chave, projeto/sessão/turno com IDs repetidos, usuário separado, expiração exata com fuso e reinício, fallback após remoção, fontes e correções preservadas, declaração aplicada antes do contexto, dados citados ignorados, bancos anteriores sem tabela, rollback transacional, rejeição de revisão obsoleta e reconstrução do índice sem ressuscitar preferências. Nenhum desses testes usa inferência real.

### Projeção compacta para inferência

A auditoria completa continua em SQLite e em `inspect`. O contexto enviado ao
modelo contém personalidade, preferências efetivas e expertise/objetivos quando
presentes, sem a proveniência textual nem IDs de auditoria. Identidade e episódios
derivados respeitam juntos `max_context_bytes=2000` por padrão e o limite legado
em caracteres. Episódios podem ser abreviados com indicação explícita; o perfil
essencial não é truncado. A medição considera a serialização JSON em UTF-8.
