# Continuação da avaliação v2: conversa cotidiana

## Resultado e escopo

Houve melhora verificável na cópia educada já recusada, no cálculo, nas três linhas, na extração e em episódios naturais de declaração/recordação. A classe de cópia literal ainda não está aprovada. A candidata permanece parcial. A regressão de referência da instalação QA correta teve 11 passes, duas parciais e uma falha em 14 tentativas. A confirmação nova teve seis passes, cinco falhas e três parciais em 14 tentativas concluídas; não houve erro operacional nesse conjunto. As retificações e continuações anteriormente recusadas também foram reproduzidas em regressão UTF-8 correta, separada da confirmação. Não se aprova conversa irrestrita nem todo o conhecimento dos predictors. A instalação principal não recebeu esta candidata.

As causas foram investigadas nos bytes efetivos do classificador e do gerador. Uma tentativa inicial de corrigir a extração atuou no agente errado; esse diagnóstico foi corrigido e os ensaios foram preservados. O wheel final foi instalado de forma não editável em uma nova instalação QA fora do checkout, com identidade CAIN conferida e com lançamento sem `PYTHONPATH` e armazenamento efetivo atestado. Os resultados de uso e interface constam nas matrizes abaixo; instalar não equivale a aprovar todos os casos.

Este incremento continua a [avaliação v2](EVALUACAO_V2_20260914.md), usando seus IDs, executores, gabaritos e controles. Não houve auditoria geral, sincronização, alteração de arquitetura, branch, produtor, Core ou Ops. As questões sobre todas as hipóteses continuam sem comprovação de cobertura integral. O catálogo ampliado de 92 fontes permanece em QA; documentos, trials e revisões não são totais de hipóteses únicas.

## Identidades e preservação

`R = C:/CAIN/work/conversation-v2-20260914`. Checkout: `C:/CAIN/projeto`, `main`, HEAD `3f88a2535f08c70bce561cd3822e7558cebec326`. O baseline continha 24 arquivos modificados/não rastreados, copiados e identificados em `R/baseline.json` e `R/baseline`. A composição inclui as alterações anteriores de pesquisa, que permaneceram inalteradas neste incremento; não se apresenta o wheel como uma correção somente do router.

A primeira candidata congelada, seu wheel e sua instalação QA foram preservados. A confirmação prevista para ela teve **zero tentativas**, pois o diagnóstico de B09 foi corrigido antes de iniciar essa série. A suíte offline iniciada nesse ponto foi interrompida junto com a orquestração, em 9% de progresso; não é uma suíte aprovada nem falha do produto. Os recibos estão em `pipeline-paused.json`, `interrupted-suite.json` e `full-tests.log`.

A candidata final está em `candidate-final-freeze.json`: identidade dos arquivos `6a567dd387e66121a120c15a8c4ed1e21a402505f3b9d8405e9d94490073a747`. Wheel `wheel-final/cain_research-0.4.12-py3-none-any.whl`, SHA-256 `a7b7cfd4d240942150375ae0a6324c9ab9ce1b0dbea8639ccad057fa4e5e77d8`. A versão textual continua 0.4.12; os hashes distinguem esta candidata da instalação principal e dos wheels anteriores. Não é uma release promovida.

Primeira instalação da fonte final: `R/installed-qa-final/Lib/site-packages/cain`. A CLI revelou dependências históricas divergentes apesar dos mesmos números de versão. Essa série não comprova a combinação canônica; seus recibos foram preservados. Instalação corrigida: `R/installed-qa-matched/Lib/site-packages/cain`, em outro ambiente novo, sem alterar o CAIN congelado. `matched-stack-freeze.json` confere também os bytes de Bundle e Snapshot contra os wheels canônicos e a principal; a CLI e `cain.archive` abrem corretamente. Setenta arquivos foram comparados byte a byte com o wheel e a fonte congelada. `pip check` passou. Configuração, armazenamento, política, documentos e índices de API e interface usam raízes QA novas, atestadas pelo executor. A pesquisa recebeu uma cópia SQLite consistente do arquivo QA anterior, com os mesmos grants e catálogo; mudou apenas a raiz de importação para o novo inbox QA. Nenhum banco pessoal foi conectado ao corpus de teste.

Backend local existente: qwen3.5:4b, temperatura 0, seed 42, think=false, num_ctx 8192, num_predict 768, limite de entrada 6500 bytes e timeout de geração 240 s. Embeddings: qwen3-embedding:0.6b. Não houve download de modelo, treinamento, troca de pesos ou contratação. As portas próprias são 11435/11436/8896. Repetições podem aproveitar cache de contexto do backend, mas cada inferência efetiva e seus contadores estão registrados. Não houve comparação controlada de latência.

## Correções e causalidade

| Etapa | Evidência anterior | Alteração e resultado comprovado | Limite |
|---|---|---|---|
| 1 — conteúdo | B07 perdia as linhas; B08 perdia a palavra entre aspas; outros pedidos perdiam objeto/escopo no `instruction_head`. B04 ainda era legível. | O classificador passa a receber o payload original completo, sem o corte silencioso de 1000 caracteres. O orçamento do provider continua explícito. | B04/B07/B08/M02 ainda foram recusados nessa etapa: preservação isolada não bastou. |
| 2 — classificação | Mesmo com o conteúdo íntegro, o classificador recusava atividades compatíveis com capacidades já registradas. `conversa` já existia no schema. | Contrato de classificação esclarece declarações, exercícios, extração, restrições de saída e quando pedir esclarecimento. B04/B07/B08 e os episódios de memória passaram a avançar. | Não troca modelo, não força intenção e não encaminha todas as tarefas para conversa; resumo, busca e código continuam selecionáveis. |
| 3 — cálculo | B05 passou pela rota, mas a geração respondeu `0` quando o resultado era `34`. | Parser limitado de sequências numéricas completas, com operações e números variáveis, cálculo racional e limites. Caso responde `34`, origem determinística, também pela CLI. | Não é um solucionador universal de matemática em linguagem natural; não usa `eval` nem respostas constantes dos testes. |
| 4 — tentativa de formato | B09 devolvia `O nome do projeto é **Atlas**.` | Foi adicionada orientação de extração na conversa, mas o caso continuou falhando. | O diagnóstico inicial estava errado: a rota efetiva era **resumo**, e a orientação não alcançava esse gerador. Não se atribui essa repetição à incapacidade do modelo de obedecer à nova orientação. |
| 5 — pergunta curta com contexto | Após X=10 e atualização X=27, `Qual é o valor?` era recusado antes de chamar o classificador. | Perguntas sem assunto autossuficiente podem usar o contexto já filtrado da identidade/sessão. O episódio completo respondeu `X = 27` com geração real. | O repasse ficou limitado a essa classe de perguntas; a confirmação encontrou retificação sem contexto no classificador, ainda recusada. |
| 6 — caminho real da extração | Capturas mostram seleção `resumo`, payload completo e resposta bruta com rótulo/Markdown. Três repetições continuaram falhando. | Orientação genérica de saída explícita acrescentada ao agente de resumo. B09 passou 3/3, sem mudar sua rota ou pós-processar a resposta. B12 e M09 preservaram seus fatos. | A confirmação mostrou outra rota, **código**, produzindo cercas em pedido de JSON puro. Não se generaliza o conserto de resumo a todos os agentes. |

O instrumento v2 também passou a marcar contagem de inferência como desconhecida quando o observador não comprova encaminhamento, mesmo que existam recibos e despachos em quantidades iguais. Isso evita chamar timeout de zero inferências. Os hashes do instrumento, além da string `v2-runner/4`, identificam a revisão efetivamente consumida. Recibos anteriores não foram reescritos.

## Exemplos verificáveis

Pedido: `Por favor, retorne somente: Boa viagem.` Resposta final: `Boa viagem.` Passou 3/3 no desenvolvimento e novamente no wheel instalado.

Pedido: `Comece com 13, some 7, multiplique por 2 e subtraia 6. Responda apenas com o resultado.` Antes do cálculo limitado: `0`. Depois: `34`, sem inferência para o cálculo.

Pedido: `Texto: "Projeto Atlas foi criado em 2024 por Marina e utiliza Python." Retorne apenas o nome do projeto.` Antes: `O nome do projeto é **Atlas**.` Depois da correção no agente realmente usado: `Atlas`, 3/3, e novamente no wheel instalado.

Episódio: `Neste exercício fictício, X = 10.` → `X = 10`; `Atualização do mesmo exercício: agora X = 27.` → `X = 27`; `Qual é o valor?` → `X = 27`. O dado entrou pela conversa, não por escrita direta no banco. Na pergunta original que pede atual/anterior, a resposta ainda oferece os registros históricos; recuperação e síntese temporal ficam separadas.

O probe anterior foi acrescentado como quarto turno ao episódio já realizado na etapa 2; o posterior usou um episódio novo de três turnos com as mesmas duas premissas. Não é replay byte a byte do mesmo histórico. O bloqueio anterior ao classificador foi identificado no código e no recibo sem chamada; o acerto posterior é uma execução real adicional, com seu contexto próprio preservado.

Primeira confirmação, na montagem com dependências divergentes — JSON: `Escreva um objeto JSON puro com somente estes campos: local deve ser null e tentativas deve ser o inteiro 2.` O classificador selecionou `codigo`; a resposta bruta foi:

````text
```json
{
  "local": null,
  "tentativas": 2
}
```
````

Os campos e tipos estão corretos, mas a resposta completa não é JSON puro. As cercas não foram removidas para aprovar o teste. O payload chegou íntegro; esta não é outra perda de conteúdo demonstrada.

Na confirmação de atualização, a declaração de 22 caixas foi aceita. `Retificação para este cenário: o estoque considerado agora é de 35 caixas.` recebeu HTTP 422; o classificador respondeu `clarify`, alegando falta de tarefa. A entrada contém os 35, mas não contém o contexto da sessão. A presença do texto no armazenamento ou no recibo não comprova atualização utilizada corretamente. A pergunta final não foi executada nos episódios interrompidos.

Na confirmação de continuação, a comparação de Norte (20 reais) e Sul (32 reais), para quatro entregas, foi aceita. `Explique com mais detalhes.` recebeu HTTP 422. A decisão do classificador diz depender do contexto anterior, mas esse contexto não foi incluído em sua entrada efetiva. O código só o repassa nesse fallback quando a mensagem corresponde à classe de perguntas. Essa lacuna está demonstrada; não se afirma que repassar contexto, sozinho, já tenha sido testado como solução para essas duas novas formas.

Em M11, com somente o documento Cedral, a pergunta sobre Lunar recebeu o trecho `CEDRAL-615`, sem abstenção. Na variante com fonte Lunar disponível, `LUNAR-294` apareceu na primeira fonte e Cedral na segunda. Isso comprova recuperação positiva no recorte, mas mantém a falha do controle de ausência. Não é fonte inventada nem vazamento; é relevância inadequada para a pergunta.

## Validação técnica e limites da revisão

Suíte completa final: **768 aprovados, 1 ignorado, 2 avisos**, em 119,50 s. Ruff passou. O teste ignorado depende de privilégio de symlink no Windows. Os testes focados anteriores (73, 97, 19 e 129 aprovados em suas respectivas fases) se sobrepõem; não são somados como testes únicos. Mocks, fixtures e verificações estáticas não contam como inferência real.

Cada conjunto de confirmação executado tem oito casos e 14 tentativas predefinidas: B03/B09/M02 com três repetições; os demais com uma. Cada repetição usa identidade/estado novos e mantém continuidade apenas dentro do episódio. Um catálogo anterior à etapa 6 foi preservado com zero tentativas. Depois houve uma confirmação na montagem de dependências divergentes e outra, com casos novos, após conferir e congelar a combinação corrigida. Os casos foram criados depois do congelamento pelo mesmo agente que implementou e revisou: **não há independência ou cegamento**. As falhas não foram excluídas nem usadas para modificar esta candidata durante a confirmação.

Os controles de autorização, supersessão, idempotência, conflito/rollback, cancelamento e revogação usam serviços reais em QA, sem modelo. Os controles HTTP verificam estado de preferências, precedência, expiração e isolamento documental. Isso não certifica segurança adversarial universal, autenticação remota, todos os idiomas, crash no meio de transação ou toda a interface. Memória conversacional e adesão da geração são avaliadas separadamente nos episódios reais.

## Arquivos e reversão

Alterações deste incremento: `src/cain/orchestrator/routing.py`, `src/cain/orchestrator/__init__.py`, `src/cain/agents/arithmetic.py`, `src/cain/agents/__init__.py`, `src/cain/evaluation/v2.py`; testes em `tests/unit/test_agent_evidence_routing.py`, `tests/unit/test_arithmetic_sequences.py` e `tests/evaluation/test_v2.py`. Documentação: este relatório, continuidade, índice, referência na v2 anterior e nota de identidade em LOCAL_INSTALLATION.md. As alterações anteriores de pesquisa e seus testes foram preservadas.

Compare `increment-final.diff`, `increment-tests.diff`, os diffs de cada etapa e os backups seletivos em `R/baseline`. Para reverter, confira antes se os hashes ainda são os da candidata congelada; se houver trabalho posterior, reverta somente os hunks deste incremento. Os arquivos de produto anteriores estão em `R/baseline/package/cain`; os testes modificados anteriormente estão em `R/baseline/tests`. O novo teste de sequências pertence somente a esta rodada. Não use reset global, não restaure bancos e não apague recibos. A principal não precisa de reversão desta candidata porque não a recebeu.

Os comandos e resultados completos ficam em `COMMANDS.md` e nos logs indicados. O pacote sanitizado contém entradas, respostas, chamadas efetivas, fontes sintéticas mínimas, gabaritos, manifestos e revisão manual. Bancos, políticas completas, perfis pessoais e listas de tokens brutos não são compartilhados. Os hashes originais identificam recibos privados; a sanitização não promete replay byte a byte.

## Erro de montagem do QA preservado

`installed-qa-final` consumiu wheels históricos em `bundle-validation/wheels`. O número Bundle 1.0.0 não distinguia esse artefato do canônico. `pip check` passou, mas a CLI encerrou antes da tarefa com `ImportError: cannot import name safe_mkdirs`. Isso é falha da montagem deste ensaio, não evidência de defeito atual no Core ou na principal. A declaração M06 não ocorreu; recordação vazia e controle de outro usuário dessa série são inconclusivos, não aprovações de memória/isolamento. O primeiro ensaio M12 também parou nesse import, antes de testar o backend, apesar do texto genérico do recibo. A revisão manual corrige essa atribuição sem sobrescrever o original.

A montagem corrigida usa os artefatos de `C:/CAIN/entregas/stocks-main-integration-20260912`: Bundle SHA-256 `7c5792e6573d55af92fd9b50cd9a2c357052b7673a61eef8abdaeaeef401ebee` e Snapshot `5e62cdf6ea7790a9e4beb0b3dd874a9a40c54cbd97e69e5a8408e88f8f22ec1a`. A fonte CAIN não mudou. Em M12 corrigido, a CLI retornou erro explícito de Ollama indisponível e exit 1 na porta QA fechada, sem resposta fabricada. Isso testa conexão recusada, não corte no meio do streaming.

## Defeito de codificação no instrumento

A primeira repetição `qa-installed-matched/runs/known-failures` leu o catálogo original com codificação padrão do Windows. M02 chegou com acentos corrompidos (`RetificaÃ§Ã£o`), portanto não é comparação equivalente com a recusa anterior. As tentativas e os bytes enviados permanecem no pacote e no denominador, marcados como instrumento inválido para essa comparação. B06 era ASCII e repetiu a falha de cercas, mas não se usa a série inteira como aprovação. `instrument-encoding-incident.json` identifica as diferenças. O catálogo `known-failure-utf8-catalog.json` foi conferido contra as mensagens originais, sem mudar o CAIN; o novo ensaio usa outro run_id. Todas as mensagens da confirmação nova foram verificadas como UTF-8 correto, sem modificação do conjunto congelado.

Na montagem divergente, `/research/coverage` também falhou com HTTP 500 pelo import de `safe_mkdirs`. O executor de pesquisa preservou a resposta `Internal Server Error`, mas não conferiu esse status ao marcar a execução do workflow como concluída. A revisão separa agora conclusão das três etapas de funcionamento do diagnóstico de cobertura; o recibo antigo não aprova esse endpoint. Na montagem com os artefatos corretos, o diagnóstico retorna objeto de cobertura. Nenhuma conclusão sobre cobertura integral decorre disso. O código congelado do executor não foi alterado após confirmação; esta limitação do instrumento e a conferência manual ficam explícitas.

## Confirmação na combinação correta

A cópia `Retorne exatamente o texto entre aspas, preservando sua pontuação: "Bem-vinda, equipe." Obrigado.` devolveu `"Bem-vinda, equipe."` com delimitadores nas três tentativas. O classificador recebeu a instrução original completa e escolheu resumo; não se atribui essa falha à perda de payload. A extração de Estação Azul passou 3/3, enquanto a nova formulação de JSON puro voltou a produzir cercas. Os cálculos 84/10 e as três linhas passaram.

Os três episódios tanque 12→19 chegaram à recordação `Quanto há nele agora?`, sem valor na pergunta. Retornaram os trechos da atualização 19, sem uma resposta direta sobre o estado atual: parcial conforme o gabarito. A captura do classificador não contém session_context; `RuleRouter.QUESTION` não inclui essa forma, embora seja uma pergunta. O diagnóstico mostra uma limitação de classe no repasse de contexto, não justifica acrescentar apenas mais uma expressão.

Na comparação Lago 42/Serra 54 para seis tarefas, `Pode desenvolver essa comparação?` recebeu HTTP 200 com recusa: exige informações não financeiras, embora a média por tarefa 7/9 pudesse ser calculada. O classificador, sem contexto, escolheu resumo e produziu uma justificativa internamente contraditória; o gerador recebeu a comparação anterior no contexto de identidade, mas recusou aprofundá-la. É falha semântica após encaminhamento, não erro operacional. Uma mudança no router, sozinha, não foi demonstrada como solução dessa geração.

A repetição equivalente das falhas antigas ficou em `qa-ui-matched/runs/known-failures-utf8`, caminho C: cinco tentativas, uma resposta concluída porém reprovada (JSON) e quatro erros nominais (três retificações e uma continuação). As três perguntas finais de recordação não foram executadas após as recusas. Não se afirma que o valor 35 tenha sido apagado ou nunca registrado; o que falhou foi o episódio de uso. O conjunto com texto corrompido permanece separado e inválido para essa comparação.

## Instalação, CLI, memória e controles

O wheel foi instalado fora do checkout, sem modo editável, e usado pela API, pela CLI real e pelo navegador QA. A nova CLI declarou NUVEM-563 com exit 0; uma sessão diferente recuperou a declaração real e outro usuário recebeu ausência de evidência. Foram cinco pedidos no suplemento: cinco concluídos/revistos, aprovados somente no recorte. Os dois exemplos gerados de preferência obedeceram inglês de usuário e português de turno. Isso não aprova todos os idiomas, preferências ou formas de memória livre. Não houve inserção direta de canário em banco.

Os seis controles de serviço (A04/A10/M07/M08/A09/A11), o grupo HTTP de preferências/isolamento e o teste de backend indisponível passaram na instalação correta, sem geração nos controles de serviço. Os dados sintéticos entram pelos serviços previstos; esses testes não substituem os episódios naturais de memória. A primeira montagem divergente falhou antes da declaração CLI e não constitui controle negativo válido de recordação.

## Denominadores por série

Casos são entradas de catálogo; famílias são capacidades v2. Julgados conta tentativas concluídas revistas; erros operacionais permanecem no denominador, sem qualidade semântica inventada. Parcial não é aprovação. Controles e interface têm denominadores separados.

| Série | Casos/famílias | Planejadas/tentadas | Concluídas/julgadas | Passa/falha/parcial | Pendente | Erro operacional / instrumento inválido | Gerações observadas / turnos desconhecidos |
|---|---:|---:|---:|---:|---:|---:|---:|
|qa-baseline/runs/baseline-basic|2/2|2/2|0/0|0/0/0|0|2/0|2/0|
|qa-installed-final/runs/confirmation|8/8|14/14|10/10|9/1/0|0|4/0|29/0|
|qa-installed-final/runs/installed-regression|14/13|14/14|14/14|12/1/1|0|0/0|17/0|
|qa-installed-matched/runs/confirmation|8/8|14/14|14/14|6/5/3|0|0/0|36/0|
|qa-installed-matched/runs/installed-regression|14/13|14/14|14/14|11/1/2|0|0/0|17/0|
|qa-installed-matched/runs/known-failures|3/3|5/5|4/0|0/0/0|0|1/5|17/0|
|qa-stage1/runs/content-only|4/4|4/4|0/0|0/0/0|0|4/0|4/0|
|qa-stage2/runs/classifier-contract|9/9|9/9|9/9|6/2/1|0|0/0|25/0|
|qa-stage5/runs/everyday-regression|26/23|36/36|36/36|32/2/2|0|0/0|52/0|
|qa-stage5/runs/output-stability|1/1|3/3|3/3|0/3/0|0|0/0|6/0|
|qa-stage5/runs/presence-pair|1/1|1/1|1/1|1/0/0|0|0/0|0/0|
|qa-stage5/runs/short-context-after|1/1|1/1|1/1|1/0/0|0|0/0|6/0|
|qa-stage6/runs/extraction-path|1/1|3/3|3/3|3/0/0|0|0/0|6/0|
|qa-stage6/runs/summary-regressions|2/2|2/2|2/2|2/0/0|0|0/0|3/0|
|qa-ui-matched/runs/known-failures-utf8|3/3|5/5|1/1|0/1/0|0|4/0|13/0|

A confirmação inicial `confirmation-catalog.json` foi preparada e não executada (14 planejadas, zero tentadas); não foi substituída silenciosamente por uma série aprovada. A primeira montagem instalada da fonte final tinha dependências divergentes. Seu nome de pasta `qa-installed-final` é histórico, não uma aprovação.

## Matriz preservada das 36 famílias

Baseline = avaliação v2 e reproduções anteriores identificadas; desenvolvimento não significa aprovação instalada. C = API/CLI, D = navegador real. Passa significa apenas o contrato dos casos realizados. Geração LLM, resposta determinística e recuperação literal são discriminadas por turno nos recibos.

| Família/capacidade | Antes | Desenvolvimento | Instalação QA correta, C | Interface D | Confirmação nova | Evidência |
|---|---|---|---|---|---|---|
|B01 Saudação|Passava|Passa; determinístico|1 passa|B01: passa no recorte|Fora deste conjunto|attempts.jsonl + manual-review.json; interface-evidence.json|
|B02 Variantes de saudação|Passavam no recorte|3 variantes passam; opa gera resposta|Não reexecutado instalado nesta continuação|Não executado|Fora deste conjunto|attempts.jsonl + manual-review.json|
|B03 Literal|Original corrigido; educada recusada|Original e educada passam 3/3|2 passa|B03-polite: passa no recorte|3 falha|attempts.jsonl + manual-review.json; interface-evidence.json|
|B04 Multiplicação|Recusada; direto 133|133, 3/3; geração real|1 passa|B04: passa no recorte|1 passa|attempts.jsonl + manual-review.json; interface-evidence.json|
|B05 Sequência|Recusada; depois respondeu 0|34 determinístico; gramática limitada|1 passa|B05: passa no recorte|1 passa|attempts.jsonl + manual-review.json; interface-evidence.json|
|B06 JSON|Original passava|Original 3/3; nova forma com cercas falha|1 passa; 1 falha|B06: passa no recorte; B06-known: reprovado|1 falha|attempts.jsonl + manual-review.json; interface-evidence.json|
|B07 Três linhas|Recusada|Linhas exatas|Não reexecutado instalado nesta continuação|Não executado|1 passa|attempts.jsonl + manual-review.json|
|B08 Palavra proibida|Recusada|Concorda sem palavra proibida|Não reexecutado instalado nesta continuação|Não executado|Fora deste conjunto|attempts.jsonl + manual-review.json|
|B09 Extração|Recusada; depois rótulo extra|Após corrigir agente resumo: Atlas 3/3|1 passa|B09: passa no recorte|3 passa|attempts.jsonl + manual-review.json; interface-evidence.json|
|B10 Informação ausente|Abstenção no recorte vazio|Abstenção no recorte vazio|1 passa|B10: passa no recorte|Fora deste conjunto|attempts.jsonl + manual-review.json; interface-evidence.json|
|B11 Regra fictícia|Passava no recorte|5, premissa fictícia preservada|Não reexecutado instalado nesta continuação|Não executado|Fora deste conjunto|attempts.jsonl + manual-review.json|
|B12 Resumo PT|Passava|Horário, caderno e ausência de transmissão preservados|1 passa|B12: passa no recorte|Fora deste conjunto|attempts.jsonl + manual-review.json; interface-evidence.json|
|M01 Declaração e recordação|Declaração recusada|3 episódios; recordação literal correta|1 passa|M01: passa no recorte|Fora deste conjunto|attempts.jsonl + manual-review.json; interface-evidence.json|
|M02 Atualização|Declaração recusada|Episódio original completo, síntese temporal parcial; pergunta curta X27 passa; retificação nova recusa|1 parcial; 3 erro nominal|M02: parcial; M02-known: erro nominal|3 parcial|attempts.jsonl + manual-review.json; interface-evidence.json|
|M03 Distrações|Declaração recusada|7 turnos completos e VELA-482 recuperado|Não reexecutado instalado nesta continuação|Não executado|Fora deste conjunto|attempts.jsonl + manual-review.json|
|M04 Continuação|Timeout histórico; depois passava|Forma original passa; outra continuação recusa|1 parcial; 1 erro nominal|M04: parcial; M04-known: erro nominal|1 falha|attempts.jsonl + manual-review.json; interface-evidence.json|
|M05 Preferências|Controles de estado passavam|Controles HTTP; geração en/pt no suplemento|HTTP estado passa; geração no suplemento|Não executado|Fora deste conjunto|controls.json / cli-api-memory-preferences.json|
|M06 Entre sessões|Somente documento/preferência comprovados|Ver suplemento natural CLI/API; import falhou na montagem divergente|Suplemento natural CLI/API; ver resultado abaixo|M06: passa no recorte|Fora deste conjunto|controls.json / cli-api-memory-preferences.json; interface-evidence.json|
|M07 Outro usuário|Controle documental passava|Controles de serviço/HTTP; memória natural separada|Controles serviço/HTTP; suplemento natural|M07: passa no recorte|Fora deste conjunto|controls.json / cli-api-memory-preferences.json; interface-evidence.json|
|M08 Outro projeto|Controle documental passava|Controles de serviço/HTTP|Controles serviço/HTTP passam|Não executado|Fora deste conjunto|controls.json / cli-api-memory-preferences.json|
|M09 Fato e opinião|Recusada|Brier relatado 0,62 separado de opinião|Não reexecutado instalado nesta continuação|Não executado|Fora deste conjunto|attempts.jsonl + manual-review.json|
|M10 Documento presente|Cedral correto|Cedral código/prazo correto|1 passa|Não executado|Fora deste conjunto|attempts.jsonl + manual-review.json|
|M11 Entidade ausente|Cedral indevido para Lunar|Ausência continua falhando; presença Lunar recupera|1 falha|Não executado|Fora deste conjunto|attempts.jsonl + manual-review.json|
|M12 Backend indisponível|Erro explícito na CLI histórica|Nova CLI com stack correto: erro explícito; sem streaming parcial|CLI/backend fechado: erro explícito esperado, passa|Não executado|Fora deste conjunto|controls.json / cli-api-memory-preferences.json|
|A01 Crypto H4|Síntese parcial/reprovada|Regressão real; ver matriz por predictor|parcial/reprovado; Preserva H4 CLOSED_INSUFFICIENT_SAMPLE, n=5, decisão por risco de cota e ausência de veredito. Extrapola para ausência de resultado observável apesar das cinco observações.|Não executado|Fora deste conjunto|research-evidence.json + research-review.json|
|A02 Stocks prontidão|Reprovada semanticamente|Regressão real; ver matriz por predictor|reprovado; Mantém não aptidão, mas não reconcilia H17-H19 históricas com H17 observada; chama exit code 2 de sucesso apesar de indicar falha.|Não executado|Fora deste conjunto|research-evidence.json + research-review.json|
|A03 BR claim|Parcial/reprovada|Regressão real; ver matriz por predictor|parcial/reprovado; Preserva BLOCKED_PENDING_PIT_FEATURES, nenhuma comparação e nenhum efeito demonstrado; apresenta enunciado sem marcar hipótese e confunde features com recursos, ampliando justificativa causal.|Não executado|Fora deste conjunto|research-evidence.json + research-review.json|
|A04 Revisões|Controle passava|Supersessão/ordem em serviço real|Serviço real passa|Não executado|Fora deste conjunto|controls.json / cli-api-memory-preferences.json|
|A05 Sem cabeçalho|Qualificação inventada/timeout|Abstenção com exclusão categórica não sustentada; parcial reprovada|Não reexecutado instalado nesta continuação|Não executado|Fora deste conjunto|attempts.jsonl + manual-review.json|
|A06 Com cabeçalho Brier|Interpretação errada|Uma resposta delimitada correta; não resolve Brier em geral|Não reexecutado instalado nesta continuação|Não executado|Fora deste conjunto|attempts.jsonl + manual-review.json|
|A07 Recorte|Literal correto|Ausência econômica preservada; retrieval_only|Não reexecutado instalado nesta continuação|Não executado|Fora deste conjunto|attempts.jsonl + manual-review.json|
|A08 Injeção documental|Literal sem alteração de GO|Literal sem efeito; sem geração adversarial|Não reexecutado instalado nesta continuação|Não executado|Fora deste conjunto|attempts.jsonl + manual-review.json|
|A09 Autorização|Controle passava|Importação não autorizada negada|Serviço real passa|Não executado|Fora deste conjunto|controls.json / cli-api-memory-preferences.json|
|A10 Reprocessamento|Controle passava|Idempotência e conflito/rollback em serviço real|Serviço real passa|Não executado|Fora deste conjunto|controls.json / cli-api-memory-preferences.json|
|A11 Workflow|Controle passava|Reabertura, cancelamento, revogação; semântica separada|Serviço real passa|Não executado|Fora deste conjunto|controls.json / cli-api-memory-preferences.json|
|A12 Utilidade|2 fatos corretos em 3 braços|Não reexecutado nesta continuação; histórico v2 preservado|Não reexecutado instalado nesta continuação|Não executado|Fora deste conjunto|attempts.jsonl + manual-review.json|

## Matriz separada dos predictors

A01/A02/A03 reutilizam os gabaritos da v2 e o arquivo QA autorizado. Antes = v2 histórica com checkout acumulado, não pacote principal certificado. Depois = wheel composto congelado, instalado com dependências canônicas. As alterações de pesquisa preexistentes não mudaram nesta continuação. Cada caso executou inspect → search → support, com uma geração e reabertura do checkpoint; challenge/synthesis não foram executados. Os resultados não são atribuídos causalmente ao router.

| Predictor/caso | Fontes, versão e período | Conhecimento necessário examinado | Cobertura e acesso comprovados | Antes/depois e qualidade | Dependência externa / limite |
|---|---|---|---|---|---|
|Brasileirão / CLAIM-BR-MARKET-001|EVIDENCE_REGISTRY.md; f87806900d2aa3c5e267259a67f27ce56e18dc03; H-24h, temporada 2026, EXP-001 → H24|Objetivo incremental versus mercado; natureza de hipótese; bloqueio PIT, nenhuma comparação executada, odds 245/245 sem multitemporadas, três snapshots antigos. Artifacts somente referenciados não foram materializados.|82 revisões recebidas; preflight retorna 1 registro; 3 citações literais conferidas. /research/coverage HTTP 200; repository_coverage=not_established; workflow_input=snapshots_only.|Falha semântica já documentada na v2; persiste na candidata instalada. Preserva BLOCKED_PENDING_PIT_FEATURES, nenhuma comparação e nenhum efeito demonstrado; apresenta enunciado sem marcar hipótese e confunde features com recursos, ampliando justificativa causal.|Nenhuma mudança externa necessária para o fix de conversa. Para completude/atualidade: publicação canônica versionada, escopo e relações temporais/supersessão explícitos quando ausentes; não implementado no produtor nesta tarefa. Não reproduz experimentos nem certifica todo o projeto.|
|Crypto / H4|scientific_state.json e EVIDENCE_REGISTRY.md; 4eb96e141389b8390536716af3c4a0cb46edab23; histórico H4 e errata 07/09/2026|Hipótese Score LLM prevê D+7; CLOSED_INSUFFICIENT_SAMPLE, n=5, trial v2-dpl-gemini-h7, interrupção por decisão de cota; sem veredito. Não inferir ausência de toda observação nem refutação.|89 revisões recebidas; preflight retorna 12 registros; 10 citações literais conferidas. /research/coverage HTTP 200; repository_coverage=not_established; workflow_input=snapshots_only.|Falha semântica já documentada na v2; persiste na candidata instalada. Preserva H4 CLOSED_INSUFFICIENT_SAMPLE, n=5, decisão por risco de cota e ausência de veredito. Extrapola para ausência de resultado observável apesar das cinco observações.|Nenhuma mudança externa necessária para o fix de conversa. Para completude/atualidade: publicação canônica versionada, escopo e relações temporais/supersessão explícitos quando ausentes; não implementado no produtor nesta tarefa. Não reproduz experimentos nem certifica todo o projeto.|
|Stocks / prontidão|STOCKS_CURRENT_STATE.md e INTEGRATION_AUDIT_20260912.md; 3066321e599ee15dd0ace4167d2791545ce6eb95; setembro de 2026 e protocolo prospectivo até sessão em/após 10/09/2027|Prontidão pessoal/econômica separada de engenharia; custos, eventos, cenário pessoal; H17 observada versus registros antigos, H18/H19 bloqueadas; exit 2 é falha, não sucesso.|74 revisões recebidas; preflight retorna 1 registro; 10 citações literais conferidas. /research/coverage HTTP 200; repository_coverage=not_established; workflow_input=snapshots_only.|Falha semântica já documentada na v2; persiste na candidata instalada. Mantém não aptidão, mas não reconcilia H17-H19 históricas com H17 observada; chama exit code 2 de sucesso apesar de indicar falha.|Nenhuma mudança externa necessária para o fix de conversa. Para completude/atualidade: publicação canônica versionada, escopo e relações temporais/supersessão explícitos quando ausentes; não implementado no produtor nesta tarefa. Não reproduz experimentos nem certifica todo o projeto.|

**Recebido não significa utilizado integralmente.** Os documentos autorizados estão disponíveis no catálogo QA, mas o workflow usa somente snapshots e excertos selecionados. Metadados Bundle e artefatos apenas referenciados não equivalem aos corpos desses artefatos no contexto. Fontes não inventariadas, bancos operacionais, cohorts protegidos, credenciais e configuração pessoal ficam excluídos. O estado de validação e as datas da informação são os declarados nas fontes; relógios desconhecidos não são substituídos por ingestão.

**Manutenção:** inventário/hashes, diagnóstico de cobertura, revisões/supersessão, trilha de importação e controles reais de idempotência foram reaproveitados. Chegadas fora de ordem e reprocessamento idêntico preservam o histórico nos controles delimitados. Nenhuma sincronização nova ou ampliação de catálogo foi feita. O manifesto de 92 fontes é curadoria local parcial e não prova total de hipóteses únicas; a principal continua sem receber esse acervo. Uma fonte pode estar documentada sem estar autenticada como exportação do produtor.

Contagens desta regressão: três casos planejados/tentados/concluídos/revistos, zero aprovações integrais, três reprovações semânticas (duas com núcleo factual parcialmente correto), zero erros operacionais de workflow na montagem correta, três gerações comprovadas. A montagem divergente também concluiu workflows, mas falhou no diagnóstico de cobertura; essa falha não foi omitida.

## Interface real da instalação QA

16 casos, 13 famílias, uma tentativa por caso. Mensagens planejadas/tentadas/concluídas: **24/23/21**. Todos os 16 desfechos foram revisados; nenhuma tentativa foi descartada. Estados por episódio: 11 passa no recorte, 1 reprovado, 2 parcial, 2 erro nominal. Chamadas reais de geração observadas: 25; casos com contagem desconhecida: 0. Sem nota global de inteligência.

Caminho D: navegador em localhost:8896, perfil sintético e projeto Geral, envio pelo formulário normal. As mensagens foram digitadas na interface, nunca inseridas diretamente no banco. O readback da API apenas recupera o que o navegador já criou. Os dois turnos de M01 aparecem também no readback M06 e não são contados duas vezes. O terceiro turno planejado de M02-known não foi enviado após o erro da retificação.

| Caso | Estado | Mensagens planejadas/tentadas/concluídas | Resposta e limites |
|---|---|---:|---|
|B01|passa no recorte|1/1/1|Saudação correta, origem determinística.|
|B03-polite|passa no recorte|1/1/1|Boa viagem. exato no formulário normal.|
|B04|passa no recorte|1/1/1|133 exato, geração real.|
|B05|passa no recorte|1/1/1|34 exato, cálculo determinístico.|
|B06|passa no recorte|1/1/1|JSON puro com cidade Londrina e ativo false; chaves/valores/tipos preservados.|
|B06-known|reprovado|1/1/1|JSON bruto contém cercas Markdown; a renderização visual do bloco não satisfaz JSON puro.|
|B09|passa no recorte|1/1/1|Atlas exato, sem rótulo adicional.|
|M01|passa no recorte|2/2/2|Declaração natural ALFA-739 seguida de pergunta sem o valor; recupera a declaração real. Resposta literal de histórico, não certificação de memória geral.|
|M06|passa no recorte|1/1/1|Após recarregar e abrir Nova conversa, recupera ALFA-739. O readback inclui também os dois turnos prévios M01, que não são contados novamente. Há fontes redundantes e citações aninhadas.|
|M07|passa no recorte|1/1/1|Outro perfil recebe ausência sem fontes nem canário, após controle positivo M01/M06. Não certifica autenticação remota.|
|B10|passa no recorte|1/1/1|Código Jade ausente: abstém-se explicitamente sem inventar código.|
|B12|passa no recorte|1/1/1|Resumo em português preserva reunião às 9h, caderno e ausência de transmissão, abaixo de 20 palavras.|
|M02|parcial|4/4/4|Terceiro turno devolve histórico de X=10 e atualização X=27 sem síntese. Quarto turno Qual é o valor? responde atual 27 e anterior 10. Este quarto turno tem histórico maior que o ensaio anterior de três turnos.|
|M04|parcial|2/2/2|Comparação e explique melhor concluídos: 40/37, cinco tarefas e diferença 3 corretos. Aprofundamento omite médias 8/7,40 exigidas e chama totais de custos unitários.|
|M02-known|erro nominal|3/2/1|Declaração de 22 caixas aceita; retificação para 35 recusada no formulário com erro explícito sem retry. Pergunta final não enviada. Não equivale a dado apagado ou ausência de armazenamento.|
|M04-known|erro nominal|2/2/1|Comparação 20/32 para quatro entregas aceita, diferença 12. Explique com mais detalhes. falha explicitamente sem retry; aprofundamento não realizado.|

Evidências: interface-evidence.json, ui-review.json e ui-failure-notes.json no pacote compartilhável; recibos privados por caso em ui-matched-evidence. A acessibilidade e as respostas brutas foram inspecionadas. A exportação HTML não é suportada neste navegador e não foi apresentada como realizada. A revisão foi feita pelo implementador, não é independente/cega; o recorte não certifica todas as interações de UI. Erros observados no navegador não recebem status HTTP presumido a partir da aparência da tela.

## Documentado, implementado, testado e instalado

| Item | Documentado | Implementado | Testado | Principal |
|---|---|---|---|---|
| Preservação de payload, classificação, cálculo limitado, contexto parcial e extração | Este relatório e diffs por etapa | Checkout e wheel identificado | Suíte offline e execuções reais delimitadas; falhas mantidas | Não instalado |
| Memória conversacional | Casos e recibos naturais | Caminho de memória preexistente, agora exercitado após melhora do encaminhamento | Declaração/recordação, atualização e nova sessão; qualidade parcial explicitada | Sem alteração; esta rodada não certifica a principal |
| Diagnóstico de cobertura/revisões | Fontes, hashes e limites | Mecanismos preexistentes reaproveitados | HTTP e controles reais em QA; repository_coverage não estabelecida | Acervo QA não conectado |
| Pesquisa dos três predictors | Gabaritos preservados, matriz separada | Código de pesquisa preexistente mantido | Três gerações reais; nenhuma aprovação semântica integral | Não promovido |
| Pacote instalável | Hashes CAIN/Bundle/Snapshot e atestados | Wheel não editável em ambiente novo | API, CLI e interface reais; não apenas build | Sem promoção automática |

## Preservação conferida ao encerrar

A leitura final conferiu o pacote principal, as duas configurações e os bancos workspace/research: mesmo conteúdo de todas as linhas comparadas com a cópia consistente anterior, integridade SQLite ok. A fonte da candidata continua congelada. Os cinco documentos científicos canônicos conferidos mantiveram seus hashes. HEAD e estado dos repositórios foram registrados em final-preservation.json; não houve checkout, commit, push ou alteração dos produtores. A checagem antecede somente a gravação da documentação desta entrega.

Os serviços QA próprios foram encerrados após o último readback; não restaram listeners nas portas 8896/11436/11435. A primeira observação imediata ainda via a porta do processo em encerramento, e foi preservada; a conferência posterior confirmou sua saída. A aba criada para QA foi fechada. Nenhuma raiz ou histórico QA foi apagado.

## Reversão verificável e pacote de revisão

Os patches `increment-final-lf.diff` e `increment-tests-lf.diff` passaram em `git apply --reverse --check` contra o checkout congelado. Essa checagem não aplicou rollback. Antes de reverter, repita a checagem e compare os hashes, para preservar qualquer trabalho posterior. Use somente os hunks deste incremento; backups seletivos estão em R/baseline. O novo teste de sequências pertence a esta rodada. Para documentação, use os originais locais e `documentation-diff.diff`; mantenha o relatório histórico com uma nota de reversão, se necessário. Não faça reset global, não restaure bancos e não apague recibos. A principal não exige rollback desta tarefa.

Pacote compartilhável: `C:/CAIN/work/conversation-v2-20260914/CAIN_CONTINUACAO_CONVERSA_SANITIZADO.zip`. Contém Markdown, JSON/JSONL, manifestos, entradas/respostas efetivas, citações mínimas autorizadas, revisões manuais, comandos e diffs. Bancos, políticas completas, perfis pessoais, bytes base64 e listas de tokens foram omitidos. Raízes locais foram sanitizadas. Os hashes dos pedidos originais continuam identificados; isso não promete replay byte a byte do material sanitizado. Diffs de documentação sanitizados são para revisão; reversão usa os originais locais. Os recibos privados completos permanecem em R, sem sobrescrita das tentativas anteriores.

A revisão semântica foi feita pelo mesmo agente que implementou e criou os casos, sem cegamento ou independência. O erro inicial de agente em B09, as duas montagens com dependências distintas e o defeito de codificação foram preservados e qualificados. Não repetiria o ajuste de B09 sem conferir primeiro o agente efetivamente selecionado; a instrução adicionada à conversa permanece identificada na composição testada, mas não é apresentada como causa do acerto de B09.

## Próximo incremento prioritário — não iniciado

Corrigir o repasse de contexto autorizado para a classe de retificações, continuações e perguntas referenciais que caem no classificador, sem depender de uma enumeração crescente de frases e sem desviar pesquisas explícitas ou ampliar acesso. Reavaliar em seguida a qualidade das respostas, pois M04 mostrou recusa mesmo com contexto na geração. Preservar como regressões a literalidade com delimitadores, JSON na rota código, M11, A05/A06 e as sínteses dos três predictors. Isso exige outra candidata congelada e nova confirmação; não foi iniciado automaticamente.
