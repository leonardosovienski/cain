# Rubrica preliminar — não é pré-registro científico

Versão `draft-2026-09-07-2-functional`. A versão inicial foi escrita antes da primeira execução
técnica do harness; esta revisão documenta a medição funcional de preferências explícitas.
O ADR-0010 continua **Proposto**. Esta rubrica precisa de revisão, validação de construto,
aprovação pertinente e commit datado antes de qualquer coleta formal.

## Coerência: somente sondas `style-*`

Compare respostas à mesma sonda em sessões distintas. O fato solicitado permanece idêntico.
Pontue separadamente tom, verbosidade, estrutura e tratamento de erro, de 1 a 5:

| Nota | Âncora para estabilidade de cada traço |
|---|---|
| 1 | Mudança incompatível com o traço declarado; contradição clara entre sessões. |
| 2 | Mudança substancial em mais de uma resposta. |
| 3 | Traço parcialmente estável, com oscilação identificável. |
| 4 | Traço estável, com variação pequena sem contradição. |
| 5 | Traço consistente nas sessões observadas. |

Não use correção factual como substituto de estilo. Registre erros factuais em campo separado.
Para o piloto de construto, tente identificar os dois estilos declarados sem ver a chave;
justifique quais traços distinguem as respostas. Discriminação ainda exige avaliação humana:
saídas do dublê determinístico não validam sondas nem medem personalidade.

## Adaptação: somente sondas `profile-*`

Compare o perfil inferido com a persona declarada previamente em `scenarios.json`.
Pontue atendimento da preferência de formato e adequação ao nível declarado separadamente:
1 = contrário; 2 = frequentemente contrário; 3 = parcial; 4 = predominantemente alinhado;
5 = alinhado em todas as respostas observadas. Ausência de evidência = não mensurável,
com motivo. Mudança por si só não recebe pontos. Não preencha notas de estilo aqui.

**Limitação aberta:** preferência de formato pode se sobrepor ao construto de estilo.
Os IDs disjuntos não provam independência. No piloto, separar recuperação factual do conteúdo
declarado (por exemplo, recordar que a preferência era “passos”) de obedecer àquele formato na
própria resposta. A rubrica de adaptação acima precisa de revisão e um extrator validado antes
de coleta; não usar o mesmo comportamento observável para pontuar coerência e adaptação.

O alvo de formato é um vetor one-hot previamente definido: `[steps, paragraph]`.
O smoke v0.2 codifica diretamente a preferência explícita realmente armazenada; ausência
ou categorias fora desse fixture são nulas. Distância e redução descrevem esse estado mecânico,
sem estabelecer inferência implícita ou validade de construto. Uso como métrica formal de
adaptação depende da revisão do instrumento. Na demonstração funcional, como o usuário corrige
a preferência durante as sessões, comparar cada etapa com seu alvo vigente; não calcular
convergência entre alvos diferentes.

## Delegação

Use o agente esperado de cada cenário, definido antes da execução. Calcule acurácia e
matriz de confusão 3×3 somente para C, sem contar as sondas auxiliares. A e B não roteiam:
seus valores são nulos, jamais zeros. Relate separadamente intent explícito e inferência.

## Satisfação e concordância

Satisfação percebida é secundária, descritiva e depende das autorizações aplicáveis.
Sem participantes, não existe medida de satisfação. Plano substituto do ADR: 2–3 avaliadores
cegos com rubrica qualitativa. Não simule avaliadores com FakeLLM. Não use testes de
significância com n < 20. Quando houver notas independentes, reporte percentual de acordo
ou Cohen's κ, preservando notas originais, discordâncias e número de pares avaliados.

## Aplicação cega e preservação

Entregue apenas `blind/paired.jsonl` e esta rubrica aos avaliadores. O arquivo
`private/unblinding.json` e os logs brutos identificam os braços e devem ficar separados.
A ordem das alternativas é randomizada com seed registrada. Respostas podem revelar
características do sistema: a remoção dos identificadores não garante cegamento perfeito.
Não descarte cenário nem resposta após observar resultados; registre invalidações e razões.
