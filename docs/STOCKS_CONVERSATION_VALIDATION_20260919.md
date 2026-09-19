# Validação conversacional Stocks H1–H22 — 19/09/2026

Foi entregue no projeto CAIN **Stocks — pesquisa e validação** a conversa
`stocks-conversation-20260916`, com 70 turnos preservados: as tentativas reais
das campanhas, a rodada integral de 50 perguntas e o reteste finito de nove
casos. As respostas foram produzidas em QA e projetadas sem reescrita para o
histórico do projeto; cada turno indica origem, fase, hash e avaliação externa.

## Resultado verificável

- Rodada v19: 50 casos, incluindo seis controles; uma tentativa interrompida
  por `std::bad_alloc` foi preservada e os demais casos continuaram em quatro
  lotes independentes.
- Reteste v20: nove casos. Os três controles passaram; H7 recuperou veredicto,
  confiabilidade e reabertura como eixos separados; H17 e H22 ficaram
  parcialmente fiéis; duas sínteses H1 voltaram a exceder o limite.
- Avaliação v19: 5 controles aprovados, 6 respostas fiéis porém parciais e 39
  respostas com falha semântica, de recuperação, cobertura ou geração. Não há
  aprovação semântica geral.
- Não houve experimento econômico novo. H21 continua resultado histórico
  condicional; H22 continua rejeitada pelo critério histórico integral.

O relatório e as 22 fichas de avaliação foram admitidos como documentos do
projeto junto às fontes revisadas. Bancos principais receberam apenas adições;
os recibos em `C:/CAIN/work/stocks-conversation-20260916` registram a entrega
em ensaio e a entrega principal, incluindo preservação de 42 turnos anteriores.

## Código e runtime

O commit `f9a48d80a46f7a538a489c99374f0e775e862e74` melhora a seleção de
facetas pedidas, reconhece veredictos em negrito e evita enviar o marcador
receptor `NOT_STRUCTURED_IN_SOURCE` como se fosse status científico. A suíte
local direcionada teve 66 testes aprovados; a CI passou em Python 3.11–3.14,
incluindo wheel não editável fora do checkout. O runtime principal foi trocado
para o candidato verificado correspondente, mantendo modelo e demais
configurações locais. Essas verificações técnicas não certificam interpretação
econômica ou semântica.

Os dados volumosos, bancos, textos brutos do provedor e backups permanecem
locais. Esta documentação não publica nem substitui esses artefatos.
