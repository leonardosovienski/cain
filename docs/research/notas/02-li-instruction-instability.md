# Li et al. — Measuring and Controlling Instruction (In)Stability in Language Model Dialogs

**Fonte:** [arXiv:2402.10962v4](https://arxiv.org/html/2402.10962v4), §§3 e 6. **Versão:** 25/07/2024; COLM 2024 indicado pelos autores. **DOI do preprint:** [10.48550/arXiv.2402.10962](https://doi.org/10.48550/arXiv.2402.10962). **Consulta:** 07/09/2026.

**O que mede.** Aderência a instruções ao longo de diálogos sintéticos; inclui formato, idioma, memorização e características do agente.

**Como mede.** Duas cópias do chatbot, instruções diferentes, oito rodadas; 100 prompts em cinco categorias. Substitui-se retrospectivamente uma mensagem por sonda, avaliando a resposta com função específica. Uma rodada contém duas falas.

**O que achou.** O protocolo detecta drift em modelos como LLaMA2-chat-70B e GPT-3.5. Oito rodadas é horizonte experimental, não prazo universal de falha. Split-softmax modifica atenção durante inferência e melhora o compromisso estabilidade/desempenho nos testes.

**O que implica para o Cain — proposta.** Ramificar snapshots para sondas que não alterem o histórico principal; fixar idioma, rubrica e versão do modelo. Separar instruções verificáveis de julgamentos subjetivos de estilo. Split-softmax não equivale a uma camada de memória e exige acesso à inferência; não assumir disponibilidade via API fechada. Atribuições de causa à atenção devem preservar o caráter de hipótese dos autores.
