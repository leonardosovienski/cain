# Índice de ADRs — Projeto Cain

Registro de decisões arquiteturais. Cada ADR é **imutável depois de Aceito**: decisão revista não se
edita, se **supersede** por um ADR novo que a referencia. O rastro é parte do artefato de pesquisa.

## Faixas

- **Faixa A — engenharia.** Decisão técnica necessária para construir. Não é contribuição de pesquisa
  e não vai para o corpo do TCC (no máximo, apêndice).
- **Faixa B — pesquisa.** Decisão que constitui a contribuição. Vai para o texto, tipicamente nos
  capítulos de arquitetura ou metodologia.
- **Sem faixa** — decisão de processo do projeto.

## Registro

| ADR | Título | Faixa | Status | Vai para o TCC |
|-----|--------|-------|--------|----------------|
| [0001](0001-adotar-adrs.md) | Adotar ADRs e tratar o repo como artefato de pesquisa | — | Aceito | Metodologia |
| [0002](0002-desacoplar-llm.md) | Desacoplar a arquitetura de qualquer LLM específico | — | Aceito | Arquitetura |
| [0003](0003-contrato-de-mensagem.md) | Contrato de mensagem entre camadas | A | Aceito | Apêndice |
| [0004](0004-contrato-de-agente.md) | Contrato comum de agente | A | Aceito | Arquitetura |
| [0005](0005-fronteira-abstracao-llm.md) | Fronteira da abstração de LLM | A | Aceito | Apêndice |
| [0006](0006-modelo-de-identidade.md) | Modelo de dados da identidade | B | **Provisório** | Arquitetura |
| [0007](0007-mecanismo-de-adaptacao.md) | Mecanismo de adaptação da identidade | B | **Provisório** | Arquitetura |
| [0008](0008-estrategia-de-roteamento.md) | Estratégia de roteamento do orquestrador | B | **Provisório** | Arquitetura |
| [0009](0009-fronteira-da-abstracao-de-persistencia.md) | Fronteira da abstração de persistência | A | Aceito | Apêndice |
| [0010](0010-protocolo-e-metricas-de-avaliacao.md) | Protocolo e métricas de avaliação | B | **Proposto** | **Metodologia** |
| [0011](0011-orquestracao-propria-vs-framework-existente.md) | Orquestração própria vs. framework existente | B | Aceito | **Metodologia** |

## Dependências e ordem de fechamento

```
0010 (avaliação)  ──depende──>  resposta sobre CEP  +  orientador
   │
   └──exige──>  0008 (roteamento)   ─ ground truth do critério 2
   └──exige──>  0006 (identidade)   ─ superfícies disjuntas dos critérios 1 e 3

0006, 0007  ──dependem──>  revisão de literatura (memória de longo prazo)

0011  ──é o mesmo argumento que──>  0008   (instrumentação do roteamento)
```

**Caminho crítico:** literatura de memória → fecha 0006 e 0007 → junto com 0008 permite Aceitar o
0010 → libera a coleta de dados.

## Regras

1. **ADR é a fonte normativa da decisão.** O documento mestre carrega o resultado e o link, nunca o
   argumento completo. Documento duplicado é decisão bifurcada.
2. **Provisório vs. Proposto.** *Provisório* = decidido o suficiente para construir, pendente de
   literatura. *Proposto* = ainda não vale, aguarda condição externa.
3. **O 0010 precisa estar Aceito antes da primeira coleta.** Fixar métrica depois de ver resultado
   invalida o trabalho.
4. Commits de ADR são datados e nunca reescritos — a data do commit é a prova de pré-registro.

## Template

Ver [`template.md`](template.md). Seções mínimas: Contexto · Decisão · Justificativa ·
Alternativas consideradas · Consequências (positivas, negativas, riscos com mitigação).
