# Auditoria de fontes e afirmações — 07/09/2026

O documento mestre recebido é material de trabalho: suas marcações “corrigido”, “validado” e “resolvido” registram alegações do documento, não substituem verificação. Esta auditoria preserva o original e propõe correções para a próxima versão. O escopo é uma revisão focal das referências prioritárias, com fontes primárias; não é revisão sistemática nem reprodução experimental.

| Local no mestre | Veredito | Correção ou limite |
|---|---|---|
| §3.1: campo dividido em duas famílias que não conversam | **Não sustentado como afirmação universal** | Tratar como hipótese de posicionamento. A taxonomia de [Wang](https://arxiv.org/html/2308.11432v7) já relaciona perfil, memória, planejamento e ação. Não inferir lacuna a partir de categorias retóricas. |
| §3.1: complexidade de orquestração degrada identidade | **Hipótese ainda não testada pelas fontes citadas** | Para sustentar causalidade, variar complexidade mantendo modelo, contexto, tarefa e instrumento comparáveis. O protótipo com três agentes, sozinho, não demonstra essa relação. |
| §3.1: Choi prova que persona por prompt não basta | **Redação forte demais** | Preservar o alcance de [Choi, v2](https://arxiv.org/html/2412.00804v2): efeito observado nas configurações estudadas; teste de persona em dois modelos. Não converter em impossibilidade geral, nem justificativa exclusiva da existência do Cain. |
| §3.1: oito rodadas em Li | **Referência correta; alcance deve ser explicado** | Em [Li, v4, §3](https://arxiv.org/html/2402.10962v4), oito rodadas são o horizonte do protocolo de self-chat. Evitar apresentar “8” como limite universal ou confundir rodada com fala. |
| §4.1 e §9.2: Hevner 2004 e três ciclos | **Atribuição a corrigir** | Acrescentar [Hevner (2007)](https://aisel.aisnet.org/sjis/vol19/iss2/4/) para a formulação dos ciclos. [Hevner et al. (2004)](https://aisel.aisnet.org/misq/vol28/iss1/10/) sustenta o framework/diretrizes; [Peffers et al. (2007)](https://jmis-web.org/articles/765) sustenta as seis atividades DSRM. |
| §4.1: duas obras “mais citadas” | **Não auditado** | Remover superlativo ou informar base bibliométrica, consulta e contagem. Ele não é necessário à escolha metodológica. |
| §4.3: ADRs constituem contribuição | **Insuficiente sem evidência** | ADR é registro de decisão; contribuição depende do problema, conhecimento produzido e avaliação. Vincular cada diretriz a evidência concreta, sem antecipar resultado. |
| §5.3 e §13: somente regras permitem ground truth de delegação | **Raciocínio incorreto** | O gabarito pode ser anotado externamente às decisões do roteador. Um roteador LLM pode ser avaliado contra ele. Usar as próprias regras para gerar todos os rótulos e depois avaliá-las cria circularidade. |
| §5.3: framework reintroduz necessariamente opacidade | **Generalização refutada** | [AutoGen documenta seletor personalizável](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html), [estado](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/state.html) e [memória](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/memory.html). Isso não prova suficiência para Cain; exige comparação de uma configuração concreta. |
| §9.1: explicar por que fine-tuning não resolve | **Conclusão antecipada** | Reformular para “alternativas sem ajuste de pesos e seus limites”. Excluir treinamento é uma restrição de pesquisa; não é prova de inutilidade de fine-tuning. |
| §9.2: bibliografia toda validada | **Validação parcial nesta execução** | Títulos e registros prioritários estão documentados nas notas. Há distinção entre preprint e publicação; não declarar leitura integral dos itens marcados como resumo/metadados. |
| §9.2: resultados MemoryBank para arquitetura sem fine-tuning | **Transferência exige cuidado** | [MemoryBank](https://ojs.aaai.org/index.php/AAAI/article/view/29946) exemplifica um sistema com componentes adicionais de treinamento. Não atribuir todos os resultados à memória isoladamente. |
| §9.4: benchmark resolve grande parte da métrica de persona | **Possibilidade, não resultado** | [LoCoMo](https://aclanthology.org/2024.acl-long.747/) e [LongMemEval](https://arxiv.org/html/2410.10813v2) ajudam no protocolo de memória. Rubrica de identidade e adaptação em português requer validação própria. |
| §12.3: notas automaticamente fecham ADR-0006/0007 | **Critério de saída não alcançado** | Notas alimentam decisões, mas não escolhem entre alternativas nem ratificam documentos ausentes. ADRs continuam provisórios até decisão rastreada e compatível com avaliação. |

## Redação sugerida para o problema

“Há evidências de instabilidade de instruções e padrões de resposta em condições específicas de diálogo com LLMs. Este trabalho investiga, em um protótipo delimitado de orquestração, se uma camada explícita de identidade e adaptação melhora a coerência comportamental ao longo de sessões, em comparação com controles definidos previamente. A contribuição e os limites serão estabelecidos pela comparação com trabalhos próximos e pela avaliação do artefato.”

Essa é uma formulação de investigação. Não afirma que o Cain já melhora resultados, que outros sistemas não integram identidade e memória, ou que a lacuna foi comprovada.

## Ajustes bibliográficos concretos

- Choi: separar primeira submissão de 2024 e versão consultada v2 de 17/02/2025; página informa preprint em avaliação. [Registro](https://arxiv.org/abs/2412.00804).
- Li: registrar COLM 2024 e v4 de 25/07/2024. [Registro](https://arxiv.org/abs/2402.10962).
- MemGPT: primeira submissão em 2023; leitura na v2 de 12/02/2024. [Registro](https://arxiv.org/abs/2310.08560).
- Wang: periódico em 2024, artigo 186345; texto aberto consultado v7 de 2025. [Editora](https://link.springer.com/article/10.1007/s11704-024-40231-1).
- Xi: publicação de 17/01/2025, volume 68, artigo 121101; omitir fascículo não confirmado. A lista de autores da versão publicada difere do preprint. [Editora](https://link.springer.com/article/10.1007/s11432-024-4222-0).
- LongMemEval: citar ICLR 2025 quando usando a versão publicada; distinguir do preprint inicial de 2024. [Registro](https://arxiv.org/abs/2410.10813).

## Limites do que foi verificado

A consulta não reproduziu resultados, não implementou AutoGen, não percorreu sistematicamente toda a literatura de 2025–2026 e não comparou Mem0, Zep, MemOS ou A-Mem. LoCoMo foi examinado pelo registro e pelas seções de avaliação do PDF; também abrange coerência narrativa multimodal, portanto não deve ser reduzido a recuperação factual. Xi final tem acesso restrito e a nota usa metadados/resumo e o resumo do preprint. DSR foi verificado por registros/resumos primários e, em Hevner 2004, pela tabela de diretrizes no texto disponibilizado pelo autor; a redação detalhada do capítulo exige leitura integral. Esses limites impedem declarar a lacuna ou a revisão encerradas.

Para dar sequência, executar a comparação especificada em [posicionamento.md](posicionamento.md), preencher as alternativas dos ADRs e congelar rubricas antes da coleta. Revisões do mestre devem incorporar estas correções de forma explícita, preservando seu histórico.
