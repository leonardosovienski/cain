# Execução técnica smoke-20260907

Foram preservadas 324 respostas/saídas de 6 cenários, 3 sessões e 3 braços. Provedor: `fake`. Este smoke verifica conexões e exportações. Não é coleta científica nem demonstra eficácia da arquitetura.

A usa prompt estático; B recebe somente transcritos brutos de sessões anteriores; C atravessa o runtime. O orçamento em caracteres é substituto técnico: não comprova equivalência de tokens. Casos C sem chamada LLM ficam sem comparação de contexto. C também pode recuperar interações da sessão atual, enquanto B só acessa sessões anteriores. A exposição à informação difere e impede inferência B/C. Logs registram o orçamento efetivo e preservam contextos injetados.

Coerência por embeddings, rubrica humana, convergência, satisfação e concordância não foram medidas; constam como nulas com motivos. Acurácia de roteamento se refere somente ao roteador provisório e aos exemplos executados.

**Validade de construto das sondas NÃO demonstrada.** O piloto com LLM real e avaliadores humanos permanece pendente. ADR-0010 continua Proposto.

Para avaliação cega compartilhe apenas `blind/` e a rubrica; a chave está em `private/unblinding.json`. Todos os cenários foram mantidos.
