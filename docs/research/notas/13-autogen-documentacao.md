# AutoGen — checagem de capacidades documentadas

**Fonte/versão:** documentação oficial no canal `stable`, consultada em **07/09/2026**; URLs mutáveis, sem versão de pacote fixada nesta inspeção. São exemplos documentados, não testes executados localmente.

**O que mede.** A inspeção verifica existência de extensões, não desempenho empírico.

**Como mede / o que achou.** Três páginas primárias mostram:

- [Memory and RAG](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/memory.html): protocolo de memória, inclusão de preferências no contexto e armazenamento extensível.
- [Managing State](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/state.html): salvar/carregar estado de agentes e equipes; exemplos de persistência entre execuções.
- [Selector Group Chat](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html): `selector_func` substitui a seleção por modelo; retorno `None` delega ao seletor padrão. Há limitação documentada de serialização dessa função.

**O que implica para o Cain — proposta.** Essas capacidades refutam a descrição universal de framework sem controle ou persistência. Não provam que AutoGen já satisfaz o construto de identidade do Cain. A comparação deve fixar pacote/commit, configurar os mesmos contratos e medir custo de adaptação/instrumentação. Uma escolha de núcleo próprio por escopo restrito é defensável sem negar capacidades existentes. Não mudar decisão aceita apenas com base nesta inspeção.
