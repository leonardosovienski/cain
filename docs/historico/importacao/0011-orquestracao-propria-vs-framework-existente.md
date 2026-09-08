# ADR-0011 — Orquestração própria vs. framework existente

- **Status:** Aceito
- **Faixa:** B (contribuição de pesquisa)
- **Data:** 2026-09-07
- **Relacionados:** ADR-0003 (contrato de mensagem), ADR-0004 (contrato de agente), ADR-0008 (roteamento), ADR-0010 (avaliação)
- **Resolve:** conflito entre `tcc-cain-base.md` (tratava como decidido) e `ESTADO_DO_PROJETO.md` (tratava como aberto)

---

## Contexto

Existem frameworks maduros de orquestração multiagente — AutoGen, LangGraph, CrewAI — que já
resolvem sessão, delegação, mediação e contratos de mensagem. Construir isso do zero é reimplementar
trabalho feito.

A documentação do projeto estava atravessada: a base v0 registrava "implementação própria (sem
LangChain por padrão)" como decisão de stack; o documento de continuidade listava a questão como
decisão técnica ainda aberta. As duas posições conviveram porque ninguém escreveu o argumento.

Isso não é escolha de biblioteca. **Define o tamanho da contribuição de pesquisa.** Sobre framework
existente, a contribuição vira "camada de identidade para AutoGen". Própria, a contribuição é a
arquitetura de coordenação entre identidade e delegação.

## Decisão

**Implementação própria, com escopo deliberadamente restrito.**

O núcleo do Cain implementa: gerenciador de sessão, roteador baseado em regras, mediador, logger de
decisões e o contrato de agente. Nada além disso.

### Fora do escopo da implementação própria

Registrado explicitamente para que o escopo não se expanda por conta própria:

- Execução paralela de agentes
- Conversação agente-a-agente (só orquestrador ↔ agente)
- Criação dinâmica de agentes em tempo de execução
- Políticas de retry, fallback e circuit breaking
- Grafos de execução arbitrários — o fluxo é o de 8 passos do documento mestre
- Streaming de respostas

Cada item acima é uma coisa que AutoGen faz e o Cain **não vai fazer**. Se algum se tornar
necessário, entra por ADR novo, não por deriva.

## Justificativa

**A tese exige.** O argumento central do trabalho é que os frameworks existentes orquestram bem e
tratam identidade como secundária. Construir a demonstração sobre um deles enfraquece a própria
premissa: ou se luta contra as abstrações do framework para inserir a camada de identidade, ou se
aceita a posição subordinada que a crítica denuncia.

**A avaliação exige.** O critério 2 (precisão de delegação) precisa de *ground truth* sobre a decisão
de roteamento, e o `DecisionLog` precisa registrar **por que** cada delegação aconteceu. Roteamento
mediado por framework é opaco nesse ponto exato. O ADR-0008 já escolheu regras + LLM justamente
porque é o que torna a delegação mensurável — usar o roteador de um framework de terceiros
reintroduziria a opacidade que aquela decisão eliminou. **ADR-0008 e este ADR são a mesma decisão
vista de dois ângulos.**

**O custo real é menor do que parece.** Com o escopo acima, o núcleo é da ordem de centenas de
linhas, não milhares. O que torna framework de orquestração caro de construir é exatamente a lista de
itens excluídos.

**AutoGen permanece no trabalho** — como trabalho relacionado na seção 2.2 e como comparação
conceitual. Não como dependência.

## Alternativas consideradas

| Alternativa | Análise |
|---|---|
| **AutoGen** | Concorrente direto e o mais próximo do problema. Descartado por opacidade de roteamento e por subordinar a contribuição. Continua como referência central da 2.2 |
| **LangGraph** | Controle de fluxo explícito resolveria parte da opacidade, mas traz um modelo de grafo e estado que competiria com a camada de identidade pela mesma responsabilidade |
| **CrewAI** | Abstração de papéis é sedutoramente próxima de "identidade" — e é isso que a torna perigosa: colapsaria a distinção entre papel funcional e persona persistente, que é o objeto do trabalho |
| **Própria sem restrição de escopo** | Descartada: é como o cronograma morre. A restrição explícita é parte da decisão, não uma nota lateral |

## Consequências

**Positivas**
- Controle total sobre a instrumentação exigida pelo ADR-0010.
- Nenhuma dependência sujeita a breaking change durante os 15 meses do TCC.
- A contribuição de pesquisa é a arquitetura inteira.
- Custo zero de infraestrutura preservado.

**Negativas**
- Reimplementação de problemas já resolvidos.
- **A banca vai perguntar por que não AutoGen.** Este ADR é a resposta — ela precisa estar no texto
  do TCC, não só no repositório.
- Sem a maturidade e os testes de campo de um framework consolidado.

**Riscos**
- *Scope creep* no núcleo. **Mitigação:** a lista de exclusões acima é normativa; qualquer adição
  exige ADR.
- Um avaliador pode ler a decisão como preferência pessoal por construir do zero. **Mitigação:** o
  argumento de instrumentação (critério 2 + `DecisionLog`) é técnico e verificável — é ele que deve
  ser apresentado, nunca "quis fazer próprio".
