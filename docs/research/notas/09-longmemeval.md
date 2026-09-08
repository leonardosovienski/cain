# Wu et al. — LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory

**Fonte:** [arXiv:2410.10813v2](https://arxiv.org/html/2410.10813v2), §§3–4; [código dos autores](https://github.com/xiaowu0162/LongMemEval). **Versão:** 04/03/2025, ICLR 2025. **DOI do preprint:** [10.48550/arXiv.2410.10813](https://doi.org/10.48550/arXiv.2410.10813). **Consulta:** 07/09/2026.

**O que mede.** Extração, raciocínio entre sessões e temporal, atualização de conhecimento e abstenção.

**Como mede.** 500 perguntas em históricos extensíveis. Configurações publicadas incluem cerca de 115 mil tokens por pergunta (S) e 500 sessões/1,5 milhão de tokens (M). Respostas são avaliadas por juiz LLM com meta-avaliação humana. O estudo separa indexação, recuperação e leitura.

**O que achou.** Identifica perda de desempenho em históricos longos e ganhos com mudanças na organização e consulta da memória. Os resultados dependem de versão, orçamento e avaliador; não são evidência de coerência de personalidade.

**O que implica para o Cain — proposta.** Acrescentar casos de preferência corrigida, informação antiga, inferência entre sessões e resposta “não sei” quando faltar evidência. Registrar gabarito e origem por caso; separar falha de recuperação de falha de geração. Fixar versão do juiz e auditar amostra humana antes de usar pontuação automática em conclusões científicas.
