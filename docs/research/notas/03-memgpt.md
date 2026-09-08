# Packer et al. — MemGPT: Towards LLMs as Operating Systems

**Fonte:** [arXiv:2310.08560v2](https://arxiv.org/html/2310.08560v2), §§2–3. **Versão:** 12/02/2024; primeira submissão 12/10/2023. **DOI:** [10.48550/arXiv.2310.08560](https://doi.org/10.48550/arXiv.2310.08560). **Consulta:** 07/09/2026.

**O que mede.** Recuperação factual entre sessões, personalização de aberturas de diálogo e tarefas com documentos extensos.

**Como mede.** Hierarquia de memória e chamadas de funções movem dados para contexto limitado. No MSC, cinco sessões alimentam pergunta adicional de recuperação; avaliação usa resposta de referência, ROUGE-L e juiz LLM. Baselines recebem resumo com perda; MemGPT consulta histórico completo.

**O que achou.** Melhora recuperação frente aos baselines publicados. O contraste inclui diferenças no acesso à informação; não isola somente organização estrutural com contexto idêntico. Personalização factual não é medida suficiente de estabilidade de estilo.

**O que implica para o Cain — proposta.** ADR-0006 pode comparar memória autoritativa, memória recuperável e contexto efetivamente enviado. Registrar seleção e orçamento de contexto por resposta. Não reivindicar novidade apenas por armazenar persona e histórico externamente. Para atribuir efeito à estrutura, comparar braços com conteúdo disponível pareado e explicitar qualquer diferença de seleção, ordem ou tokens. Nenhuma alternativa é aceita por esta nota.
