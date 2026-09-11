# Revisão independente da entrega de testes individuais do CAIN

Revisão concluída em ambiente separado. A entrega tem melhorias úteis, mas não
deve ser aproveitada sem as correções de extração, contexto e rastreabilidade
registradas aqui. A síntese livre dos modelos continua sem confiabilidade
demonstrada: persistem conclusões falsas mesmo com citações exatas.

As suítes corrigidas passaram com 447 testes e um skip em cada Python 3.12/3.13.
Foram concluídas as três rodadas de 38 relatos, 16 respostas de qualidade,
12 etapas funcionais, workflows, streaming, visão e embedding. Falhas semânticas
e a resposta recusada foram mantidas nos resultados. Não é avaliação humana cega
nem validação financeira. Nenhum merge, push da revisão ou instalação operacional
foi realizado; a entrega anterior publicada e o trabalho deste chat foram preservados.

## Origem e preservação

| Origem | Revisão confirmada |
|---|---|
| Trabalho deste chat / baseline | `231ffa8791b6cd89de0a025ddb4ec02298e8cd45` |
| Protocolo congelado do outro chat | `cfa3658b4f9ad15dc1d2fb61fd7b44011192ab79` |
| Foco por identidade, prompts, controles e avaliador | `92792001b4b0f2aa5899f25d279f877eea7c782e` |
| Tabelas multicoluna / código entregue | `dc114fcbfeb7e709468da129408851d3e7665ced` |
| Relatório e autorização posterior / remoto conferido | `e1786feb70f1a0175be8238b0cf4c1ecaec2637b` |
| Correções desta revisão | `86c38f8a333f278084adac3abc2ebe40c48b616c` |

Branch de revisão: `review/individual-models-20260911`, checkout
`C:\CAIN\work\independent-review-20260911`. Baseline e código entregue têm
checkouts detached próprios, `independent-baseline-20260911` e
`independent-delivered-20260911`. Os dois checkouts de trabalho anteriores não
foram substituídos. O código operacional continua na 0.4.7 deste chat.

Os 106 arquivos do manifesto da entrega anterior conferiram por SHA-256. Os
testes usam cópias somente de leitura do arquivo de relatos admitidos, com bancos
de saída separados. Evidências desta revisão: `C:\CAIN\entregas\independent-review-20260911`.
Não publicar bancos, fontes recebidas ou respostas brutas no GitHub.

## Acertos do outro chat

- Focar chaves JSON exatas resolve a mistura no formato efetivamente recebido
  para H1–H9. Caminhos distintos mantêm estado e nome de trial separados.
- Recusar JSON duplicado antes de interpretá-lo como prosa é uma melhoria real.
- Tabelas multicoluna e deduplicação da mesma linha retiram inferência
  desnecessária da extração de campos, quando o formato suportado é respeitado.
- Controles num_ctx, num_predict, max_input_bytes e think chegam ao provider e
  aos subprocessos da avaliação. O teste novo cobre a serialização da configuração.
- O protocolo /5 impede continuação silenciosa de jobs /4 com prompts novos.
  Jobs completos continuam idempotentes; pendentes continuam legíveis/canceláveis.
- O relatório separa aprovação da suíte de qualidade semântica e conserva falhas.
  A CI publicada foi confirmada em Python 3.11/3.12/3.13 no commit final e1786fe.
  [Execução original da CI](https://github.com/leonardosovienski/cain/actions/runs/34649588365).
  Essa CI não cobre o commit novo desta revisão; os testes novos foram locais.

## Defeitos encontrados e decisões

| Severidade / origem | Evidência reproduzida | Correção / decisão |
|---|---|---|
| Alta; seletor herdado deste chat, mantido pela entrega | Linhas isoladas eliminam negações: DPL recebe “consumidor real foi confirmado” sem “nenhum segundo”; CLAIM-CR-H6 recebe “REFUTED nem VALIDATED” sem “não é”. | Descartar recorte arbitrário por linha. Preservar parágrafos e continuações de itens; omitir blocos excessivos com cobertura explícita. Offsets continuam sobre o texto original. |
| Alta; foco novo incompleto sobre fallback herdado | `{"H1":{"status":"NO"},"H6":{"status":"WAIT"}}` envia ambas as identidades; H6 ausente devolve H1/H60. | Foco por segmentos exatos do caminho JSON, incluindo chaves escapadas; identidade ausente em estrutura reconhecida causa abstenção, não fallback para outras entidades. |
| Média; regressão introduzida em dc114fc | `| H6 | WAIT |\r\n` era literal no baseline, tornou-se unsupported na entrega. | Percorrer spans de linhas sem normalizar texto; LF, CRLF e CR mantêm offsets corretos. |
| Média; extensão de tabelas incompleta | Cabeçalho vira relação, inline code simples é descartado e delimitador recusado pode levar a outra linha. | Excluir cabeçalho reconhecido por separador; aceitar células literais com inline code completo; registrar delimitadores não suportados e impedir reinterpretação ambígua. |
| Média; prompt novo contraditório | Exige copiar estado literal, mas proíbe copiar texto da fonte. | Proibir cópia de excertos completos/hashes, mantendo cópia de valores literais. Isso elimina a contradição; melhora semântica precisa ser medida. |
| Média; avaliador introduzido em 9279200 | Wrapper não é OllamaLLM; model_identity não consulta digest e grava null. | Recorder herda o provider real e conserva suas opções, digest e verificação de mudança do modelo. |
| Média; rastreabilidade do avaliador | Caminho do runner não necessariamente é o código importado numa comparação. | Registrar módulo efetivamente importado, commit, hashes, parâmetros, identidade do avaliador e rechecagem de fonte inalterada. |

As correções não tratam uma citação literal como prova da interpretação. No
exemplo DPL, a fonte completa nega o segundo consumidor externo; o contexto
anterior havia perdido justamente essa negação. Classificar toda a falha como
“alucinação do modelo” ocultaria um defeito do consumidor. Em H1, por outro lado,
o prompt entregue já continha CLOSED_NO_GO e o modelo negou que esse estado
estivesse disponível: há erro do gerador mesmo com o campo correto presente.

## Compatibilidade e limites da correção

O contrato ResearchSnapshot, os registros, estados, fontes e políticas não foram
alterados. As mudanças ficam na seleção/extração, prompts e avaliação. Novos
workflows da revisão usam `/6`, revisão de prompt `addressable-review/4` e
seletor `identity_then_lexical_excerpts/3`; /4 e /5 pendentes não avançam com
semântica nova. Nenhum job operacional foi migrado.

Formatos suportados são explícitos. Identidade pode ser chave/caminho JSON,
primeira célula de tabela ou título Markdown exato. Não se infere identidade
arbitrária de um esquema desconhecido, nem se inventam nomes de colunas.
Blocos longos podem ser omitidos pelo orçamento; a abstenção por orçamento é
distinta de ausência de fonte. Valores estruturados são transcrições, não fatos
científicos certificados. Estados parciais recebidos continuam parciais.

## Método de comparação

Mesmos 19 relatos, perguntas, arquivos de política e parâmetros em cada versão:
contexto 8192, saída 768, entrada 6500 bytes, think=false, temperatura 0, seed 42,
timeout 240 s. Geradores qwen3.5:0.8b e qwen2.5:3b executados separadamente;
embedding qwen3-embedding:0.6b avaliado como embedding, não gerador. Rodadas
sequenciais usam processos e bancos separados. Durações incluem carga do modelo
e atividade de testes no host; não são comparação controlada de velocidade.

O protocolo anterior permaneceu byte a byte intacto. Não houve acesso ao holdout
ou reexecução de pesquisa financeira. Presença de estado literal, outros IDs e
citação exata são diagnósticos; a inspeção semântica considera negação, estado,
identidade, causalidade e cumprimento da instrução. O avaliador deste chat é um
assistente, não um painel humano independente.

O arquivo original do protocolo foi preservado. A cópia obtida do Git usa LF,
enquanto o artefato anterior usa CRLF; seus JSONs decodificados são idênticos,
e a igualdade dos bytes após normalização somente CRLF→LF foi conferida. Todas
as rodadas desta revisão usam a mesma cópia. Não foram alterados casos, perguntas
ou gabaritos. `input-config.toml`, `input-policy.json`, `input-archive.db` e
`input-protocol.json` preservam as entradas na pasta privada de evidências.

## Testes reproduzidos

- Código entregue dc114fc: 430 aprovados, um skip Windows, Ruff aprovado.
- Oito falhas em dez novos testes reproduzidas antes do primeiro ajuste.
- Quatro falhas adicionais reproduzidas nos testes de negação e seções Markdown.
- Revisão corrigida em Python 3.12: 447 aprovados, um skip Windows.
- Revisão corrigida em Python 3.13: 447 aprovados, um skip Windows. O skip é
  `test_symlink_import_escape`, sem privilégio de symlink neste Windows.
- Cada suíte corrigida coletou 233 testes de integração, 179 unitários,
  26 de avaliação, seis de CLI e quatro de API; o skip está incluído nessa coleta.
- Wheels entregue e corrigido construídos e instalados offline em venvs novos,
  fora dos checkouts; assets, contrato, CLI e pip check aprovados.
- Os avisos de depreciação do TestClient são preservados nos resultados.

XMLs, comparações de contexto, wheels e recibos ficam na pasta de evidências.
As verificações de offsets incluem Unicode e finais de linha variados, sem
normalização das fontes. O arquivo `context-comparison.json` preserva os trechos
selecionados por cada versão para cada relato, separadamente das respostas.

Houve pressão de memória com aproximadamente 223 MB livres: um build isolado
de dependências falhou no subprocesso pip com access violation, e um pip check
excedeu 30 s após instalação bem-sucedida. As filas ociosas e a primeira rodada
Python 3.13 foram interrompidas, não contadas como aprovadas. A repetição serial
passou. O build entregue foi repetido com setuptools 84.0.0 já instalado, sem
isolamento de build; a **instalação** dos wheels permaneceu isolada e offline.
Os 50 arquivos cain/ do wheel reconstruído são idênticos aos do wheel entregue
anteriormente, embora o SHA do ZIP difira por metadados de empacotamento.

Wheel entregue reconstruído: `6f1c735e9d1dc12c00196bd9d295722ea7255db293432134d121a98604e7a80c`.
Wheel corrigido: `ce43f2bed45be8b191da775aa85d643453e6200d94ff0e8a0044b51b3cf18600`.
Ambos mantêm versão de pacote 0.4.7 e ficam em diretórios separados; distinguir
por commit e hash, sem substituir o wheel operacional deste chat.

## Como reproduzir

Use o ambiente de revisão e uma pasta de saída nova por condição. O runner
fica na revisão; PYTHONPATH escolhe o código que será importado, cuja origem
e hashes são conferidos no próprio recibo. Troque apenas o checkout entre
baseline, entregue e revisão; mantenha protocolo, parâmetros e arquivo de entrada.

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = 'C:\CAIN\work\independent-baseline-20260911\src'
C:\CAIN\work\independent-review-env-20260911\Scripts\python.exe tools/verify_individual_models.py --protocol evaluation/individual-models-20260911.json --config C:\CAIN\work\research-capabilities-20260911\cain.toml --db C:\CAIN\work\individual-validation-20260911\archive-baseline.db --policy C:\CAIN\config\research-policy.json --output CAMINHO_NOVO
```

Execute do checkout da revisão. `independent-delivered-20260911` contém dc114fc;
`independent-review-20260911` contém as correções. A avaliação de qualidade usa
`python -m cain.evaluation.quality --models qwen3.5:0.8b qwen2.5:3b --split dev
--think false --timeout 240 --num-ctx 8192 --num-predict 768 --max-input-bytes 6500
--output PASTA --run-id NOVO_ID`. O funcional usa `python -m cain.evaluation
--mode functional --provider ollama --model MODELO` com os mesmos controles.
Nunca execute duas inferências/rodadas de modelos em paralelo neste host.

A suíte completa usa `python -m pytest -q --junitxml=ARQUIVO_NOVO.xml`, nos dois
ambientes isolados `independent-review-env-20260911` (3.12) e
`independent-review-env313-20260911` (3.13). O lint usa `python -m ruff check .`.
O build serial usa `python -m build --wheel --no-build-isolation --outdir PASTA_NOVA`,
com dependências de build instaladas no ambiente de desenvolvimento. A instalação
é verificada por `python tools/verify_wheel.py --wheel CAMINHO_DO_WHEEL`, que cria
um venv temporário offline e executa fora do checkout. Não usar a `.venv` operacional.

A busca dos 19 relatos é filtrada por identidade: preservação do ID não valida
ranking geral sem filtro. O par semântico PT/EN é apenas um caso sintético.
Checks de preferência verificam persistência/injeção, não obediência da resposta.
Regex de fatos pode produzir falso alarme, como local/locais; não se alterou o
gabarito congelado para favorecer saídas observadas. Essas métricas não devem ser
usadas como critério automático de aprovação semântica.

O contador de estado literal procura o valor recebido inteiro após `strip()`.
Em CLAIM-CR-H6 esse valor termina em uma frase parcial sobre o gate operacional;
uma resposta correta com `INCONCLUSIVE_DUE_TO_POWER` pode não satisfazer o
contador. Em H1, uma resposta que nega a disponibilidade de `CLOSED_NO_GO` pode
satisfazê-lo. Isso exige inspeção semântica separada. O estado parcial admitido
foi preservado, sem reconstruir ou corrigir silenciosamente dados do produtor.

## Comparação controlada dos relatos

Cada linha corresponde a 19 perguntas com os mesmos parâmetros. Presença literal e citação exata não significam interpretação correta. A coluna de outros IDs conta casos entre H1–H9, não mistura dentro dos relatos compostos.

| Código | Modelo | Respostas admitidas | Citações exatas | Valor literal presente | Casos com outros IDs | Workflows concluídos |
|---|---|---:|---:|---:|---:|---:|
| 231ffa8 | qwen3.5:0.8b | 19/19 | 19/19 | 8/19 | 5/9 | 2/3 |
| 231ffa8 | qwen2.5:3b | 19/19 | 19/19 | 7/19 | 2/9 | 3/3 |
| dc114fc | qwen3.5:0.8b | 19/19 | 19/19 | 9/19 | 0/9 | 3/3 |
| dc114fc | qwen2.5:3b | 19/19 | 19/19 | 3/19 | 0/9 | 3/3 |
| 86c38f8 | qwen3.5:0.8b | 18/19 | 18/19 | 9/19 | 0/9 | 3/3 |
| 86c38f8 | qwen2.5:3b | 19/19 | 19/19 | 1/19 | 0/9 | 3/3 |

As 38 explicações do baseline e as 38 da entrega foram reproduzidas exatamente, incluindo suas falhas. A revisão tem 37 respostas admitidas e uma recusada por comprimento. O contador de literal do Qwen2.5 caiu de 7 para 3 na entrega, e para 1 nesta revisão; não houve recuperação dessa obediência. Algumas paráfrases corrigidas são melhores semanticamente, mas a alteração de prompt não pode ser anunciada como melhora geral.

Nos três códigos, streaming terminou corretamente para ambos os geradores; o Qwen3.5 identificou vermelho no caso visual; Qwen2.5 é somente texto. A pergunta de identidade ausente fez zero chamadas ao gerador. O embedding qwen3-embedding:0.6b produziu vetores de 1024 dimensões, normas unitárias, cache idêntico e similaridade PT/EN acima do par não relacionado; as 19 buscas filtradas preservaram a identidade em cada versão. Nenhum desses casos pequenos certifica visão, tradução ou ranking geral.

Todos os novos workflows registraram digest real do modelo. Código, parâmetros, casos e tags de modelos foram conferidos entre as três rodadas; os recibos confirmam `source_unchanged=true` e `states_preserved=true`. Resultados legíveis e máquina: `per-case-diagnostics.md` e `comparison-summary.json`, na pasta de evidências.

## Interpretação dos resultados e decisões de aproveitamento

O foco novo deve ser aproveitado com as correções desta revisão. Nos nove
relatos H1–H9, a entrega retirou os IDs de outras hipóteses que apareciam no
baseline. Essa métrica não cobre mistura interna de CLAIM-CR-LLM, cujo estado
composto distingue H5 e H4. Ela também não detecta a troca de estado por trial.

O recorte por linha deve ser descartado: uma citação pode ser exata e, ainda
assim, ter sua negação retirada pelo consumidor. Os blocos completos corrigem
esse defeito mecânico. No Qwen3.5, DPL passou a negar corretamente confirmação
de consumidor externo. No Qwen2.5, CLAIM-CR-H6 passou a distinguir inconclusão
por poder, com 23% para rho=0,2, de refutação. Esses ganhos pontuais não aprovam
o restante das respostas.

Persistem falhas graves dos geradores com contexto correto. O Qwen3.5 atribui
a H5 a falta de poder de H4, troca H1 pelo nome do trial e contradiz limitações
que acabou de enumerar. O Qwen2.5 transforma a descrição da hipótese HMM em
conclusão positiva, apesar de o estado REFUTED estar disponível; em DPL, confunde
execução real de testes com uso de dados reais. Essas respostas não devem ser
consumidas como sínteses científicas verificadas.

A correção do prompt remove uma contradição, mas não produz ganho uniforme.
CLAIM-CR-H6 no Qwen3.5 gerou análise de 1.206 caracteres e foi recusado pelo
limite já existente de 1.000. O provider terminou com `done_reason=stop`; a
resposta bruta foi preservada. Não foi erro de transporte nem corte no limite
de tokens. O limite não foi relaxado para transformar falha em aprovação.

Devem ser mantidos os controles explícitos de geração, a recusa de ambiguidades,
os caminhos e offsets literais, a deduplicação e a separação dos protocolos.
O recorder anterior deve ser substituído pelo corrigido, que registra o digest
real. As métricas de presença literal e citações devem permanecer diagnósticas.
Descartar a interpretação dessas métricas como prova de qualidade, bem como
qualquer proposta de promover automaticamente as sínteses a estado científico.

Compatibilidade com este chat foi verificada pela suíte completa, fluxos reais
nas cópias e preservação do contrato/instalação. A revisão descende da entrega
do outro chat, que descende do trabalho deste chat; não reimplementa nem remove
streaming, visão, busca, relações, debate, MCP ou armazenamento. A compatibilidade
de jobs é deliberadamente restritiva: seis jobs reais /4 em banco copiado
permaneceram legíveis; cinco completos foram idempotentes; o pendente recusou
continuação e pôde ser cancelado na cópia. /4 e /5 também têm regressões
automatizadas. Isso não autoriza migrar os bancos operacionais.

## Qualidade e obediência fora dos relatos científicos

Os oito casos de desenvolvimento por gerador foram executados novamente: 16/16
respostas concluídas, idênticas às respostas preservadas da entrega anterior,
com 16/16 entradas idênticas. Não houve acesso ao holdout. Esse conjunto é
conhecido e exploratório, não estima generalização.

Ambos os modelos geraram JSON válido escolhendo `busca` no caso que exigia
`codigo`. Qwen3.5 respondeu em português ao pedido explícito de inglês,
acrescentou “teste de hipótese” ao enunciado genérico, omitiu a citação exigida
na abstenção de preço e omitiu a revisão de sexta-feira no resumo de negação.
Qwen2.5 sugeriu remover o original, contrariando a instrução de preservá-lo.
Sua resposta teve 144 palavras, acima do critério interno de 70 do avaliador;
esse número não estava explícito no prompt, portanto a contagem não prova
violação de uma instrução numérica dada ao modelo.

Também houve falsos alarmes: `local` não reconheceu `locais`, e a regex de
aprovação não reconheceu a paráfrase correta “sem aprovação”. O check de palavra
`original` passou apesar da recomendação de removê-lo. Não foi alterado o
conjunto congelado para elevar notas. `quality-comparison.json` e
`quality-semantic-observations.json` separam checks de observações individuais.
As funções `soma(a,b)` tiveram sintaxe/assinatura verificadas e retorno `a+b`
inspecionado; nenhum código gerado foi executado.

O funcional concluiu seis etapas e 35/35 checks em cada gerador. As 12 respostas
foram idênticas às preservadas anteriormente. Os checks cobrem preferência
persistida e corrigida entre processos, isolamento entre usuários, roteamento
e fonte local. Não certificam obediência: Qwen3.5 justificou abandonar passos
em favor de parágrafo e afirmou retorno inteiro para uma função sem restrição
de tipos. Ambos recuperaram BOREAL-731 e sete dias da fonte sintética. Esses
resultados estão em `functional-comparison.json` e nos dois diretórios funcionais.

## Entrega e conferência final

Os dois checkouts anteriores permaneceram limpos: `231ffa8` neste chat e
`e1786fe` no outro. As respectivas refs remotas conferiram com os mesmos hashes.
Os 106 arquivos do manifesto anterior, os 50 arquivos do pacote instalado,
configuração e política conferiram sem divergência. Recibo: `preservation-after.json`.
O wheel corrigido também conferiu byte a byte nos 50 arquivos cain/ com o código
testado. A instalação principal não recebeu a branch de validação nem esta revisão.

`engineering-verification-summary.json` referencia XMLs, wheels e CI original;
`final-source-receipt.json` confirma código imutável depois de todas as rodadas.
O `git_dirty=true` dos testes de qualidade/funcional decorre da redação deste
relatório, dos índices e da ferramenta de resumo; src, tests e evaluation
continuaram iguais ao commit de código `86c38f8`.

O relatório, README, CONTINUIDADE e ferramenta de resumo são registrados em
commit documental posterior ao código testado. `MANIFESTO_REVISAO_INDEPENDENTE_20260911.json`
identifica esse commit e os hashes das evidências; `cain-independent-review.bundle`
preserva a branch local. Ambos ficam em `C:\CAIN\entregas\independent-review-20260911`.
Para retomar, ler este relatório e os recibos, sem promover automaticamente os
resultados ou executar novas pesquisas nos produtores.

## Inspeção individual das respostas corrigidas

Observações independentes deste assistente sobre os 19 relatos admitidos. Não são notas de um painel humano cego. Respostas, prompts e contexto completos estão em `model-review/report.json` e `model-review/`, na pasta privada de evidências. O arquivo `independent-semantic-observations-delivered.json` conserva a inspeção dos 38 resultados da entrega reproduzida; `independent-semantic-observations-review.json` conserva os 38 resultados corrigidos, incluindo a resposta recusada.

| Relato | Qwen3.5:0.8b corrigido | Qwen2.5:3b corrigido |
|---|---|---|
| CLAIM-CR-COSTS | Parafrase compativel com custo assumido e impossibilidade de recalculo; omite estado literal. Redacao sobre preservacao da posicao e imprecisa, mas nao afirma friccao real medida. | Estado literal correto. Condicao de reabertura citada e real, mas omite limitacao central de custos assumidos/nao calibrados e impossibilidade de recalculo. |
| CLAIM-CR-DPL | Corrige a falsa confirmacao de consumidor externo: preserva negacao e limita testes a dados controlados/sinteticos. Omite estado literal SUPPORTED. | Confunde execucao real de testes com testes em dados reais. Fonte explicita dados controlados/sinteticos. Limite de auditoria de consumidores e parcialmente preservado; estado literal omitido. |
| CLAIM-CR-H6 | Backend recusou analise com 1206 caracteres, acima do limite existente de 1000. Resposta bruta preservada; nao contar como resposta admitida. Problema de obediencia do modelo, nao de citacao ou transporte. | Identifica INCONCLUSIVE_DUE_TO_POWER e poder de 23% para rho=0,2 corretamente. Diagnostico literal falha porque valor recebido inclui sufixo parcial do gate; nao e refutacao. Estado completo solicitado nao copiado. |
| CLAIM-CR-HMM | Parafraseia REFUTED mas nega a limitacao de universo que ele proprio menciona; estado literal ausente. Interpretacao contraditoria. | Afirma edge economico da hipotese que a fonte marca REFUTED; descricao da hipotese virou conclusao. Limite BTC/ETH vs outros mercados preservado, mas nao corrige a conclusao falsa. |
| CLAIM-CR-LLM | Confunde H5 refutado por evidencia negativa com H4 inconclusivo por falta de poder; contexto completo nao elimina a mistura dentro do relato composto. | Distingue corretamente H5 refutado e H4 inconclusivo por poder, incluindo interrupcao operacional/amostra pequena. Parafrase compativel, sem estado composto literal exato. |
| CLAIM-CR-TREND | Corrige distincao entre encerramento de escopo e refutacao cientifica e ausencia de trial formal; omite estado literal composto. | Nucleo CLOSED_BY_SCOPE / INCONCLUSIVE e ausencia de trial formal compativeis. Omite ressalva explicita de nao refutacao cientifica e nao copia valor completo recebido. |
| H1 | Substitui estado solicitado pelo nome do trial; CLOSED_NO_GO estava disponivel em caminho distinto. Falha do gerador. | Parafraseia encerramento, mas resultado negativo nao e demonstrado pelo campo CLOSED_NO_GO isolado. Limite vago e estado literal omitido. |
| H2 | Estado literal correto; inventa que a limitacao explicita e impossibilidade de inferir outras hipoteses. Ausencia no recorte nao prova ausencia na fonte. | Parafraseia encerramento sem promocao, mas inventa causalidade por dominio de lifecycle. Estado literal omitido. |
| H3 | Estado literal correto, mas explicacao de dominio/ciclo de vida sem sucesso e extrapolacao; nao informa limitacao recebida. | Parafrase de fechamento sem recomendacao; negativa global sobre informacoes do processo nao e sustentada por contexto selecionado. Estado literal omitido. |
| H4 | Estado literal correto, mas omite insuficiencia amostral na explicacao e usa ciclo de vida como interpretacao nao sustentada. | Parafrase correta de fechamento por amostra insuficiente; estado literal pedido omitido. |
| H5 | Estado literal correto, mas sem atividade nao e significado demonstrado de CLOSED_NO_GO; nao informa limitacao. | Nega informacao de trial apesar de hypothesis_trials/H5 estar no contexto; falha de leitura do gerador. Estado literal omitido. |
| H6 | Estado literal correto; afirma que fonte nao fornece detalhes quando o acesso e apenas a campos selecionados. Limite de cobertura nao e ausencia global. | Parafrase correta de fechamento por amostra insuficiente; estado literal pedido omitido. |
| H7 | Estado literal correto, sem mistura; nao apresenta limitacao substantiva. Nao ha limitacao citada na resposta e constatacao sobre sua propria resposta, nao fonte completa. | Parafrase correta de registrada nao ativa; limite deveria dizer recorte consultado, nao toda fonte. Estado literal omitido. |
| H8 | Estado literal correto, sem mistura; nao apresenta limitacao substantiva. Nao inferir validacao cientifica da nao ativacao. | Parafrase correta de registrada nao ativa; limite deveria dizer recorte consultado, nao toda fonte. Estado literal omitido. |
| H9 | Estado literal e insuficiencia de amostras coerentes; formula dominio/ciclo de vida e desnecessaria. Diz nao haver limitacoes citadas apesar de mencionar amostra. | Parafrase correta de fechamento por amostra insuficiente; estado literal pedido omitido. |
| Retorno líquido pessoal e operação real | Nao aptos e suas quatro limitacoes sao parafraseados de modo compativel; frase final nega limitacao explicita apesar de acaba-la de enumerar. Valor literal completo nao reproduzido. | Troca nao aptos por nao aprovado, omite cenario pessoal e transforma limitacoes de custos/eventos em falta desses itens. Estado literal completo omitido. |
| CLAIM-BR-MARKET-001 | Preserva falta de comparacao e prova PIT, mas transforma ausencia de multiplas temporadas em multi-semana; omite estado literal. | Mantem bloqueio, ausencia de comparacao e tres snapshots mais antigos que 24h. Recursos do Pit e formulacao imprecisa; omite estado literal e cobertura 245/245. |
| CLAIM-BR-MARKET-002 | Reproduz BLOCKED_PENDING_PIT_FEATURES, mas afirma contraditoriamente que nao ha status literal disponivel; limitacoes resumidas parcialmente. | Parafrase parcial de bloqueio/disponibilidade nao provada; mistura recursos multi-temporadas com ausencia de odds multi-season. Estado literal omitido. |
| CLAIM-BR-MARKET-003 | Parafrase compativel da ausencia de comparacao e multiplas temporadas; omite estado literal e requisito de prova de disponibilidade PIT. | Parafrase parcial do bloqueio; dados antigos generaliza a limitacao de tres snapshots >24h. Omite estado literal, cobertura e falta de comparacao. |
