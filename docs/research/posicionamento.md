# Posicionamento provisório e decisões que a literatura informa

**Data:** 07/09/2026. **Estado:** proposta para discussão e experimento; não é declaração de novidade nem aceite dos ADRs 0006–0008. Ver [notas](notas/README.md) e [auditoria](auditoria-fontes.md).

O recorte investigável do Cain é a relação entre coerência do comportamento, adaptação a preferências e delegação em um sistema com três agentes. Separar esses construtos torna o resultado interpretável: preservar fatos não demonstra estilo consistente, e mudar um perfil não demonstra adaptação correta.

## Matriz inicial de comparação

“Não avaliado” significa que o instrumento lido não responde à pergunta; não significa que o sistema não possa suportá-la.

| Trabalho / evidência | Construto principal | Relação com Cain | Lacuna da comparação atual |
|---|---|---|---|
| [Choi](notas/01-choi-identity-drift.md) | Drift em diálogo sintético | Motiva sondas de comportamento | Não testa a arquitetura Cain |
| [Li](notas/02-li-instruction-instability.md) | Aderência a instruções | Inspira sondas por snapshot | Transferência para tarefas/português pendente |
| [MemGPT](notas/03-memgpt.md) | Contexto e memória entre sessões | Alternativa de organização da memória | Identidade e delegação não isoladas pelo instrumento lido |
| [MemoryBank](notas/04-memorybank.md) | Histórico e personalização | Alternativas de atualização/retenção | Efeito puro da estrutura Cain não medido |
| [AutoGen](notas/05-autogen.md) e [docs](notas/13-autogen-documentacao.md) | Orquestração configurável | Comparador de implementação | Configuração equiparável ainda não implementada |
| [Wang](notas/06-wang-survey.md) e [Xi](notas/07-xi-survey.md) | Taxonomias de agentes | Vocabulário e busca por comparadores | Surveys não são baseline experimental |
| [LoCoMo](notas/08-locomo.md) e [LongMemEval](notas/09-longmemeval.md) | Memória longitudinal | Sessões, evidências e casos de atualização | Validade da rubrica de persona não estabelecida |

## Propostas para o ADR-0006 — modelo de identidade

Comparar três alternativas explicitamente: persona como texto persistido; estado estruturado com campos validados; estrutura combinada com memória episódica recuperável. Para cada opção registrar conteúdo que chega ao LLM, orçamento de tokens, controle de versões e comportamento diante de conflito. Memória hierárquica e estrutura de perfil já têm antecedentes; a novidade não pode ser apenas renomear seus componentes.

Proposta de separação operacional, a validar:

- **Identidade do agente:** compromissos comportamentais relativamente estáveis, com critérios observáveis nas respostas.
- **Perfil do usuário:** preferências sustentadas por evidência, com origem e possibilidade de correção.
- **Memória episódica:** eventos de interação e evidência que apoiam recuperação e auditoria.
- **Contexto enviado:** seleção concreta usada naquela geração; deve ser registrada para interpretar efeito.

Um campo só deve entrar se houver razão funcional e maneira de avaliar sua influência. `tom`, `verbosidade` e `proatividade` precisam de escalas e sondas operacionais; números entre zero e um não tornam um construto validado. Esta proposta não determina esquema definitivo.

## Propostas para o ADR-0007 — adaptação

Comparar ausência de adaptação, atualização por preferência explícita e atualização por sinais inferidos. Tratar confirmação explícita e inferência como evidências de força diferente. Definir resolução de contradições, janela temporal, limites de mudança e rollback. Separar decisão de guardar episódio da decisão de alterar preferência.

Especificar sequência roteirizada com preferência conhecida, sua eventual alteração e correção. Medir distância ao alvo por sessão, atraso para corrigir e alterações incorretas. Reservar sondas de identidade distintas das sondas de preferência, incluindo pares com o mesmo tema e perfis diferentes. Não assumir que decay inspirado em memória humana é superior; ele é uma alternativa a comparar.

## Propostas para o ADR-0008 — roteamento

Regras, LLM e híbrido são todos avaliáveis se o gabarito for independente do mecanismo. Criar conjunto de pedidos revisado antes da execução, com conjunto de agentes aceitáveis quando houver ambiguidade e indicação de tarefas que exigem múltiplas etapas. Registrar critérios de desempate e casos em que nenhuma capacidade atende.

Comparar precisão por classe, cobertura/abstenção e sucesso da tarefa. Uma taxa global pode esconder a exclusão sistemática de um agente. Alterações de contexto que mudem a delegação precisam de registro de entrada, regra/modelo escolhido e saída estruturada; não é necessário coletar raciocínio interno do LLM.

Um núcleo próprio pode facilitar o escopo limitado do experimento. Comparar essa escolha com uma configuração instrumentada de AutoGen requer estimar adaptação, visibilidade de estado, substituição de componentes e restrições de serialização. As capacidades documentadas de um framework não demonstram nem impedem sucesso no experimento Cain.

## Contraste que pode sustentar a avaliação

O contraste entre um controle com informação pareada e Cain deve declarar exatamente o que muda: estrutura, ordem, seleção, atualização, localização da persona e tamanho do contexto. Parear apenas quantidade de tokens não garante equivalência de informação. Se múltiplos fatores mudarem juntos, interpretar o resultado como efeito do pacote arquitetural, não de um fator isolado.

Repetições com dublê determinístico demonstram integridade do harness; não demonstram estabilidade de um LLM nem validade das sondas. Um piloto real deve incluir contraprovas: respostas que mantêm o tema mas trocam estilo; respostas que mantêm estilo mas perdem fatos; perfis diferentes com a mesma tarefa; preferências alteradas por correção explícita. Uma métrica útil precisa discriminar esses casos de forma coerente com a definição operacional.

## Próxima etapa da revisão, com saída verificável

1. Fixar critérios de inclusão: memória entre sessões, perfil/identidade explícitos, influência no planejamento/delegação, extensibilidade e protocolo avaliativo. Registrar período, bases, strings e exclusões.
2. Ler versões integrais pendentes, percorrer referências dos surveys e examinar Mem0, Zep, MemOS e A-Mem como candidatos citados pelo mestre. A presença nessa fila não afirma suas capacidades.
3. Para cada concorrente próximo, adicionar na matriz versão/commit e evidência por requisito, incluindo “não encontrado no material consultado” quando necessário. Buscar contraexemplos à alegação de novidade.
4. Selecionar e justificar alternativas nos ADRs, com consequências e experimento discriminante. Só então alterar seu status, preservando o registro de decisão.
5. Validar rubricas em piloto real e fechar controles antes da coleta de resultados científicos.

**Critério de conclusão desta etapa futura:** uma contribuição delimitada que permaneça defensável mesmo quando comparadores já oferecem memória, perfil e roteamento; decisões rastreadas; e instrumento capaz de distinguir as hipóteses. Esta entrega prepara esse trabalho, sem alegar que ele já foi concluído.
