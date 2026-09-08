# Wu et al. — AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation

**Fonte:** [arXiv:2308.08155v2](https://arxiv.org/html/2308.08155v2), texto e apêndice D. **Versão:** 03/10/2023. **DOI:** [10.48550/arXiv.2308.08155](https://doi.org/10.48550/arXiv.2308.08155). **Consulta:** 07/09/2026. A nota trata do paper, não de todas as versões posteriores do software.

**O que mede.** Utilidade de aplicações construídas por conversa entre agentes, em tarefas como matemática, código, QA e decisão.

**Como mede.** Agentes configuráveis combinam LLM, ferramentas e humanos. Fluxos podem ser programados em linguagem natural e código. Estudos qualitativos e quantitativos variam por aplicação; matemática usa GPT-4 e comparadores específicos.

**O que achou.** Apresenta resultados favoráveis nos casos estudados. Não é experimento longitudinal controlado sobre identidade; ausência dessa avaliação não significa impossibilidade arquitetural de implementá-la.

**O que implica para o Cain — proposta.** Usar como comparador técnico: quais componentes o Cain necessita instrumentar e qual custo de adaptação? ADR-0008 pode comparar roteadores por regras e LLM com o mesmo conjunto rotulado. A justificativa de núcleo próprio deve indicar escopo e controle experimental. “Todo framework é opaco” é generalização indevida; ver também a [checagem da documentação](13-autogen-documentacao.md).
