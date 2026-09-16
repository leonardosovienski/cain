# Correção da prontidão Stocks — 15/09/2026

A auditoria encontrou apenas um registro Snapshot na coleção Stocks principal,
proveniente de `STOCKS_CURRENT_STATE.md`. Um Bundle adicional continha dois
artefatos `reference_only`: referências não são dados recebidos. A instalação
também não correspondia às correções integradas na main.

## Correções desta revisão

- Campos JSON herdam os rótulos do objeto que os contém e de seus ancestrais.
  Elementos irmãos não compartilham identidade; uma identidade mais específica
  substitui a identidade do ancestral. `hypothesis_id` é reconhecido literalmente.
- Um título que menciona explicitamente a hipótese continua elegível quando
  começa pelo identificador do relatório, como `R5 — resultado da H22`.
- Caminhos de documentos citados não são reinterpretados como hipóteses por
  conterem datas ou números.
- Termos solicitados no conteúdo têm prioridade sobre metadados incidentais.
  Uma pequena lista explícita de termos de campos em português/inglês auxilia
  a busca; não mapeia estados nem inventa equivalências científicas.

Seleção: `identity_balanced_excerpts/12`. Não há alteração de protocolos,
resultados históricos, dados do produtor ou autorização de operação financeira.

## Verificação e limites

Os 78 testes direcionados de seleção, instruções e leitura literal passaram,
com dois avisos de depreciação de dependências. A suíte completa da revisão será
verificada pela CI, em Python 3.11–3.14, incluindo o wheel fora do checkout.
Uma suíte local intermediária foi interrompida para incorporar a correção de
caminhos datados e não conta como validação final.

O catálogo preparado em QA tem 48 fontes e 87 ocorrências com hashes conferidos.
H1–H22 têm trechos recuperáveis, mas isso não prova completude dos insumos de
experimento ou compreensão. O teste do filtro `source_id=H1` não é equivalente
à pergunta sobre H1: o filtro identifica registros, cujos IDs podem incluir
caminho e revisão. A matriz de perguntas sem esse filtro é a referência correta.

O primeiro piloto foi interrompido pelo ambiente sem resposta. A tentativa
seguinte falhou no inventário de um Ollama ainda inicializando. Ambas permanecem
registradas; nenhuma delas é aprovação semântica. Novos resultados de interpretação
devem ser examinados contra os trechos efetivamente enviados.

Evidências locais: `C:/CAIN/work/stocks-study-20260915`. Bancos de QA, políticas,
copias de recuperação e modelos não acompanham este documento público. A atualização
da instalação e a admissão no acervo principal exigem recibos próprios, distintos
do commit de código. Nenhum novo backtest ou resultado econômico é declarado aqui.


## Continuação em 16/09/2026

A PR #4 foi integrada na main `83c3d013d5f80828b365004d303c588c1b33a27b`.
As duas execuções de CI daquela revisão passaram em Python 3.11–3.14, incluindo
validação do wheel fora do checkout. Não confundir com a revisão seguinte.

A ativação principal foi executada: 48 fontes, 88 registros com permissão de
geração; os 12 payloads de publicação preexistentes foram preservados. Os 87
registros novos somam-se ao registro anterior. `activation-receipt.json` e
`activation-backup` documentam admissão, cópia consistente do banco, políticas,
configurações e atalhos anteriores. A antiga `.venv` permanece no disco.
Referências Bundle sem conteúdo recebido continuam `reference_only`.

A revisão `/12` remove o caminho explícito também dos termos e pares de busca.
Antes, a data do arquivo selecionava horários e excluía os campos solicitados.
O novo teste mantém duas revisões independentes e preserva valores `null`.
Os três estudos literais passaram em QA (`literal-studies-r3-qa`): H1 mantém
`NOT_SUPPORTED` e `INCONCLUSIVE_METHOD`; H17 mantém revisões 1/2 e ausência de
veredicto canônico (`null`); H22 expõe critérios de lucro histórico e fontes.
São leituras determinísticas com zero chamadas de modelo, não inferência certificada.

### Denominador das tentativas de interpretação

- Primeiro piloto: interrompido pelo ambiente antes da resposta.
- Segunda tentativa: falha de inicialização/inventário do servidor local.
- Piloto r3: H1 teve saída inválida; H17 produziu resposta, mas citou informação
  incidental histórica de H18/H19 sem delimitação suficiente. H22 foi interrompida.
- Piloto de perguntas menores: H1 interrompida por disputa de recursos; H17/H22
  não executadas após encerramento do servidor próprio. Inputs e falhas preservados
  em `bounded-pilot-r1`; isso não é reprovação semântica dessas duas perguntas.

A interpretação livre ainda não passou na validação geral. Não converter as
leituras literais aprovadas em aprovação dessa capacidade. Não houve backtest novo,
reabertura de protocolo, operação financeira ou evidência de lucro futuro.


### Verificação instalada da revisão /12

Em `literal-studies-r4-installed`, H1/H17/H22 passaram em QA e na coleção
principal; os seis workflows registraram zero chamadas de modelo. IDs no principal:
`stocks-literal-r4-20260916-H1`, `stocks-literal-r4-20260916-H17` e
`stocks-literal-r4-20260916-H22`. Não são novos experimentos do Stocks.

Atalhos e configuração local apontam para
`C:/CAIN/work/stocks-study-20260915/runtime-r3/Scripts/python.exe`.
`runtime-r3-verification.json` confere os 71 arquivos de produto entre código,
wheel e instalação; SHA256 do wheel:
`5c79a82a19ea81c33461cb7dcf46ecf09ade3d3f2d81a8d68079b85b9204e480`.
`activation-r3-receipt.json` e `activation-r3-backup` preservam a troca de atalhos.
O runtime intermediário r2 não foi ativado: sua verificação detectou diferença de
bytes após preservação dos finais de linha do código, exigindo nova construção.

Suíte local: 868 aprovados, 1 pulado e 1 timeout de 30 segundos no teste
`test_abrupt_process_exit_preserves_commit_boundary[after_history]` durante
pressão de recursos. Reexecução do arquivo completo: 10 aprovados. O teste novo
de seleção integra os oito testes de identidade aninhada aprovados. Ruff e
`git diff --check` passaram. Logs locais preservam inclusive o timeout.


## Fechamento técnico e limite de uso — 16/09/2026

A [PR #5](https://github.com/leonardosovienski/cain/pull/5) foi integrada na main
`e8eb3c1961c60c98b8d10388daf1599281f2f3c5`. CI de push `35150278288` e de PR
`35150304553` aprovadas nas quatro versões Python 3.11–3.14, com suíte completa,
Ruff e verificação do wheel instalado fora do checkout.

`primary-final-verification.json` confirma o runtime instalado, os 71 arquivos,
88 registros recebidos e trechos recuperáveis para 22/22 identidades H1–H22.
Não comprova que todo insumo do produtor foi recebido. Workflows antigos sem
processo vivo foram conciliados como cancelados, sem apagar etapas ou evidências.

### Piloto real encerrado: 3 respostas, 0 aprovações semânticas gerais

O piloto `bounded-pilot-r3` usou qwen3.5:4b, temperatura 0, seed 42, contexto 6144,
768 tokens máximos e `think=false`. Entradas, respostas brutas, metadados, hashes
e avaliação manual estão preservados. As três respostas passaram no formato,
mas a comparação semântica identificou:

| Caso | Limite observado |
|---|---|
| H1 | Omitiu `INCONCLUSIVE_METHOD` e não preservou claramente a distinção entre veredicto histórico e confiabilidade |
| H17 | Contexto final reteve somente a revisão 2; resposta não cobre ambas e amplia a ausência de evidência além dos trechos selecionados |
| H22 | Preservou 24/22/2 avaliações e 11 pares, mas confundiu incremento negativo com critério de lucro absoluto e validação futura com motivo histórico |

A tentativa anterior com contexto 4096 foi barrada antes da inferência pelo
limite conservador de entrada (3072 bytes após reservas); não entra como chamada
real. A tentativa interrompida por concorrência também permanece no denominador
de tentativas. O servidor próprio foi encerrado ao final; nenhuma automação criada.

**Uso validado nesta entrega:** leitura literal dos campos testados, consulta de
fontes e registro rastreável. **Ainda não aprovado:** estudo autônomo com conclusões
livres do modelo, generalização de desempenho econômico ou execução de backtests.
O próximo incremento precisa balancear revisões no contexto final e validar
explicações causais; as falhas semânticas acima não são declaradas corrigidas.
Nenhum resultado científico, banco do produtor, protocolo ou arquivo local foi apagado.
