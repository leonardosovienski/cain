# Adaptação explícita e memória — implementação 0.2

Esta versão substitui o mecanismo de adaptação vazio por regras determinísticas para
preferências declaradas diretamente pelo usuário. Não aceita nem encerra os ADRs 0006/0007:
o modelo científico de identidade e a validade de adaptação continuam em revisão.
Não há fine-tuning, inferência de personalidade nem aprendizado a partir de respostas do LLM.

## Contratos e valores

`IdentityService.observe(user_id, user_text, metadata=None)` persiste a entrada e atualiza o
perfil antes de montar o contexto da resposta. O orquestrador registra depois o transcrito
com `update(user_id, Signal(...))`, informando `user_input` e `preference_observed=True`.
Assim a entrada é aplicada uma vez, e texto gerado/documentos não vira evidência de preferência.

| Chave | Valores canônicos | Exemplo de declaração reconhecida |
|---|---|---|
| `format` | `bullets`, `paragraph`, `steps` | “Prefiro respostas em tópicos.” |
| `verbosity` | `short`, `detailed` | “Quero respostas detalhadas.” |
| `language` | `pt`, `en` | “Prefiro respostas em inglês.” |

As constantes `PREFERENCE_VALUES` e `PREFERENCE_KEYS` são exportadas por `cain.identity`.
O parser aceita primeira pessoa, prefixos simples de correção, acentos Unicode normalizados,
e combinações como “Prefiro respostas curtas em passos e em português”. A gramática é limitada:
frases ambíguas, condicionais, citações, blocos de código e falas identificadas de terceiros
são ignorados. Perguntas como “Quero saber por que o cliente prefere inglês” não alteram perfil.
Isso é extração conservadora, não compreensão geral de linguagem natural. Preferências
temporárias de uma tarefa e permanentes ainda exigem uma distinção de produto mais refinada.

## Conflitos, correção e remoção

A declaração explícita mais recente, na ordem de gravação, prevalece para cada chave.
“Agora prefiro um parágrafo” substitui `steps` por `paragraph`. Uma negação simples remove
somente o valor citado se ele for o atual: “Não prefiro respostas curtas” remove `short`,
sem inferir `detailed`. Não remove uma preferência diferente que já esteja vigente.

`inspect(user_id)` retorna uma cópia do perfil atual. `forget_preference(user_id, key)` remove
uma preferência; `clear_preferences(user_id)` remove todas as três dimensões conhecidas.
Também são reconhecidos “Esqueça minha preferência de formato” e
“Esqueça todas as minhas preferências”. Cada remoção deixa um registro de remoção na procedência.
Essas operações retiram valores do perfil operacional; **não apagam transcritos, snapshots ou
logs históricos**. A interface deve informar essa distinção ao usuário.

Cada alteração incrementa `IdentityState.revision` e conserva em
`UserModel.preference_provenance` a origem, identificador do sinal, revisão, data, ação, valor
e trecho da declaração. Uma nova declaração idêntica reafirma a evidência e também gera revisão.
Os princípios e o estado da personalidade não são alterados por essa política.

## Persistência e recuperação

A extensão `IdentityStore.apply_signal(user_id, signal, state=None, expected_revision=None)`
grava sinal, perfil alterado e snapshot em uma transação SQLite. Uma revisão desatualizada
é rejeitada explicitamente, sem retry. Duplicação do identificador do sinal reverte toda a
transação. JSON antigo, sem procedência, continua legível pelo valor padrão do novo campo;
não há migração destrutiva ou reescrita de documentos originais.

O índice recebe a entrada somente depois do commit autoritativo. Se o índice falhar, o erro
é informado, mas sinal e preferência já persistidos continuam válidos. `rebuild_from(store)`
recupera o índice. A API deve evitar dizer que nada foi alterado em uma falha de indexação.

Por padrão, o contexto tem até 6.000 caracteres e até três memórias, selecionadas entre no
máximo doze candidatos lexicais do mesmo usuário. Cada trecho tem até 1.000 caracteres.
São limites de caracteres, não equivalência de tokens de avaliação. O perfil canônico é
preservado integralmente; se ele sozinho exceder o limite, ocorre erro explícito.
O orquestrador pode informar `exclude_decision_id` em `context_for` para que a entrada
acabada de observar não seja reapresentada como memória histórica da própria requisição.

Episódios que contêm declaração de preferência são excluídos do contexto recuperado porque
o valor vigente já está no perfil. Metadados identificam entradas novas; um filtro lexical
conservador cobre registros antigos. Isso sacrifica parte do contexto de uma tarefa misturada
com preferências para evitar que uma preferência corrigida/esquecida reapareça por recuperação.
`is_preference_memory(text, metadata)` fornece a mesma política para o agente Busca.
O texto bruto permanece no armazenamento autoritativo. Memórias são rotuladas como dados,
nunca como ordens, e preferências ausentes/removidas não devem ser reconstruídas delas.

## Evidência técnica e limites

Os testes exercitam correção e reabertura SQLite, procedência, negação, Unicode, citação e
terceiros, exclusão de aprendizado por saídas geradas, remoção sem ressurgimento após rebuild,
isolamento de usuários, limites do contexto, rollback transacional e conflito de revisão.
Esses testes demonstram comportamento de engenharia nas entradas cobertas. Não comprovam
coerência de personalidade, validade de construto ou eficácia científica do Cain.

A busca continua lexical; memória semântica, inferência implícita, decaimento/retenção temporal,
exclusão definitiva de dados e uma política completa de concorrência entre sessões não são
implementados por esta atualização.
