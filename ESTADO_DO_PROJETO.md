# Cain — Documento Mestre

> **Fonte da verdade única.** Este documento consolida e **substitui** os três anteriores:
> `tcc-cain-base.md` (v0, sessão inicial), `cain_esbozo_v1.md` (v1, esboço conceitual) e
> `ESTADO_DO_PROJETO.md` (v2, documento de continuidade).
> Os três originais devem ser arquivados em `docs/historico/`, não deletados — o rastro de
> evolução é ele próprio um artefato de pesquisa em DSR.
>
> **Versão:** 3.2 · **Última atualização:** 2026-09-07
> **Uso:** versionar em `ESTADO_DO_PROJETO.md` no repo e/ou colar no card "Conhecimento do Projeto".

## Como ler as marcações

| Marca | Significado | O que fazer |
|---|---|---|
| `✔ RESOLVIDO` | Conflito entre documentos, decidido. O argumento fica registrado. | Nada — é decisão fechada. |
| `🔧 CORRIGIDO` | Erro factual ou de atribuição encontrado e corrigido. | Conferir e remover a marca. |
| `✅ PREENCHIDO` | Lacuna completada por inferência. | **Auditar.** Aceitar, ajustar ou remover. |
| `🔎 A VALIDAR` | Depende de informação externa (instituição, orientador). | Levantar e fechar. |

**Estado da v3.1:** os cinco conflitos entre documentos estão resolvidos e os ADRs 0009–0011 estão
escritos. Restam **duas pendências externas** — instituição/orientador (§12.1) e comitê de ética
(§12.2). Ambas são ligação telefônica, não trabalho intelectual, e ambas estão no caminho crítico.

O **Anexo A** lista todas as marcações em uma tabela só, para auditoria rápida.

---

# 1. Identificação

| Campo | Valor |
|---|---|
| **Codinome** | Cain |
| **Título acadêmico formal** | *Arquitetura para Identidade Persistente em Sistemas Multiagente baseados em LLM* |
| **Natureza** | TCC em Sistemas de Informação + projeto de software de longo prazo |
| **Autor** | Leo — Sistemas de Informação, Paraná, Brasil |
| **Perfil técnico** | DevSecOps / CI-CD; GitHub Actions, .NET, FastAPI, Python |
| **Idioma de trabalho** | Português brasileiro, tom direto |
| **Instituição de matrícula** | 🔎 **A VALIDAR** — ver §12.1 |
| **Orientador** | Não definido — **bloqueio crítico** |
| **Fase atual** | Fundamentação (revisão de literatura) |

**Origem do codinome:** inspirado no personagem de *The Amazing Digital Circus* — o host que controla
o ambiente digital, delega aos "personagens" (agentes) e mantém identidade forte e reconhecível.

O codinome fica **separado do título acadêmico** e não entra no texto formal do TCC exceto como nome
do artefato.

🔧 **CORRIGIDO** — havia três títulos diferentes circulando. Canonizei o do `ESTADO_DO_PROJETO`
(mais preciso: nomeia *sistemas multiagente*, que é o campo onde o gap existe). Descartados:
*"Arquitetura de Agente Orquestrador com Identidade Persistente baseado em LLM"* e a variante
"Tema" do esboço.

---

# 2. Ambição e diretrizes

O Cain **não é um entregável descartável de TCC**. Diretrizes aceitas como consequência:

- Versionamento público no GitHub desde o dia zero — o histórico de pesquisa é visível e datado.
- Arquitetura modular real: LLM e agentes trocáveis por configuração, não por refatoração.
- Documentação como artefato de pesquisa (ADRs).
- Problema formulado de modo **model-agnostic**, para sobreviver à obsolescência tecnológica.
- Avaliação reprodutível.
- Continuidade planejada: publicação (ENIAC, BRACIS) e possível mestrado.

---

# 3. Definição de pesquisa

## 3.1 Problema

Agentes baseados em LLM perdem coerência comportamental ao longo do tempo e entre sessões. O campo
se divide em duas famílias que não conversam:

- **Sistemas de orquestração multiagente** (AutoGen, LangChain, CrewAI) coordenam bem, mas tratam
  identidade como secundária — a persona é um *system prompt* solto.
- **Sistemas de persona** (Character.AI, assistentes conversacionais) mantêm identidade, mas não
  orquestram agentes heterogêneos.

Quando alguém tenta combinar os dois, a identidade se degrada conforme a complexidade da orquestração
aumenta.

✅ **PREENCHIDO — base empírica do problema.** Os três documentos afirmavam o problema sem evidência
citável. Ela existe e é forte:

- Choi et al. (2024) mediram *identity drift* em nove LLMs em conversas multi-turno e encontraram
  três resultados relevantes: modelos maiores derivam **mais**, não menos; a diferença entre famílias
  de modelo é menor que o efeito do tamanho; e — o achado que sustenta o Cain inteiro —
  **atribuir uma persona via prompt não é suficiente para manter a identidade.**
- Li et al. (2024) demonstraram degradação de estabilidade de instrução em ~8 rodadas de auto-diálogo
  em LLaMA-2-70B.

O segundo achado de Choi et al. é a sua justificativa central: se prompt resolvesse, o Cain não
precisaria existir. **Priorize essa leitura.**

## 3.2 Questão de pesquisa

> Como projetar um orquestrador baseado em LLM com identidade persistente que coordene agentes
> heterogêneos (de IA e não-IA) e se adapte ao perfil do usuário ao longo do tempo, **sem recorrer a
> fine-tuning**?

## 3.3 Objetivo geral

Projetar, construir e avaliar uma arquitetura de orquestração multiagente com identidade adaptativa
persistente, resolvida por **arquitetura** e não por ajuste de pesos.

✔ **RESOLVIDO — "maximizar a satisfação do usuário" fica fora do objetivo geral.**

O esboço v1 tinha a cláusula; o `ESTADO_DO_PROJETO` a derrubou mas manteve o critério nº 4, que ficou
órfão. Satisfação permanece apenas como critério **secundário** (§6.1). Razão: um objetivo que manda
maximizar satisfação transforma sycophancy em alvo de otimização, e satisfação é a medição mais
frágil do conjunto (n pequeno, refém do CEP) — apoiar o objetivo geral nela é descasamento
estrutural. §6.4 permanece integralmente: adaptação ao perfil já produz o risco sem a palavra.

## 3.4 Objetivos específicos (proposta canônica)

✔ **RESOLVIDO — lista canônica de 5 objetivos.** Havia três listas incompatíveis (6 itens na base,
5 no esboço, 4 no ESTADO). Esta preserva o que cada uma tinha de melhor e é a única válida.

| # | Objetivo | Origem |
|---|---|---|
| **OE1** | Revisar a literatura sobre agentes baseados em LLM, orquestração multiagente e persistência de identidade, delimitando a lacuna de pesquisa. | base + esboço (o ESTADO tinha derrubado — recuperei) |
| **OE2** | Definir um modelo operacional de identidade persistente para agentes orquestradores, tornando *coerência comportamental* mensurável. | esboço OE2 + ESTADO |
| **OE3** | Projetar a arquitetura do Cain — camadas, componentes, contratos e fluxo — fundamentada em DSR. | consenso dos três |
| **OE4** | Implementar um protótipo funcional em Python integrando três agentes (Busca, Código, Resumo) sob orquestrador com camada de identidade. | consenso dos três |
| **OE5** | Avaliar o protótipo segundo os critérios definidos, **comparando-o a um baseline sem camada de identidade**. | ESTADO (fundiu avaliação + comparação — mantive fundido) |

Nota sobre o que ficou de fora: a base listava "Documentar e publicar resultados" como OE. Não é
objetivo específico de pesquisa — é a fase 6 do DSR e a existência do próprio TCC. Removido como OE,
preservado no roadmap.

**Atenção ao OE2.** Ele deixou de ser decorativo. É onde a separação `PersonalityState` /
`UserModel` vira definição operacional, e é o que torna a tensão coerência × adaptação (§6.3)
resolvível em vez de fatal. Trate-o como entregável real com produto verificável — as definições
operacionais escritas e o conjunto de sondas do ADR-0010 — e não como "definir conceitos".

## 3.5 Delimitação de escopo (blindagem de banca)

**O Cain não faz e o TCC não promete:**

- Fine-tuning, treinamento ou ajuste de pesos de qualquer modelo.
- Proposta de um novo LLM.
- Estado da arte em tarefas individuais (os agentes são meio, não fim).
- Produto comercial; UX/UI além do mínimo funcional.
- Segurança, privacidade ou governança como objeto de pesquisa.
- Avaliação de produção: latência, custo sob carga, escala.
- Generalização empírica para N agentes arbitrários — o protótipo é restrito a 3.

✔ **RESOLVIDO — genericidade é propriedade de design demonstrável, não generalização reivindicada.**

O esboço usava genericidade como justificativa central; o `ESTADO_DO_PROJETO` a excluía do escopo.
Se justifica o trabalho mas não é avaliada, a banca abre exatamente aí. Redação canônica para a
justificativa:

> A extensibilidade é uma **propriedade de design demonstrável**, não uma **generalização empírica
> reivindicada**. Demonstra-se que o contrato de agente (`handle` + `describe`) permite plugar um
> novo agente sem alterar o núcleo. **Não** se reivindica eficácia comprovada em N domínios.

**Artefato que sustenta:** `tests/integration/test_plug_new_agent.py`. Meia hora de trabalho, e
converte a alegação em teste executável — a pergunta da banca vira demonstração de dois minutos.

---

# 4. Metodologia

## 4.1 Design Science Research

🔧 **CORRIGIDO — atribuição errada nos três documentos.**

Os três atribuíam as **seis fases** do processo a Hevner et al. (2004). Está errado, e é o tipo de
erro que um avaliador que conhece DSR pega na hora:

- **Hevner et al. (2004)**, *MIS Quarterly* — propõe **sete diretrizes** de rigor e relevância para
  DSR em SI, e o framework de três ciclos (relevância, design, rigor). Não é um modelo de processo
  em fases.
- **Peffers et al. (2007)**, *Journal of Management Information Systems* — propõe a **DSRM**, o
  modelo de processo com as **seis atividades** que você está usando: identificação do problema,
  definição dos objetivos da solução, design e desenvolvimento, demonstração, avaliação, comunicação.

Cite os dois, com papéis distintos: **Peffers dá o processo; Hevner dá os critérios de rigor.**
Ambos são canônicos e as duas obras são as mais citadas do campo.

## 4.2 Fases (Peffers et al., 2007) — estado atual

```
DSRM
├── 1. Identificação do problema      ✅  gap: orquestração vs. identidade
├── 2. Objetivos da solução           ✅  o que o Cain precisa fazer
├── 3. Design e desenvolvimento       🔄  esqueleto fechado; 3 peças provisórias
├── 4. Demonstração                   ⬜  protótipo rodando nos cenários
├── 5. Avaliação                      ⬜  Cain vs. baseline
└── 6. Comunicação                    ⬜  o TCC e a eventual publicação
```

## 4.3 Alinhamento com as diretrizes de Hevner (✅ PREENCHIDO)

Tabela ausente nos três documentos. É barata de escrever e desarma metade das perguntas de
qualificação. Preencha a coluna da direita conforme avançar.

| # | Diretriz (Hevner et al., 2004) | Como o Cain atende |
|---|---|---|
| 1 | Design como artefato | Arquitetura + protótipo funcional versionado |
| 2 | Relevância do problema | *Identity drift* documentado empiricamente (Choi et al., 2024) |
| 3 | Avaliação do design | Comparação controlada contra baseline, em ≥3 sessões |
| 4 | Contribuição de pesquisa | A arquitetura em si + os ADRs de faixa B |
| 5 | Rigor da pesquisa | DSRM como processo; métricas fixadas em ADR **antes** da execução |
| 6 | Design como processo de busca | ADRs registram alternativas descartadas e o porquê |
| 7 | Comunicação | TCC + repositório público + eventual paper |

A diretriz 6 é a que o seu método de ADR já atende melhor que a média dos TCCs — **explore isso na
qualificação.** Registrar alternativas descartadas é literalmente o que Hevner pede e quase ninguém
faz.

---

# 5. Arquitetura

Três camadas + uma abstração de LLM transversal. O **esqueleto está fechado** (caixas, fronteiras,
contratos, fluxo). Três peças internas são **provisórias**, pendentes de revisão de literatura.

## 5.1 Visão em camadas

```
┌─────────────────────────────────────────────┐
│                  USUÁRIO                    │
│   input · feedback implícito · preferências │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│                 CAIN CORE                   │
│  ┌──────────────┐   ┌───────────────────┐   │
│  │  Identidade  │   │   Orquestrador    │   │
│  │  (memória)   │   │ planejar + delegar│   │
│  └──────────────┘   └─────────┬─────────┘   │
│  ┌────────────────────────────▼──────────┐  │
│  │            Aprendizado                │  │
│  │  atualiza perfil · persiste sessões   │  │
│  └───────────────────────────────────────┘  │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│        CAMADA DE PROVIDERS (a tomada)       │
│  LLM | Memória | Vetorial | Infra           │
│  abstração por interface — plugável         │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│           REGISTRY DE AGENTES               │
│  Busca | Código | Resumo | (extensível)     │
│  heterogêneos · plugáveis · independentes   │
└─────────────────────────────────────────────┘
```

## 5.2 Camada 1 — Identidade / Memória (`src/cain/identity/`)

| Componente | Função | Status |
|---|---|---|
| Serviço de Identidade | Leitura/escrita da persona | **firme** |
| Injetor de Contexto | Monta o prompt-base com a identidade | **firme** |
| Modelo de Identidade | O que compõe a persona | **provisório — ADR-0006** |
| Mecanismo de Adaptação | Como a persona evolui | **provisório — ADR-0007** |

**Contrato:** `Identity.get(user_id)` · `Identity.update(user_id, sinal)` · `Identity.as_context()`

### Modelo de identidade — dois vetores (provisório)

O esboço v1 propunha dois vetores que persistem entre sessões e evoluem com o uso. Preservado aqui
como **ponto de partida do ADR-0006**, não como decisão fechada:

```python
UserModel = {          # Vetor 1 — quem o usuário é
    "preferencias_comunicacao": "direto, técnico, sem rodeios",
    "historico_tarefas": [...],
    "dominio_de_expertise": "DevSecOps",
    "objetivos_recorrentes": [...],
    "feedback_implicito": [...],
}

PersonalityState = {   # Vetor 2 — como o Cain responde
    "tom": "ajustado ao usuário",
    "proatividade": 0.7,
    "verbosidade": 0.3,
    "estilo_de_erro": "direto + solução",
}
```

🔎 **A VALIDAR — este é o ponto onde a literatura mais te ajuda e mais te ameaça.** Ver §9.3: existe
uma linha inteira de trabalho recente sobre memória de agentes (MemGPT, MemoryBank, Mem0, Zep,
MemOS) que precisa ser confrontada antes de fechar o ADR-0006. Fechar esse ADR sem ler esses
trabalhos é assumir risco desnecessário de reinventar algo que já tem nome.

## 5.3 Camada 2 — Orquestração (`src/cain/orchestrator/`)

| Componente | Função | Status |
|---|---|---|
| Gerenciador de Sessão | Ciclo de vida da interação | **firme** |
| Mediador | Combina respostas de múltiplos agentes | **firme** |
| Logger de Decisões | Rastreabilidade para avaliação | **firme** |
| Roteador | Decide qual agente atende | **provisório — ADR-0008** |

**Contrato de mensagem:** `{ intent, contexto_identidade, payload, metadata }`

### Onde fica a inteligência do planejamento (entra no ADR-0008)

| Opção | Como funciona | Prós | Contras |
|---|---|---|---|
| LLM decide | O modelo escolhe agentes em tempo real | flexível, natural | imprevisível, caro, difícil de avaliar |
| **Regras + LLM** | Regras fixas; LLM só nos casos difíceis | controlado, auditável, barato | menos dinâmico |

**Recomendação (do esboço, mantida):** a segunda. Não é só "mais fácil de explicar para a banca" —
é a única das duas em que o critério "precisão de delegação" tem *ground truth* definível. Se o LLM
decide livremente, você não tem contra o quê medir a taxa de roteamento correto. **A escolha
arquitetural e a viabilidade da avaliação estão acopladas aqui**, e nenhum dos três documentos
notou isso. Registre esse argumento no ADR-0008; é o mais forte que você tem.

O mesmo argumento sustenta a decisão de não usar framework de terceiros (ADR-0011): adotar o
roteador de um framework reintroduziria a opacidade que esta decisão elimina. **Os dois ADRs são a
mesma decisão vista de dois ângulos** — cite um no outro.

## 5.4 Camada 3 — Registro de Agentes (`src/cain/agents/`)

**Contrato:** `handle(mensagem) -> resposta` + `describe() -> capabilities` — **firme**

| Agente | O que faz | Por que ele está aqui |
|---|---|---|
| **Busca** | Recupera informação | Prova que o Cain sabe *onde buscar* |
| **Código** | Gera ou analisa código | Prova que o Cain sabe *o que fazer* com o resultado |
| **Resumo** | Condensa texto longo | Prova que o Cain sabe *como entregar* ao usuário |

Os três cobrem um ciclo funcional completo (recuperar → processar → entregar) e criam a superfície
onde a adaptação de identidade fica observável: o mesmo pedido, de dois usuários com perfis
diferentes, deve produzir entregas formatadas de modo distinto. **Escolha deliberada, não
arbitrária** — e essa frase precisa estar no texto do TCC.

## 5.5 Transversal — Abstração de LLM (`src/cain/llm/`)

Princípio: **o Cain não chama o Ollama. O Cain chama "um LLM". Qual, é configuração.**

- Contrato: `generate(prompt, context) -> response` — **firme**
- Adaptador Ollama (local, custo zero, desenvolvimento) — **firme**
- Adaptador API (provedores comerciais, escala) — **firme**
- Nenhuma outra camada conhece o provedor concreto.

## 5.6 Fluxo de uma requisição

1. **Usuário → Orquestrador** — entrada recebida, sessão registrada.
2. **Orquestrador → Identidade** — carrega persona (`get` + `as_context`).
3. **[provisório]** Roteador decide o agente.
4. **Orquestrador → Agente** — delega com `{ intent, contexto_identidade, payload, metadata }`.
5. **Agente → LLM** (via abstração) — processa com contexto + especialização.
6. **Mediador** consolida; **Logger** registra.
7. **[provisório]** Mecanismo de Adaptação pode atualizar a identidade (`update`).
8. **Orquestrador → Usuário** — resposta entregue; estado pronto para a próxima sessão.

---

# 6. Avaliação

## 6.1 Critérios (fechados)

| # | Critério | O que mede |
|---|---|---|
| 1 | Coerência de identidade entre sessões | A persona se mantém? |
| 2 | Precisão de delegação | O agente certo foi acionado? |
| 3 | Adaptação ao perfil | O perfil evoluiu com o uso? |
| 4 | Satisfação percebida | O usuário aprovou? — **secundário**, ver abaixo |

**Status do critério 4 após §3.3.** Com a saída da cláusula de satisfação do objetivo geral, o
critério 4 é **secundário e indicativo**: ele não sustenta a conclusão do trabalho, e nenhum
resultado principal depende dele. Justifica-se por complementar os critérios 1–3 com percepção
humana — coerência e delegação podem ir bem em métrica automática e ainda produzir uma interação
ruim, e isso vale registrar. É também o único critério condicionado a aprovação externa (§12.2), e
o ADR-0010 já fixa o plano substituto caso ela não venha.

## 6.2 Plano — três braços

| Braço | Descrição | O que a comparação isola |
|---|---|---|
| **A — Baseline** | LLM + system prompt estático | — |
| **B — Controle pareado por contexto** | Transcritos brutos, mesmo orçamento de tokens, sem estrutura | A vs B: efeito de ter memória |
| **C — Cain** | Identidade estruturada + roteamento + mediação | **B vs C: efeito da estrutura** |

A vs C prova que *alguma coisa* ajuda. **B vs C sustenta a tese**, separando a contribuição
arquitetural do efeito trivial de ter mais contexto — é a resposta à ameaça de validade interna
(§6.5). Amostra: 5–10 cenários × 3 braços × ≥3 sessões.

→ **Métricas por critério, controles de execução, plano substituto do critério 4 e regras de
descarte: ADR-0010** (normativo).

## 6.3 Definições operacionais a fechar

Os documentos anteriores listavam isso como pendência sem propor nada. Deixo pontos de partida
(✅ **PREENCHIDO** — são propostas, não decisões):

**"Coerência comportamental"** — estabilidade mensurável de traços observáveis da resposta (tom,
verbosidade, estrutura, estilo de tratamento de erro) entre respostas a estímulos equivalentes em
sessões distintas, com o conteúdo factual controlado. Operacionalizável como distância entre
embeddings de resposta + rubrica qualitativa aplicada por avaliador cego.

**"Identidade adaptativa persistente"** — a conjunção de duas propriedades que puxam em direções
opostas e por isso precisam ser medidas separadamente:
- *Persistência:* o perfil sobrevive ao fim da sessão e é recuperado na seguinte.
- *Adaptatividade:* o perfil muda em resposta a sinais do usuário.

✔ **RESOLVIDO — a tensão entre os critérios 1 e 3 se resolve separando as superfícies.**

Um sistema que adapta muito é incoerente; um que persiste demais não adapta. Medidos sobre a mesma
superfície, os critérios se canibalizam e o resultado não significa nada. **Decisão:** o
`PersonalityState` é estável e é o que o critério 1 mede; o `UserModel` evolui e é o que o critério 3
mede. Os conjuntos de sondas são **disjuntos** — a separação vale no nível da métrica, não só no
conceito, ou a canibalização volta pela porta dos fundos.

→ Operacionalização em **ADR-0010**; modelo que a sustenta em **ADR-0006**.
*Alternativa descartada:* reportar o trade-off como curva — registrado como trabalho futuro.

## 6.4 Limitações éticas (seção obrigatória do TCC)

Preservada do esboço v1 e ampliada. Vai no texto final, não é rascunho:

- **Sycophancy.** Um agente que adapta comportamento para agradar tende a concordar mais, discordar
  menos e reforçar o que o usuário já pensa. Se "satisfação percebida" é critério de avaliação, o
  sistema é *literalmente otimizado* na direção desse risco. Reconhecer isso e discutir mitigação
  (ex.: medir se a taxa de discordância cai ao longo das sessões) é diferencial acadêmico, não
  fraqueza.
- **Perfilamento.** O `UserModel` é um perfil de usuário construído por inferência, incluindo
  feedback implícito que o usuário não sabe que está dando. Mesmo fora do escopo de pesquisa,
  privacidade precisa de um parágrafo honesto.
- **Ilusão de relacionamento.** Identidade persistente entre sessões é exatamente o mecanismo que
  faz sistemas conversacionais parecerem mais próximos do que são. Vale um parágrafo.

## 6.5 Ameaças à validade (✅ PREENCHIDO — seção ausente nos três)

Em DSR isso é cobrado. Escreva agora, não na semana da defesa:

| Ameaça | Descrição | Mitigação |
|---|---|---|
| **Construto** | "Coerência" medida por similaridade de embedding pode capturar similaridade de tópico, não de persona. | Controlar o conteúdo factual entre estímulos; combinar com rubrica humana. |
| **Interna** | Ganho atribuído à camada de identidade pode vir só do contexto adicional no prompt. | Baseline recebe **o mesmo volume de contexto**, sem estrutura de identidade. Sem isso, o experimento não prova nada. |
| **Externa** | Um único LLM local, três agentes, poucos usuários. | Não reivindicar generalização (§3.5). Rodar, se der, com dois modelos de tamanhos diferentes. |
| **Conclusão** | n pequeno no questionário de satisfação; sem poder estatístico. | Reportar como indicativo e qualitativo. Não aplicar teste de significância em n=5. |
| **Viés do avaliador** | Você é autor, implementador e avaliador. | Avaliação pareada cega; ordem randomizada; rubrica escrita **antes** de ver os resultados. |

A ameaça interna é a mais séria. **Se o baseline receber menos contexto que o Cain, o resultado é
inválido e um avaliador atento derruba o experimento inteiro.** Escreva isso no ADR-0010.

---

# 7. Stack, persistência e custos

## 7.1 Stack

| Componente | Tecnologia |
|---|---|
| Linguagem | Python |
| IDE | VS Code |
| LLM local | Ollama |
| Backend / API | FastAPI |
| Memória relacional | SQLite |
| Memória vetorial | ChromaDB |
| Orquestração | Implementação própria, escopo restrito — **ADR-0011** |
| Versionamento | Git + GitHub (público desde o início) |
| CI/CD | GitHub Actions |

✔ **RESOLVIDO — implementação própria, escopo restrito. → ADR-0011** (normativo).

Não era detalhe de stack: define o tamanho da contribuição. O argumento decisivo é de
**instrumentação** — o critério 2 exige *ground truth* de roteamento e o `DecisionLog` precisa
registrar por que cada delegação ocorreu; roteador de framework é opaco nesse ponto. Mesmo argumento
do ADR-0008, visto de outro ângulo.

O que segura o cronograma é a **lista normativa de exclusões** do ADR-0011 (sem paralelismo, sem
conversação agente-a-agente, sem criação dinâmica, sem retry, sem grafos, sem streaming). AutoGen
permanece como referência da 2.2, nunca como dependência.

## 7.2 Persistência — escalonamento progressivo

| Camada | Fase TCC | Escala |
|---|---|---|
| Relacional | SQLite | PostgreSQL / Supabase |
| Vetorial | ChromaDB local | Pinecone / Weaviate |
| LLM | Ollama local | GPT / Claude / Llama Cloud |
| Infra | Máquina local | Oracle Free → VPS → Cloud |

Tudo atrás de abstração de provedor — nenhuma camada superior conhece o backend concreto.

## 7.3 Custos

| Fase | Stack | Custo |
|---|---|---|
| Esboço | Só raciocínio | $0 |
| Protótipo (TCC) | Ollama local + SQLite + VS Code | $0 |
| Avaliação | Testes com modelo comercial pequeno (opcional) | $0–10 |
| Defesa | Oracle Free Tier ou máquina local | $0 |
| Iniciação científica | Modelo comercial + PostgreSQL + VPS | $0–50/mês |
| Publicação | Modelo avaliado + Supabase | $50–200/mês |
| Produto | Multi-LLM + cloud + multiusuário | $200+/mês |

O TCC inteiro cabe em custo zero. Isso é uma decisão de design, não sorte — e vale uma frase na
metodologia sobre reprodutibilidade: **qualquer pessoa consegue rodar seu experimento sem pagar
nada**, o que é um ponto forte de reprodutibilidade que quase nenhum trabalho com LLM comercial tem.

---

# 8. Registro de decisões (ADRs)

**Faixa A** = engenharia (firme, não é contribuição de pesquisa).
**Faixa B** = contribuição de pesquisa (provisória, pendente de literatura).

| ADR | Título | Faixa | Status |
|---|---|---|---|
| 0001 | Adotar ADRs e tratar o repo como artefato de pesquisa | — | Aceito |
| 0002 | Desacoplar a arquitetura de qualquer LLM específico | — | Aceito |
| 0003 | Contrato de mensagem entre camadas | A | Aceito |
| 0004 | Contrato comum de agente | A | Aceito |
| 0005 | Fronteira da abstração de LLM | A | Aceito |
| 0006 | Modelo de dados da identidade | B | Provisório |
| 0007 | Mecanismo de adaptação da identidade | B | Provisório |
| 0008 | Estratégia de roteamento do orquestrador | B | Provisório |
| **0009** | **Fronteira da abstração de persistência** | **A** | **Aceito** |
| **0010** | **Protocolo e métricas de avaliação** | **B** | **Proposto** — ver nota |
| **0011** | **Orquestração própria vs. framework existente** | **B** | **Aceito** |

Textos completos em `docs/adr/`.

> **O ADR-0010 está Proposto, não Aceito**, porque depende da resposta sobre comitê de ética (§12.2)
> e da validação do orientador. Precisa estar **Aceito antes da primeira coleta de dados** — fixar
> métrica depois de ver resultado é o modo mais comum de invalidar um trabalho de DSR sem perceber.

**Por que os três novos:**

- **0009** — o ESTADO dizia "atrás de uma abstração de provedor" sem ADR. A fronteira LLM tem ADR
  (0005), a de storage não tinha. Assimetria sem motivo.
- **0010** — o próprio documento anterior identificou que "transformar critérios em métricas
  concretas é o ponto que trava qualificação de DSR" e mesmo assim não abriu ADR para isso. É o ADR
  mais importante da lista e não existia. Ele deve conter também o controle de contexto do baseline
  (§6.5) e a rubrica escrita antes da coleta.
- **0011** — resolve o conflito de §7.1, que estava atravessado entre dois documentos.

**Nota:** a base v0 tinha uma numeração diferente (`ADR-001` a `ADR-005`, três dígitos, mapeamento
distinto). Descartada em favor da numeração de quatro dígitos do repositório, que já tem os textos
escritos. Se algum conteúdo da lista antiga não foi absorvido — especificamente *"escolha do LLM
local"* — ele cabe como seção dentro do 0002, não como ADR próprio.

---

# 9. Referencial teórico (Capítulo 2)

## 9.1 Estrutura

Lógica: do conceito geral até o gap que o Cain preenche.

| Seção | Conteúdo | Papel |
|---|---|---|
| **2.1** | Agentes baseados em LLM | Estabelece vocabulário |
| **2.2** | Sistemas multiagente e orquestração | *"orquestra bem, trata identidade como secundária"* — **primeira frente a desenvolver** |
| **2.3** | Identidade e persona em LLMs | *"tem identidade, não orquestra"* — par espelhado com 2.2 |
| **2.4** | Coerência comportamental e memória de longo prazo | O problema central; por que fine-tuning não resolve |
| **2.5** | Design Science Research | Fundamenta a metodologia |
| **2.6** | Síntese e lacuna de pesquisa | Costura tudo — **a seção mais importante para a banca** |

## 9.2 Bibliografia validada

🔧 **CORRIGIDO** — todos os títulos e veículos foram conferidos. Havia quatro erros nos documentos
originais (marcados abaixo). Os DOIs ainda precisam ser colados um a um no formato ABNT da sua
instituição, mas as referências em si estão corretas.

### Metodologia

| Referência | Papel | Seção |
|---|---|---|
| **Peffers, K. et al. (2007).** *A Design Science Research Methodology for Information Systems Research.* Journal of Management Information Systems, 24(3), 45–77. | Modelo de processo (as 6 atividades) 🔧 | 2.5 |
| **Hevner, A. R. et al. (2004).** *Design Science in Information Systems Research.* MIS Quarterly, 28(1), 75–105. | Diretrizes de rigor (as 7) e três ciclos | 2.5 |

### Agentes e orquestração

| Referência | Papel | Seção |
|---|---|---|
| **Wang, L. et al. (2024).** *A Survey on Large Language Model based Autonomous Agents.* Frontiers of Computer Science, 18(6). | Panorama do campo — âncora da 2.1 🔧 *(a base citava como arXiv 2023; é o mesmo trabalho, cite a versão em periódico)* | 2.1 |
| **Xi, Z. et al. (2025).** *The rise and potential of large language model based agents: a survey.* Science China Information Sciences, 68(2), 121101. | Survey complementar; framework cérebro/percepção/ação 🔧 *(era citado como arXiv 2023 — saiu em periódico, use a versão publicada)* | 2.1 |
| **Yao, S. et al. (2023).** *ReAct: Synergizing Reasoning and Acting in Language Models.* ICLR. | Base de raciocínio + ação 🔧 *(o esboço trazia o título errado: "Reasoning and Acting in LLMs")* | 2.1 |
| **Wu, Q. et al. (2023).** *AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation.* | Framework multiagente — **concorrente direto**, precisa ser confrontado 🔧 *(título estava incompleto)* | 2.2 |

### Identidade, persona e o problema central

| Referência | Papel | Seção |
|---|---|---|
| **Park, J. S. et al. (2023).** *Generative Agents: Interactive Simulacra of Human Behavior.* ACM UIST. | Agentes com memória e comportamento persistente | 2.3 |
| **Choi, J. et al. (2024).** *Examining Identity Drift in Conversations of LLM Agents.* arXiv:2412.00804. | ✅ **A referência mais importante da lista.** Evidência empírica de identity drift em 9 LLMs; mostra que persona via prompt não basta | **2.4** |
| **Li, K. et al. (2024).** *Measuring and Controlling Instruction (In)Stability in Language Model Dialogs.* arXiv:2402.10962. | Método de medição de drift + evidência de degradação em ~8 turnos | **2.4** |

### Memória de longo prazo (✅ PREENCHIDO — frente inteira ausente)

| Referência | Papel | Seção |
|---|---|---|
| **Packer, C. et al. (2023).** *MemGPT: Towards LLMs as Operating Systems.* arXiv:2310.08560. | Gerenciamento de contexto virtual; referência fundadora da linha | 2.4 |
| **Zhong, W. et al. (2024).** *MemoryBank: Enhancing Large Language Models with Long-Term Memory.* AAAI, 38. | Memória de longo prazo com mecanismo de esquecimento | 2.4 |
| **Maharana, A. et al. (2024).** *Evaluating Very Long-Term Conversational Memory of LLM Agents.* ACL 2024, 13851–13870. | **Protocolo de avaliação** de memória de longo prazo | 2.4 / metodologia |
| **Wu, D. et al. (2024).** *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory.* ICLR 2025. | **Benchmark existente** — ver §9.4 | 2.4 / metodologia |

## 9.3 🔎 Risco de novidade — leia isto antes de fechar o Capítulo 2

Um levantamento rápido mostra que a linha de **memória persistente para agentes** cresceu muito
desde 2023: além de MemGPT e MemoryBank, existem Mem0, Zep, MemOS, A-Mem, e pelo menos um survey
dedicado ao tema. Nenhum dos três documentos mencionava essa frente.

Duas consequências, e as duas importam:

1. **Ameaça.** Se a sua contribuição for lida como "sistema de memória para agentes", ela já tem
   concorrência densa e bem financiada. A 2.6 tem que deixar claro que o Cain **não é um sistema de
   memória** — é uma arquitetura de orquestração *cuja camada de identidade* usa memória como meio.
   O objeto é a coordenação entre identidade e delegação. Essa distinção é a sua sobrevivência
   argumentativa e precisa estar escrita com todas as letras.
2. **Oportunidade.** Esses trabalhos já resolveram problemas que você teria que resolver do zero no
   ADR-0006. Ler antes de projetar economiza semanas.

## 9.4 ✅ Benchmarks existentes — atalho para o seu maior risco

O `ESTADO_DO_PROJETO` registrava, corretamente, que transformar critérios em métricas concretas é
onde DSR costuma travar na qualificação. Existe atalho: **LongMemEval** (ICLR 2025) e o protocolo de
Maharana et al. (ACL 2024) já são instrumentos publicados e revisados por pares para avaliar memória
de longo prazo em assistentes.

Adaptar um instrumento existente é **mais defensável** do que inventar métrica própria, e resolve
metade do ADR-0010. Você provavelmente não vai conseguir usar nenhum dos dois direto — eles medem
memória factual, não coerência de persona — mas herdar a estrutura do protocolo e citar a origem é
muito mais forte que partir do zero. Avalie na revisão.

## 9.5 Conceitos-chave para a busca bibliográfica

`multi-agent systems (MAS)` · `LLM orchestration` · `persistent identity in LLMs` · `persona drift` ·
`identity drift` · `user-adaptive agents` · `implicit feedback learning` · `pluggable agent
architecture` · `long-term agent memory` · `behavioral consistency` · `sycophancy in LLMs`

✅ Os quatro últimos foram acrescentados — `persona drift` e `identity drift` em especial são os
termos que realmente indexam a literatura do seu problema central. Sem eles, a 2.4 sai vazia.

---

# 10. Roadmap

✅ **PREENCHIDO** — o `ESTADO_DO_PROJETO` tinha derrubado o roadmap da base v0. Recuperado e
reancorado em datas reais.

| Fase | Período | Entregas | Marco |
|---|---|---|---|
| **1. Fundamentação** | Set–Dez 2026 | Revisão de literatura (2.2 → 2.4 → 2.3 → 2.6); ADRs 0006–0008 fechados; **orientador definido** | Capítulo 2 escrito |
| **2. Design formal** | Jan–Mar 2027 | Arquitetura formalizada; ADRs 0009–0011; protocolo de avaliação fechado | **Qualificação** |
| **3. Implementação** | Abr–Jul 2027 | Cain v1 funcional; três agentes; baseline implementado | Protótipo demonstrável |
| **4. Avaliação** | Ago–Set 2027 | Execução dos cenários; coleta; análise | Resultados |
| **5. Escrita e defesa** | Out–Dez 2027 | TCC completo; **defesa** | Entrega |

🔎 **A VALIDAR** — as datas são inferência minha a partir de uma graduação prevista para dezembro de
2027. **O calendário oficial de TCC da sua instituição manda**, e datas de qualificação e defesa
costumam ser fixas e inegociáveis. Levante isso e reancore. É informação de cinco minutos que
reorganiza o resto.

**Riscos de cronograma:**

- A fase 1 depende do orientador, que é bloqueio externo. Se escorregar dois meses, a fase 3 come a
  4. **Comece a implementação do esqueleto em paralelo à revisão** — o esqueleto já está fechado e
  não depende dos ADRs provisórios. É o hedge óbvio e você já tem o repo montado para isso.
- Se a avaliação com pessoas exigir comitê de ética (§12.2), some 2–4 meses ao caminho crítico.
  Descobrir isso em julho de 2027 seria fatal.

---

# 11. Estrutura do repositório

Monorepo tratado como artefato de pesquisa. Já criado e empacotado.

```
cain/
├── README.md · LICENSE (MIT) · CONTRIBUTING.md · SETUP_GITHUB.md
├── ESTADO_DO_PROJETO.md        (este documento)
├── pyproject.toml · .gitignore · .github/workflows/ci.yml
├── docs/
│   ├── adr/                    (0001–0011 + template + índice)
│   ├── architecture/           (overview.md + diagramas HTML)
│   ├── research/               (revisão, metodologia, avaliação)
│   └── historico/              ✅ (os três documentos originais, arquivados)
├── src/cain/                   (identity · orchestrator · agents · llm · common)
├── tests/                      (unit · integration · scenarios)
└── evaluation/                 (scenarios · results)
```

---

# 12. Pendências

## 12.1 Bloqueio crítico — orientador

Institucional, não técnico. Tudo na fase 1 depende disso.

**Caminho:** mapear professores via Lattes e diretório de grupos de pesquisa (dgp.cnpq.br) que
publicaram sobre LLM, agentes ou NLP nos últimos 2–3 anos. Abordar por e-mail curto citando um
trabalho específico da pessoa.

🔎 **A VALIDAR — os leads de orientação não batem com a matrícula.**

Os documentos listam **UFPR e UTFPR** como leads de orientação, mas nenhum deles nomeia a instituição
onde você está matriculado — e pelo que você já me contou, não é nenhuma das duas. Orientador de TCC
normalmente precisa ser docente da instituição em que você está matriculado.

Se for esse o caso, a estratégia atual está mirando fora do alvo e o bloqueio crítico continua
travado por um motivo evitável. Três caminhos, e vale decidir isto **esta semana**, porque é o
gargalo de tudo:

1. **Orientador interno** na sua instituição — pode não ter ninguém publicando em LLM/agentes, mas
   um orientador de engenharia de software com boa disciplina de método serve, e o seu método já é
   forte.
2. **Interno + coorientador externo** (UFPR/UTFPR) — se o regulamento permitir. Melhor dos dois
   mundos; verifique se coorientação externa é permitida.
3. **UFPR/UTFPR como alvo de mestrado**, não de TCC — talvez essa fosse a intenção original e os
   documentos misturaram os dois horizontes.

🔎 Confirme a instituição e o regulamento antes de disparar e-mails.

## 12.2 ✅ Informação institucional a levantar

| Item | Por que importa | Urgência |
|---|---|---|
| Normas ABNT / template do curso | Formatação; retrabalho se descoberto tarde | Baixa |
| Calendário: qualificação e defesa | **Reancora o roadmap inteiro** | **Alta** |
| Regulamento de TCC (coorientação externa?) | Destrava §12.1 | **Alta** |
| Exigência de publicação paralela | Muda o escopo de esforço | Média |
| ✅ **Necessidade de aprovação em comitê de ética (CEP)** | Ver abaixo | **Alta** |

**Sobre o comitê de ética** — lacuna que nenhum dos três documentos registrava. Seu plano prevê
**questionário de satisfação aplicado a pessoas**. No Brasil, pesquisa envolvendo seres humanos pode
exigir submissão ao CEP via Plataforma Brasil, e o trâmite leva meses. Instituições variam: algumas
dispensam TCC de graduação com dados não identificados, outras não. **Pergunte na coordenação
agora.** Se for exigido e você descobrir tarde, o cronograma quebra — e a alternativa (cortar o
critério 4 e avaliar só com métricas automáticas) é uma decisão que você quer tomar por escolha, não
por desespero.

## 12.3 Plano de execução — três frentes paralelas

As três são paralelas por construção: uma é leitura, outra é código, outra é script. **Nenhuma
bloqueia as outras e nenhuma depende de orientador.** É o hedge contra o bloqueio institucional
escorregar.

### Frente A — Literatura

**Produto:** notas de posicionamento em `docs/research/notas/`, uma por trabalho.
**Estrutura fixa:** o que mede · como mede · o que achou · **o que implica para o Cain**.
Nota que não termina em implicação é resumo, e resumo se joga fora.

| Ordem | Trabalho | Fecha |
|---|---|---|
| 1 | Choi et al. (2024) — identity drift | Base empírica do problema (§3.1) |
| 2 | Li et al. (2024) — instruction (in)stability | Método de medição → alimenta ADR-0010 |
| 3 | MemGPT (Packer et al., 2023) | ADR-0006 |
| 4 | MemoryBank (Zhong et al., 2024) | ADR-0007 |
| 5 | AutoGen + surveys (Wang, Xi) | Seções 2.1 e 2.2 |

Os dois primeiros são uma tarde e mudam o tom do capítulo inteiro.
**Critério de saída:** ADRs 0006 e 0007 saem de *Provisório*.

### Frente B — Esqueleto

**Contratos antes de qualquer lógica.** Tudo que depende de ADR provisório entra como stub
explícito — não é adiar, é construir o decidido e deixar buraco nomeado no resto.

| # | Módulo | Conteúdo |
|---|---|---|
| 1 | `common/` | `Message`, `IdentityState`, `DecisionRecord` |
| 2 | `llm/` | `Protocol` + adaptador Ollama + dublê determinístico |
| 3 | `persistence/` | As três portas do ADR-0009 + **teste da invariante `drop()`/`rebuild_from()`** |
| 4 | `agents/` | Contrato + Busca, Código, Resumo |
| 5 | `orchestrator/` | Sessão, mediador, `DecisionLog`. Roteador `# STUB — ADR-0008` |
| 6 | `identity/` | Serviço + injetor. Modelo e adaptação como `# STUB — ADR-0006/0007` |
| 7 | `tests/integration/` | `test_plug_new_agent.py` (§3.5) |

O teste da invariante no passo 3 é a guarda do ADR-0009 — sem ele a invariante quebra em silêncio.
**Critério de saída:** CI verde e um pedido atravessando os 8 passos de §5.6 ponta a ponta.

### Frente C — Harness de avaliação, antecipado

Construir os três braços do ADR-0010 como código **na fase 2**, rodando contra o Cain ainda stub.
Braços A e B não dependem de nada do Cain — são scripts contra o Ollama.

**Por quê antecipar:** §6.5 registra que as sondas de estilo podem estar capturando tópico em vez de
persona, e a mitigação é um piloto de 2–3 sondas. Esse piloto exige o harness. Descobrir em março,
com Cain stub, que as sondas não discriminam custa uma tarde; descobrir em agosto de 2027 custa o
TCC.

É a inversão que separa DSR que passa na qualificação do que trava: **o instrumento de medida existe
antes da coisa medida.**

**Critério de saída:** piloto rodado, sondas que discriminam personas, ADR-0010 pronto para *Aceito*
assim que o CEP responder.

### Se a capacidade real for menor

O plano assume noites e fins de semana sobre uma jornada de estágio. Se não couber, o que se corta é
o polimento da frente B. **A e C não se cortam** — são o que determina se o trabalho fecha.

## 12.4 Decisões técnicas abertas

- LLM base definitivo além do Ollama local (entra no ADR-0002).
- Idioma do protótipo (interface e prompts).
- N de participantes para a avaliação de satisfação — condicionado a §12.2.

~~Orquestração própria vs. framework~~ — ✔ resolvido em ADR-0011.

---

# 13. Notas de método

Aprendizados registrados. Não deletar; é o que mantém a coerência entre sessões.

- Decisões separadas explicitamente entre **firmes (engenharia)** e **provisórias (pesquisa)** —
  mantém integridade acadêmica e permite avançar sem travar.
- ADRs têm duplo papel: disciplina de engenharia **e** rastreabilidade acadêmica. Atendem
  diretamente à diretriz 6 de Hevner (design como processo de busca).
- O problema deve ser formulado de modo **model-agnostic** para não obsolescer junto com o LLM.
- Transformar critérios em **métricas concretas** é o ponto que trava qualificação em DSR. Agora tem
  ADR próprio (0010) e possível atalho via benchmark existente (§9.4).
- A delimitação de escopo é **arma defensiva de banca**, não item decorativo.
- ✅ **Novo:** escolha arquitetural e viabilidade de avaliação estão acopladas. O roteador baseado em
  regras não é só mais simples — é o que torna "precisão de delegação" mensurável (§5.3).
- ✅ **Novo:** documento único e canônico. Três documentos paralelos produziram, em uma única semana,
  três títulos, três listas de objetivos e duas posições opostas sobre framework. Fork de documento é
  fork de decisão. **Um documento, versionado.**
- ✅ **Novo — regra de fronteira entre mestre e ADR.** O ADR é a **fonte normativa** da decisão: ele
  carrega contexto, argumento, alternativas descartadas e consequências. O mestre carrega o
  **resultado e o link**, nunca o argumento completo. Duplicar o argumento nos dois é recriar o fork
  em escala menor — foi exatamente o que aconteceu na v3.0 e foi corrigido na v3.1.

---

# Anexo A — Índice de marcações para auditoria

## A.1 Aberto — exige ação

| § | Marca | Assunto | Ação |
|---|---|---|---|
| 1 · 12.1 | 🔎 | Instituição de matrícula vs. leads UFPR/UTFPR | **Confirmar — destrava o bloqueio crítico** |
| 12.2 | 🔎 | Comitê de ética (CEP) | **Perguntar na coordenação — risco de cronograma** |
| 10 | 🔎 | Datas do roadmap | Reancorar no calendário oficial de TCC |
| 9.3 | 🔎 | Risco de novidade — campo de *agent memory* | Ler antes de fechar a 2.6 |
| 5.2 | 🔎 | ADR-0006 depende da literatura de memória | Ler antes de fechar |
| 8 | — | ADR-0010 está **Proposto** | Aceitar **antes** da primeira coleta |
| 3.5 | — | `test_plug_new_agent.py` | Escrever (~30 min) |

## A.2 Resolvido nesta versão

| § | Assunto | Decisão |
|---|---|---|
| 3.3 | "Maximizar satisfação" no objetivo geral | **Fica fora.** Critério 4 rebaixado a secundário; §6.4 preservada |
| 3.4 | Objetivos específicos — 3 listas | **Lista canônica de 5.** OE2 elevado a entregável real |
| 3.5 | Genericidade | **Propriedade de design demonstrável**, não generalização reivindicada + teste que a sustenta |
| 6.3 | Tensão coerência × adaptação | **Superfícies separadas**, sondas disjuntas, imposto na métrica |
| 7.1 | Orquestração própria vs. framework | **Própria, escopo restrito** — ADR-0011, argumento de instrumentação |
| 6.2 | Desenho experimental | **Três braços.** B vs C isola a estrutura — ADR-0010 |
| 8 | ADRs 0009, 0010, 0011 | Escritos |

## A.3 Correções a conferir ao citar

| § | Assunto |
|---|---|
| 1 | Título canonizado entre três variantes |
| 4.1 | **DSR: as 6 fases são Peffers (2007), não Hevner** — corrigir em todo texto derivado |
| 9.2 | Quatro referências com título ou veículo errado |

## A.4 Preenchimentos a auditar

| § | Assunto |
|---|---|
| 3.1 | Base empírica do problema (Choi, Li) — **ler os dois papers** |
| 4.3 | Tabela de alinhamento com as 7 diretrizes de Hevner |
| 6.4 | Limitações éticas ampliadas |
| 6.5 | Ameaças à validade — atenção à ameaça interna, já endereçada pelo braço B |
| 9.2 | Frente de memória de longo prazo (4 refs) → incorporar à 2.4 |
| 9.4 | Benchmarks existentes como atalho |
| 12.3 | Ordem de leitura da revisão (2.4 antes de 2.2) |

**Nada foi deletado dos originais sem registro.** Cortes deliberados: "Documentar e publicar
resultados" saiu dos objetivos específicos (§3.4) e o SBIE saiu dos veículos-alvo (Anexo C).

---

# Anexo B — Log de sessões

| Data | O que foi feito |
|---|---|
| 2026-09-07 | Sessão inicial: tema, escopo, artefato, metodologia, roadmap (`tcc-cain-base.md`) |
| 2026-09-07 | Esboço conceitual v1: arquitetura em camadas, modelo de identidade, custos (`cain_esbozo_v1.md`) |
| 2026-09-07 | Documento de continuidade: contratos, ADRs 0001–0008, estrutura do repo, Cap. 2 (`ESTADO_DO_PROJETO.md`) |
| 2026-09-07 | **Consolidação nos três → documento mestre v3.0.** Correção da atribuição DSR; bibliografia validada; frente de memória de longo prazo incorporada; ameaças à validade, roadmap, ADRs 0009–0011 e questão do CEP acrescentados; sete conflitos entre documentos identificados e marcados |
| 2026-09-07 | **v3.1 — ADRs 0009, 0010 e 0011 escritos; cinco conflitos resolvidos.** Terceiro braço experimental (controle pareado por contexto) incorporado ao plano de avaliação; adaptação passa a ser medida por convergência a personas roteirizadas; separação coerência/adaptação imposta no nível da métrica. Restam duas pendências externas |
| 2026-09-07 | **v3.2 — enxugamento e execução.** Argumentos duplicados entre mestre e ADR reduzidos a ponteiros; regra de fronteira formalizada; §12.3 vira plano de três frentes paralelas com critério de saída; harness de avaliação antecipado para a fase 2; índice de ADRs criado |

---

# Anexo C — Changelog

## v3.2

**Enxugamento**
- §3.3, §3.5, §6.2, §6.3 e §7.1 reduzidas a resultado + ponteiro. O argumento completo vive no ADR.
- Regra de fronteira mestre ↔ ADR formalizada em §13. A v3.0 duplicava os argumentos de ADR-0010 e
  ADR-0011 dentro do mestre — o mesmo fork que o documento diagnostica, em escala menor.

**Execução**
- §12.3 substituída por plano de três frentes paralelas (Literatura · Esqueleto · Harness), com
  produto, ordem e critério de saída por frente.
- Antecipação do harness de avaliação para a fase 2, contra Cain stub.
- `docs/adr/README.md` criado com registro, faixas, grafo de dependências e caminho crítico.

## v3.1

**Conflitos resolvidos** (argumentos completos nas respectivas seções)
- Satisfação fora do objetivo geral; critério 4 rebaixado a secundário e rejustificado.
- Lista canônica de 5 objetivos específicos; OE2 elevado a entregável verificável.
- Genericidade reformulada como propriedade de design demonstrável, com teste que a sustenta.
- Tensão coerência × adaptação resolvida por separação de superfícies, imposta na métrica.
- Orquestração própria com escopo restrito, por argumento de instrumentação.

**ADRs escritos**
- 0009 — três portas de persistência (`IdentityStore`, `MemoryIndex`, `DecisionLog`) e a invariante
  de reconstrução do índice vetorial.
- 0010 — três braços experimentais, métricas por critério, pré-registro, plano substituto do
  critério 4.
- 0011 — implementação própria com lista normativa de exclusões de escopo.

**Mudanças de desenho decorrentes**
- Plano de avaliação passou de dois para **três braços**. B vs C é a comparação que sustenta a tese.
- Adaptação deixa de ser medida como "o perfil mudou" (que ruído satisfaz) e passa a ser
  **convergência** a personas roteirizadas com preferência conhecida.
- Temperatura, seed e pré-registro de rubricas entram como controles obrigatórios.

## v3.0

**Corrigido**
- Atribuição das 6 fases do DSR: Hevner → **Peffers et al. (2007)**. Erro presente nos três documentos.
- Título do ReAct (Yao et al.) e do AutoGen (Wu et al.).
- Wang et al. e Xi et al.: atualizados de preprint para versão em periódico.
- Título formal canonizado entre três variantes.

**Acrescentado**
- Base empírica citável para o problema (Choi et al. 2024; Li et al. 2024).
- Frente bibliográfica de memória de longo prazo — quatro referências, ausente por completo.
- Seção de ameaças à validade.
- Tabela de alinhamento com as diretrizes de Hevner.
- ADRs 0009 (persistência), 0010 (avaliação), 0011 (framework).
- Definições operacionais propostas + a tensão coerência × adaptação.
- Roadmap recuperado, com datas e riscos de cronograma.
- Questão do comitê de ética.
- Risco de novidade frente ao campo de *agent memory*; benchmarks existentes como atalho.
- Ordem de leitura da revisão bibliográfica.

**Marcado como conflito (não resolvido por mim)**
- Cláusula de satisfação no objetivo geral.
- Lista de objetivos específicos.
- Genericidade: justificativa vs. delimitação.
- Orquestração própria vs. framework existente.
- Instituição de matrícula vs. leads de orientação.

**Removido**
- Numeração antiga de ADRs (`001`–`005`), superada pela de quatro dígitos.
- "Documentar e publicar resultados" como objetivo específico.
- SBIE da lista de veículos-alvo: é um simpósio de **informática na educação**, e o Cain não é um
  trabalho educacional. ENIAC e BRACIS continuam. ✅

---

*Documento mestre — Projeto Cain. Substitui `tcc-cain-base.md`, `cain_esbozo_v1.md` e a versão
anterior de `ESTADO_DO_PROJETO.md`. As decisões de fundo vivem no repositório, não nas conversas.*
