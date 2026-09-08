# ADR-0010 — Protocolo e métricas de avaliação

- **Status:** Proposto *(não Aceito — depende de §12.2 do documento mestre e da validação do orientador)*
- **Faixa:** B (contribuição de pesquisa)
- **Data:** 2026-09-07
- **Relacionados:** ADR-0006 (modelo de identidade), ADR-0008 (roteamento), ADR-0009 (persistência)

> Este ADR precisa estar **Aceito antes da primeira coleta de dados**. Fixar métrica depois de ver
> resultado é o modo mais comum de invalidar um trabalho de DSR sem perceber.

---

## Contexto

Os quatro critérios de avaliação estão fechados desde o esboço: coerência de identidade, precisão de
delegação, adaptação ao perfil e satisfação percebida. O que nunca foi fechado é **como medir cada
um**, e as notas de método do próprio projeto já registravam que este é o ponto onde qualificação em
DSR costuma travar.

Há dois problemas estruturais além da falta de métrica:

1. **Ameaça de validade interna.** Se o Cain recebe contexto de sessões anteriores e o baseline não,
   qualquer ganho medido pode ser efeito de "mais contexto", não da arquitetura de identidade. O
   experimento provaria algo trivial e já conhecido.
2. **Canibalização entre critérios 1 e 3.** Coerência premia estabilidade; adaptação premia mudança.
   Medidos sobre a mesma superfície, melhorar um piora o outro mecanicamente, e o resultado não
   significa nada.

## Decisão

### 1. Três braços experimentais, não dois

| Braço | Descrição | O que a comparação isola |
|---|---|---|
| **A — Baseline** | LLM + system prompt estático. Sem persistência, sem orquestração explícita. | — |
| **B — Controle pareado por contexto** | LLM + despejo bruto dos transcritos das sessões anteriores, **no mesmo orçamento de tokens** que o Cain injeta. Sem estrutura de identidade, sem roteamento. | A vs B: efeito de ter memória |
| **C — Cain** | Identidade estruturada + roteamento + mediação. | **B vs C: efeito da estrutura** |

A vs C prova que *alguma coisa* ajuda. **B vs C é a comparação que sustenta a tese**, porque isola a
contribuição arquitetural do efeito trivial de dispor de mais contexto. Sem o braço B, a banca tem
uma pergunta óbvia e o trabalho não tem resposta.

Custo: o braço B é barato — é o mesmo harness do baseline com um injetor de transcrito. O retorno em
força argumentativa é desproporcional ao esforço.

### 2. Separação de superfície entre os critérios 1 e 3

Adotada a divisão proposta no documento mestre (§6.3), **imposta no nível da métrica**, não só no
conceito:

| Critério | Mede | Sondas | Objeto |
|---|---|---|---|
| **1 — Coerência** | `PersonalityState` | Sondas de **estilo** | Estável entre sessões |
| **3 — Adaptação** | `UserModel` | Sondas de **conteúdo de perfil** | Evolui entre sessões |

Os dois conjuntos de sondas são **disjuntos**. Nenhuma sonda alimenta os dois critérios. Se houver
interseção, a canibalização volta pela porta dos fundos.

### 3. Métricas por critério

**Critério 1 — Coerência de identidade**
- Conjunto fixo de *N* sondas de estilo, aplicadas em todas as sessões, com **conteúdo factual
  controlado** (a resposta correta é a mesma; só o estilo pode variar).
- Quantitativo: distância de cosseno entre embeddings das respostas à mesma sonda em sessões
  distintas. Menor = mais coerente. Reportar a **distribuição**, não só a média.
- Qualitativo: rubrica cega, Likert por traço (tom, verbosidade, estrutura, estilo de tratamento de
  erro). Rubrica escrita **antes** da coleta.
- Concordância entre avaliadores reportada (Cohen's κ ou percentual simples, dado o n pequeno).

**Critério 2 — Precisão de delegação**
- *Ground truth* por cenário: qual agente deveria atender. Definido junto com os cenários,
  antes da execução.
- Acurácia + **matriz de confusão** 3×3. A matriz importa mais que a acurácia: erra-se para qual
  agente, e por quê.
- Só é mensurável porque o roteador é baseado em regras (ADR-0008). Com roteamento livre por LLM não
  existiria *ground truth* — a decisão arquitetural e a mensurabilidade estão acopladas.

**Critério 3 — Adaptação ao perfil**
- **Personas de usuário roteirizadas**, com preferências declaradas e conhecidas *a priori*.
- Métrica de **convergência**, não de mudança: a distância entre o `UserModel` inferido e a
  preferência declarada da persona diminui ao longo das sessões?
- Medir só "o perfil mudou" premiaria ruído. Um sistema que muda o perfil aleatoriamente pontuaria
  bem. A direção é o que importa.

**Critério 4 — Satisfação percebida**
- Escala Likert, aplicada após interação, com ordem dos braços randomizada e cega.
- **Reportado como descritivo e indicativo.** Nenhum teste de significância com n < 20.
- **Plano B declarado desde já:** se a aprovação em comitê de ética não vier a tempo ou não for
  viável, o critério 4 é substituído por avaliação qualitativa de 2–3 avaliadores cegos com rubrica.
  A substituição está decidida aqui, antes de saber a resposta — não vai ser improvisada sob pressão
  de prazo.

### 4. Controles de execução

- **Temperatura fixada e reportada.** Seed fixada onde o backend permitir.
- Ordem de apresentação dos braços randomizada; avaliação **pareada e cega**.
- Rubricas e *ground truth* escritos e commitados **antes** da primeira coleta (o commit datado é a
  prova).
- Todos os logs brutos versionados em `evaluation/results/`, com o `run_id` amarrando log,
  configuração e análise.
- Nenhum cenário descartado após a coleta. Se um cenário for inválido, a invalidação é justificada
  por escrito e o dado permanece no repositório.

### 5. Amostra

5–10 cenários atravessando os três agentes × 3 braços × ≥3 sessões separadas.

## Justificativa

O braço B é a decisão que carrega este ADR. Sem ele o trabalho é vulnerável a uma única pergunta, e
é a pergunta que qualquer avaliador competente faz. Com ele, a resposta já está no desenho
experimental.

A escolha de medir adaptação por convergência a uma persona roteirizada resolve um problema que os
documentos anteriores não tinham visto: "o perfil evoluiu" é uma métrica que ruído satisfaz. Usar
personas com preferência conhecida transforma uma medida de variação em uma medida de acerto.

Fixar o plano B do critério 4 antes de conhecer a resposta do comitê de ética é deliberado: separa a
decisão metodológica da pressão de cronograma.

## Alternativas consideradas

| Alternativa | Por que foi descartada |
|---|---|
| Dois braços (baseline vs. Cain) | Não isola estrutura de contexto; deixa a ameaça de validade interna aberta |
| Adotar LongMemEval / protocolo de Maharana et al. diretamente | Medem memória factual, não coerência de persona. **Herdar a estrutura do protocolo e citar a origem**, sem alegar uso do benchmark |
| Métricas só automáticas | Similaridade de embedding não distingue persona de tópico; a rubrica humana é o controle de construto |
| Só avaliação qualitativa | Não sustenta comparação entre três braços nem dá matriz de confusão |
| Definir métricas após ver os primeiros resultados | Pré-registro é o que separa DSR de justificativa retroativa |

## Consequências

**Positivas**
- A comparação B vs C dá ao trabalho um resultado que significa alguma coisa.
- Critérios 1 e 3 deixam de se canibalizar.
- Pré-registro em commit datado é defesa objetiva contra a acusação de ajustar a métrica ao resultado.
- O plano B do critério 4 protege o cronograma de um bloqueio institucional.

**Negativas**
- Três braços = ~50% mais execução e mais tempo de coleta.
- Personas roteirizadas dão trabalho de projetar e precisam ser validadas antes.
- Pré-registro remove a liberdade de "achar a métrica que funciona" — que é exatamente o ponto.

**Riscos**
- As sondas de estilo podem capturar tópico em vez de persona. **Mitigação:** piloto com 2–3 sondas
  antes de fixar o conjunto; se respostas de personas diferentes à mesma sonda não se separarem, a
  sonda não serve.
- n pequeno no critério 4 pode não sustentar nenhuma leitura. Aceito e declarado como limitação
  desde já, não descoberto na escrita.
