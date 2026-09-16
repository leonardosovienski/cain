# Campanha de leitura e validação Stocks — 16/09/2026

## Disponível no CAIN principal

Projeto **Stocks — pesquisa e validação**, pertencente ao usuário local `leo`.
Na interface do CAIN, selecionar esse projeto para consultar seus documentos.
Foram admitidos como documentos de projeto 88 textos de evidência já autorizados,
22 fichas de hipóteses, um resultado da campanha e uma bibliografia: **112 documentos**.
Os hashes dos documentos foram conferidos; o documento preexistente foi preservado.

Os jobs de pesquisa continuam na coleção `stocks`, com projeto vazio, prefixo
`stocks-campaign-20260916-primary-H`. São 22 jobs concluídos: 15 leituras literais
dos campos históricos/reliabilidade e 7 buscas de fontes. Isso não significa que
22 hipóteses foram economicamente aprovadas ou executadas novamente.

## Testes efetivamente executados

| Verificação | Resultado |
|---|---|
| Testes locais da simulação mensal | 12 aprovados |
| Testes locais da exposição simples | 19 aprovados |
| Reprodução H21 | 8 cenários e 16.400 pontos idênticos; 9 ZIPs reconferidos |
| Reprodução H22 | 24 avaliações e 30.226 pontos idênticos; 2 casos inviáveis preservados |
| Stocks Linux/Python 3.13, nova execução | 901 testes e 65 subtestes aprovados; 17 regressões arquivadas aprovadas separadamente |
| Ferramenta da campanha CAIN | 2 regressões aprovadas e CI Python 3.11–3.14 aprovada |

As verificações locais foram feitas primeiro em QA e depois registradas no
principal. As repetições não são somadas como novas provas econômicas.
O código produtor permaneceu limpo no commit `9363ce242cb8e732b7c5222dd09b0d0715b323b9`.

[Nova execução Stocks](https://github.com/leonardosovienski/stocks-predictor/actions/runs/35038751214),
job Python 3.13 `104990850762`; cobertura reportada 79%, demais gates aprovados.
[PR #6 do CAIN](https://github.com/leonardosovienski/cain/pull/6), integrada em
`9a719efca2d94417e38007b44eb97237c99a95e7`; CI de push `35154813151` e PR
`35155070969` aprovadas. Não houve alteração do pacote instalado: a ferramenta
de campanha usa o CAIN instalado e chama os verificadores stdlib revisados.

## O que as conclusões permitem afirmar

- H1–H20: fontes e estados históricos foram organizados; a suíte de software foi
  repetida. Não houve uma nova observação econômica ou reabertura dos protocolos.
- H21: o resultado histórico condicional foi reproduzido. Custos/eventos completos,
  prontidão pessoal e resultado futuro continuam sem comprovação integral.
- H22: a rejeição nos critérios registrados foi preservada. Casos inviáveis não
  foram descartados e reproduzir a conta não converte a rejeição em aprovação.
- Interpretação livre: continua com as limitações do
  [piloto anterior](STOCKS_STUDY_READINESS_20260915.md). Esta campanha não usou
  respostas do modelo para decidir aprovação científica.

Os dossiês conservam todos os campos/revisões localizados pelo extrator nativo e
registram limites de análise. Não certificam leitura integral de todo arquivo do
produtor. Os documentos originais recebidos permanecem disponíveis no projeto.

## Evidências locais e continuação

- Principal: `C:/STOCKS/work/cain-campaign-20260916-primary/campaign.json`.
- Entrega na interface: `workspace-delivery.json` no mesmo diretório.
- Dossiês: `H1-dossier.json` até `H22-dossier.json`, preservados localmente.
- Jobs e resultados: `H1-job.json` até `H22-job.json`.
- QA: `C:/STOCKS/work/cain-campaign-20260916-qa`.
- H22 completa: `C:/STOCKS/work/profit-validation-r5-20260910/stocks-campaign-20260916-primary.jsonl`.
- Banco de documentos anterior: `workspace-before.db` no diretório da campanha.

Fontes volumosas, bancos e dossiês privados não foram publicados no GitHub.
Nada foi apagado; nenhuma ordem, conta financeira ou automação recorrente foi criada.
O runtime completo Stocks segue dependendo de Linux; este Windows não tem WSL.

Para uma nova reprodução finita, usar o runner com identificador e saída novos:

```powershell
& C:\CAIN\work\stocks-study-20260915\runtime-r3\Scripts\python.exe -I `
  C:\CAIN\work\stocks-study-20260915\checkout\tools\run_stocks_campaign.py `
  --stocks-root C:\STOCKS\stocks-predictor `
  --output C:\STOCKS\work\NOVA_CAMPANHA `
  --db C:\CAIN\dados\research.db `
  --policy C:\CAIN\config\research-policy.json `
  --run-id NOVO_IDENTIFICADOR
```

O runner não agenda continuações. A próxima rodada científica exige fechar os
requisitos de cada protocolo; uma repetição técnica não supre dados ausentes.

## Pesquisa bibliográfica complementar

[Kenneth French — definição do fator momentum](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_mom_factor_daily.html)
e [Sloan (1996) — accruals e fluxos de caixa](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2598)
foram localizados como referências metodológicas. Não constituem validação dos
resultados brasileiros nem substituem os protocolos locais; os artigos integrais
não foram admitidos como conteúdo recebido.
