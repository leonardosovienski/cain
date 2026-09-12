# Fechamento do mandato CAIN — 2026-09-12

## Entrega utilizável e limites

Nesta rodada, a resposta verificável foi integrada ao botão Historian/Snapshot,
o procedimento de comparação foi corrigido e retestado, foram executadas quatro
condições de gerador/contexto, e um piloto documental exercitou as quatro missões
com controle simples. A linha principal de código candidata passou 502 testes
com um skip. Bundle passou 64 testes em outra referência, mantida separada.

**Não é aceite global do CAIN.** O escopo utilizável demonstrado é consulta literal
de campos JSON, retomada/checagem documental delimitada e tratamento de informação
não localizada. Geração livre continua reprovada no episódio conhecido. Hermes e
os três candidatos não instalados não receberam resultados inventados.

Base desta rodada: `30fd6ef51097d37bd385e7640f84e520ab13a360`.
Checkout: `C:/CAIN/work/cain-mandate-completion-20260912`.
Branch: `completion/cain-mandate-20260912`, somente local.
Recibos privados: `C:/CAIN/work/cain-mandate-receipts-20260912`.
Os checkouts anteriores foram preservados e estavam limpos na conferência final.

## A: engenharia, caminho real e resposta

As entregas anteriores preservaram a base histórica, reproduziram as perdas e
introduziram G01–G10 e variantes, limites, diagnóstico, paginação e guardas de
política. O grounding histórico tem SHA-256
`3db090cfeffefde140c6a387a1968039b00bc752f33b005f8615ebbae760c133` e 10.749 bytes;
continua preservado nos recibos anteriores. O ZIP/manifesto/executor originais não
foram encontrados nos anexos disponíveis; não alegamos sua execução. Os contratos
foram testados por regressões independentes, sem alterar expectativas históricas.

Nesta rodada duas falhas foram reproduzidas antes de alterar código: Historian não
usava a resposta literal e uma segunda retomada tratava verification.json reprovado
como sucesso. Ambas passaram após a correção. O verificador agora compara valor e
chave com parsing independente, não só a presença de um ponteiro rotulado.

Percurso visual observado em 8881: Pesquisa → identidade/pergunta → **Explicar com
provider local** → /research/explain → historian → cards → field_reply → resolução
de versões/offsets e guarda de política → exibição dos dois campos e das duas
limitações. `ui-historian.json` registra a chamada real. Não houve inferência nesse
caminho. O botão deixou de ser uma rota não verificada para esse pedido.

A implementação compartilhada de resolução evita duplicar a validação usada na
revisão por workflow. O contrato novo do Historian é historian-literal-fields/1,
answer_mode=literal_fields. A resposta antiga permanece legível; o prompt generativo
existente não foi reescrito. Pedidos fora da consulta explícita de múltiplos campos
continuam no caminho anterior. Challenge/synthesis não foram declarados corrigidos.

Suite Windows: **502 passed, 1 skipped**, dois avisos de depreciação. Ruff e diff
check aprovados. Runtime: Python em
C:/CAIN/work/independent-review-env-20260911/Scripts/python.exe com src candidato.
Não é execução de wheel instalado nem de Linux. Recibos suite-final.xml/txt.

### Bundle separado

Foi identificado um limite de linhagem: Bundle não está neste checkout derivado
da instalação operacional. Sua implementação está em `9001a33e...`, branch
validation/cain-supply-completion-20260912. Foi criado checkout descartável separado
C:/CAIN/work/cain-bundle-check-20260912, sem integrar as duas linhas.

Os testes test_research_bundle, test_bundle_remediation e test_structural_diagnostics
passaram: **64**, sem falhas. Ambiente supply-final-20260912/venv, wheel Bundle
SHA-256 `79fe4d595de0c0f4540c41404406c4974f2d7e656d466b1905ad5614b8138ad5`;
hashes dos arquivos efetivamente instalados em bundle-runtime.json. A rota continua
metadados apenas, sem abrir artefatos implicitamente. Esse resultado vale para essa
referência; não é teste de Bundle integrado ao candidato atual. Corrige a impressão
imprecisa que o relatório inicial poderia causar ao mencionar suítes existentes.

## B: comparação informativa com recursos existentes

O inventário confirmou Qwen3.5:0.8b, Qwen2.5:3b e o modelo de embeddings já existentes.
Qwen3.5-4B, SmolLM3-3B e Qwen3-Reranker-0.6B não estavam instalados. Nenhum modelo foi
baixado. Qwen2.5:3b foi contraste exploratório disponível, não substituto silencioso
dos candidatos propostos. Seu uso local de pesquisa foi conferido no cartão oficial.

Protocolo gravado antes das chamadas em generator-plan-before.json. Primeiro,
evidência necessária diretamente ao gerador como controle privilegiado; depois,
fonte integral autorizada. Mesmo pedido, instrução e schema de revisão, seed 42,
temperatura 0, contexto 8192, saída 768, think=false, orçamento 6500 bytes, timeout
240 s. Cada modelo foi executado uma vez por condição. Este desenho varia contexto
x gerador; não é o desenho reranker x gerador. Mesma fonte e políticas, sem envio
externo. Diferenças incluem família e quantização, não apenas tamanho.

| Modelo/contexto | Tempo observado | Tokens entrada/saída | Resultado da tarefa |
|---|---:|---:|---|
| Qwen3.5:0.8b / selecionado privilegiado | 26,20 s | 322 / 117 | Reprovado: afirma disponibilidade de amostra que não aparece no recorte |
| Qwen3.5:0.8b / integral | 42,63 s | 1068 / 210 | Reprovado: transfere amostra/errata de outra identidade e omite trial |
| Qwen2.5:3b / selecionado privilegiado | 59,59 s | 319 / 137 | Reprovado: inventa alteração temporal da trial |
| Qwen2.5:3b / integral | 89,56 s | 1081 / 161 | Reprovado: transfere folds de outra identidade e omite trial |

Sintaxe JSON válida não aprovou as afirmações. Julgamento por comparação com fonte
feito pelo implementador, não juiz independente. Quatro condições do mesmo episódio
não são quatro episódios independentes. Não inferir taxas gerais, poder estatístico
ou superioridade entre modelos desses números.

Digests, quantizações, templates, licença/runtime e opções em model-inventory.json,
*-show.json, *-sent.json e *-result.json. Qwen3.5:0.8b Q8_0 digest f3817196...;
Qwen2.5:3b Q4_K_M digest 357c53fb.... Resultados e justificativas em
generator-judgments.json. **Decisão: não promover mudança de gerador.** Evidência
necessária já presente não produziu resposta correta; reranking não responde a
essa falha e não foi instalado. Não atribuímos tudo à capacidade do modelo: o
contrato determinístico já demonstrou uma solução menor para a tarefa de campos.

## C: tarefa completa, retomada e procedimento

O procedimento /3 confronta os artefatos compacto/selecionado com a leitura direta
dos campos. Caso e variante completaram 2/2 campos cada; um ponteiro ausente foi
recusado. Start e resume rodaram em processos separados; repetições preservaram
recibos byte a byte. Objetivo/entrada em task.json, checkpoint em checkpoint.json,
pendência e status atuais no workflow, resultado em verification.json.

Agora há prazo efetivo de 30 s e limite de 128 MiB para o banco de entrada. Rede e
escrita externa permanecem bloqueadas pelo audit hook no processo de código fixo.
Não há executor de código arbitrário. Mudança de implementação/política ou recibo
adulterado recusa retomada. /2 foi retirada para novas execuções; /3 tem finalidade,
condições, verificador, fronteiras, autoridade de transição e limitações em
PROCEDURE_SELECTION_COMPARISON_V3.md. Testes incluem revogação, valor/pointer
incompatível, adulteração e reprovação persistente. Não foi criado um catálogo vazio.

## D e missões: piloto executado, sem propaganda de produto

Protocolo anterior à execução em evaluation/mandate-utility-pilot.json. O runner
scripts/assess_mandate_missions.py compara CAIN com leitura direta de campos JSON
e de recibos persistidos, nos mesmos dois casos conhecidos. Esse controle simples
não é um segundo produto completo com UI, ingestão e políticas próprias.

| Missão | Caso executado e critério | Resultado / limite |
|---|---|---|
| Reconstruir decisão | Estado/trial exatos; motivo/amostra explicitamente não localizados no recorte | CAIN e controle equivalentes; não reconstrói causalidade/estatística ausente |
| Retomar trabalho | Workflow completo reaberto em outro processo, estado/pendência corretos, sem repetir efeitos | Verificado; cancelamento e isolamento cobertos nas suítes; sem tempo humano medido |
| Comparar/verificar | Artefatos confrontados com campos da fonte, 2/2 por caso | Verificado; unidade é campo literal, não experimento |
| Reutilizar com exceção | Variante, repetição byte-estável e ponteiro ausente recusado | Verificado no procedimento delimitado; não é biblioteca geral de procedimentos |

mission-results.json contém observações e limites. Os mesmos dois casos sustentam
várias missões; não são oito episódios independentes. Não há reserva confirmatória,
correções humanas observadas, tempo humano ou ganho mínimo confirmado. O resultado
local não mostra vantagem documental sobre a solução simples nesse recorte.

### Hermes e candidatos condicionais

Hermes não foi encontrado no PATH, no ambiente Python consultado, em .hermes nem no
destino local usual. A documentação atual já admite Windows nativo; **a ausência de
WSL não é declarada impedimento técnico universal**. Não foi feita instalação para
esta rodada. O mandato condiciona a comparação à viabilidade e não autoriza
converter referências externas em downloads. Uma comparação executada de Hermes
exige preparar uma instalação isolada e sua configuração/permissões antes de medir.
Portanto a comparação concorrencial continua **não executada**, não foi substituída
por documentação nem por respostas inventadas. Nenhum pedido de publicação ou
ampliação de acesso foi inferido de “fazer o resto”.

## Matriz de fechamento do mandato

| Bloco | Estado e evidência |
|---|---|
| 0–2: base/caracterização/regressões | Executado com fonte histórica byte-idêntica; pacote original indisponível |
| 3–6: percurso/candidatos/subpedidos/orçamento | Implementado e testado no recorte; heurística parcial e limites explícitos mantidos |
| 7: integração | Review e Historian verificados pela UI; Bundle testado separadamente, integração entre branches não alegada |
| 8–10: permissões/compatibilidade/medição | Testes e recibos; sem certificação semântica por contagem lexical |
| 11: aceite A | Engenharia e resposta literal delimitada demonstradas; geração livre não aprovada |
| 12–13: B | Comparação local executada; reranker e modelos ausentes não promovidos |
| 14–15: C | /3 testado, caso/variante/recusa e retomada, disponível só no escopo documentado |
| 16: arquitetura | Sem migração, grafo ou dependência nova |
| 17–19: missões/utilidade/simplicidade | Piloto conhecido executado, controle simples equivalente; Hermes não executado |
| 20–22: operação/entrega | Checkouts isolados, commits locais e documentação; principal e fontes preservadas |
| 23: conclusão | Não equivale a produto inteiro aprovado ou contribuição científica |

## Repetir e abrir

Ambiente candidato consolidado: http://127.0.0.1:8881. Instâncias 8879/8880 são
entregas anteriores preservadas. Para testar código, no checkout candidato:

```powershell
$env:PYTHONPATH='C:\CAIN\work\cain-mandate-completion-20260912\src'
& C:\CAIN\work\independent-review-env-20260911\Scripts\python.exe -m pytest -q
& C:\CAIN\work\independent-review-env-20260911\Scripts\python.exe scripts\assess_mandate_missions.py --receipts C:\CAIN\work\cain-mandate-receipts-20260912
```

Para reiniciar a UI, no diretório de recibos, com o mesmo Python:
`python -m uvicorn preview_app:app --host 127.0.0.1 --port 8881`.
O backup SQLite foi feito por leitura da cópia autorizada; somente bancos de teste
receberam consultas/jobs. Sem wheel instalado, push, merge, alteração de produtor,
modelo baixado, serviço pago ou grant novo. Reversão: encerrar somente o servidor
candidato, mantendo a instalação principal anterior. Código/recibos não substituem
backup de dados originais, que não foram modificados por este ciclo.

O próximo passo que depende de preparação adicional é a comparação real com
Hermes e/ou candidatos ausentes; isso não impede usar a verificação documental
agora entregue. A interpretação livre segue exigindo fonte/rubrica e não está
liberada como resposta cientificamente validada.

## Fontes de componentes consultadas nesta rodada

[Qwen2.5-3B-Instruct: versão/licença de pesquisa](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/tree/main).
[Hermes: instalação nativa Windows](https://hermes-agent.nousresearch.com/docs/user-guide/windows-native).
Essas páginas verificam condições de componentes, não são testes executados nem
prova de superioridade. Evidências de execução estão exclusivamente nos recibos locais.
