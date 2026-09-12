# Aceite manual — CAIN em staging

**LIMITED_IN_STAGING.** CLI/API dos seis bundles e web do acervo legado foram exercitadas. O roteiro é factual, sem precisar de modelo. Diagnósticos por regras são experimentais; os bundles reais atuais negam geração. Inferência real foi testada separadamente na CLI, com qualidade semântica não certificada.

Candidato `d00bbc6fb910b3c51be6720d21012f4655258468adb7d7335451974929c58752`; CAIN 0.4.7; Python 3.12.14 Windows; wheel SHA256 `4fc950531cca6930055636e78485967c647cc5aee2dd326039719ec0af277006`. Ambiente `C:/CAIN/work/supply-final-20260912/venv`; dependências exatas em `dependencies.txt`. O manifesto identifica código/contratos, corpus, política e runner. Não é um commit Git nem a instância ativa.

## Abrir e encerrar

```powershell
Set-Location 'C:\CAIN\work\supply-final-20260912'
$CainPython = 'C:\CAIN\work\supply-final-20260912\venv\Scripts\python.exe'
& $CainPython .\preview.py --collection crypto query --entity-type hypothesis --limit 50
```

Cada consulta encerra sozinha; Ctrl+C interrompe somente esse comando. O adaptador grava saída e erro em `USER_OBSERVATIONS.jsonl`.

Para a interface web **legada**, execute no mesmo terminal:

```powershell
& $CainPython .\web_preview.py --legacy
```

Abra http://127.0.0.1:8889. Expanda **Pesquisa · L0 Historian**, deixe usuário `leo` e projeto `Geral`, escolha `crypto`, `stocks` ou `brasileirao` no campo Acervo e clique **Consultar acervo**. Limpe Identidade da fonte/Estado/Texto ao trocar de domínio. Abra uma evidência recebida; **Dossiê** permite navegar proveniência e datas desconhecidas. Ao recarregar, o campo retorna a `crypto`: selecione o acervo desejado novamente.

Encerre com **Ctrl+C no terminal desse servidor**. Repita o mesmo comando para recuperar o acervo. Esse início/reinício foi ensaiado. Nenhum serviço ficou ativo; Host/Origin originais e binding 127.0.0.1 foram mantidos. A web usa `model/research.db` e sua política; a CLI Bundle usa `staging/research.db`. São acervos diferentes. Não use os botões de geração como parte deste roteiro factual: o provider temporário foi encerrado.

## Acervos e limites

| Coleção | Entidades Bundle | Descritores recebidos | References |
|---|---:|---:|---:|
| crypto |20|12|0|
| brasileirao |14|2|3|
| stocks |3|0|3|
| core |16|16|0|
| ops |11|11|0|
| ecosystem |6|6|0|

O acervo Bundle tem 70 entidades, 47 descritores recebidos e 6 referências, 231658 bytes lógicos. A web legada contém 15/1/3 revisões em Crypto/Stocks/BR. Revisões não são experimentos. Stocks não recebeu preços; BR inclui relato retrospectivo, sem gerar previsão. Core/Ops/Ecosystem oferecem documentos e contratos, não todos os logs de runtime. UNKNOWN e ausência de clock histórico permanecem explícitos.

Descoberta, admissão e ingestão estão separadas em `SOURCE_INVENTORY.json`, `LEGACY_SOURCE_INVENTORY.json`, `POPULATION_PLAN.json` e `KNOWLEDGE_COVERAGE.json`. Outros paths visíveis não foram automaticamente autorizados. `ADMISSION_REQUESTS.json` registra operações pendentes de decisão administrativa; nenhum grant foi ampliado para passar um teste.

## Doze perguntas para experimentar


Use `& $CainPython .\preview.py --collection SCOPE COMANDO` com os valores abaixo. As perguntas descrevem o objetivo da consulta; a CLI não interpreta linguagem natural. Não há gabarito factual antecipado nesta tabela.

| Scope | Pergunta | COMANDO | O que inspecionar |
|---|---|---|---|
| crypto | Quais hipóteses constam do estado admitido? | `query --entity-type hypothesis --limit 50` | Status, eixo de status, origem e limitações; não é novo ensaio. |
| crypto | Quais relações do acervo têm apoio declarado? | `lineage --limit 50` | Endpoints e relações explícitas, sem completar vínculos históricos ausentes. |
| brasileirao | Que alegações estão registradas e em quais estados? | `query --entity-type claim --limit 50` | Claim, fonte e diferença entre alegação e previsão prospectiva. |
| brasileirao | Que relatórios têm bytes e quais são referências? | `artifacts --limit 50` | availability e sha256; preservar limitação retrospectiva/contaminada. |
| stocks | Quais versões de fontes estão representadas no catálogo? | `query --entity-type dataset --limit 50` | source_id, versão, origem, clocks existentes e UNKNOWN. |
| stocks | Que dependências exigiriam bytes externos? | `artifacts --limit 50` | Referências sem fetch; ausência de licença não vira autorização. |
| core | Quais documentos de metodologia e contratos estão disponíveis? | `query --entity-type document --limit 50` | Descoberta por título/caminho; versão documental não prova versão de trial. |
| core | Como um registro documental se liga ao objeto preservado? | `lineage --limit 50` | Relação explícita REPRESENTED_BY e identidade do objeto. |
| ops | Quais contratos operacionais posso consultar? | `query --entity-type document --limit 50` | Contratos e documentos; distinguir biblioteca de recibos reais de jobs. |
| ops | Quais documentos originais foram recebidos? | `artifacts --limit 50` | Objeto, bytes e hash; nenhum sucesso econômico implícito. |
| ecosystem | Que contratos de distribuição estão documentados? | `query --entity-type document --limit 50` | Pacotes e documentos do recorte versionado, sem inventar compatibilidade histórica. |
| ecosystem | Como inspecionar a proveniência documental desse acervo? | `lineage --limit 50` | Relacionar registro e objeto, depois abrir evidence pelo bundle/id. |

Para inspecionar uma evidência, copie `bundle_id` e `id` de uma entrada `evidence` retornada por `query`:

```powershell
& $CainPython .\preview.py --collection core evidence 'BUNDLE_ID_RETORNADO' 'EVIDENCE_ID_RETORNADO'
```

Os IDs desse exemplo são campos a substituir. O ensaio de todos os seis scopes usou IDs reais e confrontou o payload com a fonte. Originais recebidos também foram materializados em `C:\CAIN\work\supply-final-20260912/materialized`, com nomes `scope-sha256`; confira `sha256` em `artifacts` para localizar o arquivo correspondente. São bytes originais verificados, sem executar seu conteúdo. References não possuem arquivo materializado.


## Reconhecer problemas

- `total:0`/exit0 pode ser ausência no escopo. `query --entity-id ABSENT-ENGINEERING-CONTROL-20260912` é o controle de ausência; `verify` testa integridade.
- `reference_only` tem metadata, sem bytes/fetch. `received` precisa de bytes e hash verificado.
- Revogação oculta fontes/derivações; histórico legado retorna `history_redacted_by_current_policy`. Não ampliar permissões para eliminar a recusa.
- `CORRUPTION`, traceback ou exit não zero não é uma resposta factual vazia.
- Sem provider, explicação não executa inferência. Houve 3 chamadas reais bem-sucedidas e 1 timeout nesta validação; saídas reais estão em `MODEL_VERIFICATION.json` e recibos associados. Citações exatas não certificam a síntese.

Registre pergunta, resposta/referências, candidato, coleção, horário e expectativa em `USER_FEEDBACK.md` nesta pasta, mencionando a entrada de `USER_OBSERVATIONS.jsonl`. Não salve o feedback como fato científico.

## Runner finito

```powershell
& $CainPython .\runner.py --config .\UTILITY_PROTOCOL.json --state .\utility-release
```

O comando foi interrompido após 2 casos e retomou até 18, preservando os resultados. Limites: 24 casos/invocação , 600 s, 45 s/subprocesso, concorrência 1, zero modelos, 2 MB por captura, 32 MB de estado e reserva 1 GiB. `utility-release/CHECKPOINT.json` já concluído é validado na retomada. Código/acervo/policy diferentes exigem revalidação e pasta nova. RAM de pico é desconhecida. Não há scheduler nem execução depois de encerrar o processo.

Recibos: `MANUAL_GUIDE_REHEARSAL.json`, `WEB_REHEARSAL.json`, `ACCEPTANCE_LEDGER.jsonl`, `INTERRUPTION_RELEASE.json`, `utility-release/CHECKPOINT.json`.


<!-- supplemental-real-closure -->
## Ensaio adicional: diagnósticos reais autorizados

O acervo suplementar usa o mesmo Python instalado e tem identidade `3f3b34cf116201aea601459668b70480570fa9583575e727228e75fd0c2a8063`. Os documentos de `core`, `ops` e `ecosystem` foram republicados para análise estrutural local. É um acervo separado; não substitui o roteiro original. Comando já exercitado (troque somente a coleção para alternar):

```powershell
& 'C:/CAIN/work/supply-final-20260912/venv/Scripts/python.exe' -m cain research --db 'C:/CAIN/work/supply-final-20260912/closure-real-20260912/staging/research.db' --policy 'C:/CAIN/work/supply-final-20260912/closure-real-20260912/staging/policy.json' --user leo --collection core bundle diagnostics
```

Encerra sozinho. O resultado é uma contagem estrutural rastreável, não interpretação por modelo. O restore usado para testar revogação está em outra pasta e intencionalmente nega geração.
