# Teste integral de uso do CAIN — 12/09/2026

Rodada iniciada em 12/09 no fuso America/Sao_Paulo, com conclusão após meia-noite UTC.
Checkout: `C:/CAIN/projeto`, main inicialmente `c449390756752117cfe813e83547e415591bd5bb`, igual ao remoto após fetch.
A fonte inicial, o pacote 0.4.7 instalado e os hashes registrados pelo processo 20532 coincidiam.
`pip check` e integridade dos bancos estavam aprovados.

## Falhas encontradas e correções

1. **Conversa tratada como pesquisa:** na interface 8877, depois de buscar um documento sintético,
   “Quanto é 2 + 2?” retornou o histórico dessa busca. A seleção LLM só dispunha de busca, código e resumo.
   A versão 0.4.8 registra conversa como capacidade própria, disponível também por intenção explícita na API e CLI.
2. **Histórico irrelevante usado como citação:** artigos e palavras de comando bastavam para recuperar uma conversa antiga.
   A busca agora exige interseção de termos relevantes antes de admitir um hit de histórico.
3. **Cálculo com extrapolação do modelo:** o primeiro candidato respondeu 4, mas inventou cenários adicionais incorretos.
   Cálculos simples reconhecidos usam AST restrita e frações exatas, sem eval, chamadas, nomes ou inferência.
   Há limites de tamanho, quantidade de nós e magnitude; divisão por zero e operações não suportadas são recusadas.
4. **Interação social com pressuposição indevida:** o modelo interpretou “Tudo bem?” como afirmação do estado do usuário.
   Cumprimentos sociais curtos e agradecimentos recebem resposta local, sem essa inferência.

As demais conversas continuam usando o modelo local configurado. Não houve troca de modelo, pesos ou política.
Não se adicionou execução de código gerado nem pesquisa externa automática.

## Matriz de verificação

| Área | Resultado e evidência |
|---|---|
| Interface principal 8877 | “oi” → “Oi! Como posso ajudar você?”, perfil QA separado |
| Projetos e documentos | Projeto QA criado; texto sintético salvo; busca híbrida retornou JADE731 e preservou “não está autorizada” |
| Citações de documentos | Detalhe S1 abriu; trecho, SHA-256 e offsets 0–119 corretos; verificação programática adicional na API |
| Memória e conversas | Preferência de tópicos no projeto; consulta de preferências e nova conversa herdaram o escopo correto |
| Conversa livre final | Inferência e persistência funcionaram; o pedido de uma única frase não foi respeitado pelo modelo, registrado como falha de aderência |
| Memória pela API isolada | Criação/remoção por escopo, precedência projeto/usuário, retorno ao padrão e isolamento entre usuários aprovados |
| API de documentos e histórico | Deduplicação, extensão inválida, acesso por outro usuário, feedback e repetição do run sem duplicar turno aprovados |
| Pesquisa e Historian | H4 em cópia do acervo: estado e trial com fonte; motivo/amostra explicitamente não localizados; dossiê e busca aprovados |
| Bundle | Consulta real de metadados; importação, autorização, migrações, artefatos e linhagem cobertos pela suíte sintética |
| Workflows | Fluxo completo H4: 6/6 etapas, crítica e síntese geradas; reabertura pela UI aprovada; API verificou checkpoints, trace e cancelamento |
| CLI instalada | Ajuda, doctor, saudação e query H4 aprovados; comandos mutáveis usaram bancos isolados |
| Segurança e erros da API | Validação 422, Origin 403 e Host inválido 400 aprovados; restauração/falhas induzidas cobertas em dados temporários |
| Streaming de texto | Transporte terminou com evento done; **falhou a aderência semântica** ao pedido “Responda somente: CAIN QA” |
| Visão e qualidade geral | Não houve nova avaliação real de imagens nem certificação da interpretação livre; testes técnicos não atestam qualidade geral do modelo |

O laboratório gerou uma descrição inventada de empresa em vez do texto solicitado. Esse resultado foi preservado como
limitação do modelo; não foi contado como aprovação semântica nem ocultado por uma resposta simulada.
Sem alterar o modelo/configuração do usuário, esta rodada não resolve a confiabilidade geral da geração livre.

## Baterias e artefatos

- Baseline: 606 passed, 1 skipped, 2 avisos de depreciação.
- Candidato intermediário em wheel estável: 623 passed, 1 skipped, 2 avisos.
- Fonte final: **624 passed, 1 skipped, 2 warnings**, 216,50 s. Regressões finais focadas: 18 passed.
- Regressões novas: conversa, cálculo, histórico irrelevante, API, limites aritméticos e entradas executáveis recusadas.
- Lint Ruff aprovado; wheel validado em venv novo, offline, não editável e fora do checkout.
- Um ensaio intermediário teve `ModuleNotFoundError: cain.research` porque o ambiente de teste estava sendo reinstalado
  enquanto um subprocesso iniciava. A execução foi invalidada, o grupo de 10 testes passou novamente e a bateria foi
  repetida sem reinstalação concorrente. Não se atribuiu essa falha ao produto.
- O skip de Windows é o ensaio de symlink sem privilégio disponível. Os avisos são de Starlette/httpx e AnyIO.

## Dados, configuração e reprodução

Recibos privados, logs e scripts: `C:/CAIN/work/qa-full-20260912`.
Interface isolada usada: porta 8891, bancos copiados para `isolated`, política copiada para `backup`.
Perfil sintético adicionado na principal: `qa-cain-20260912`; não reutilizar como perfil pessoal.
Backup SQLite consistente inicial em `backup`; backup de promoção com bancos, documentos e pacote anterior em `promotion-backup`.
Nenhum banco, resposta real de pesquisa ou configuração privada foi incluído neste commit.
Os dados existentes são conferidos por comparação de linhas e integridade; configurações por hash.

## Promoção e reteste principal

Código: `92b6428cb26064ed9032b0a93ccae64da7b06c3d`. Wheel 0.4.8:
`ae5d6e658b8c8690cacbd5e760938eb9aa0f10b2992b52ef56dd18a89b02542d`.
Os 61 arquivos instalados foram comparados com o wheel e a fonte, sem diferenças.
Processo principal reiniciado pelo launcher padrão: PID observado 24896, loopback 8877, health 0.4.8.
O reteste da pergunta original na mesma conversa retornou `2 + 2 = 4.` sem a citação irrelevante.
Saudação, resposta social, memória de projeto, busca híbrida, hash da citação, Historian H4 e atalho CLI passaram.
Inferência livre funcionou, mas a aderência de formato segue limitada como registrado acima.
`preservation-final.json` confirmou integridade dos bancos, nenhuma linha preexistente ausente/alterada fora do QA,
configurações idênticas e nenhuma mudança de dependência além do próprio CAIN.
O histórico da resposta errada foi preservado; a correção vale para novos pedidos.

Comandos de desenvolvimento em ambiente separado:

```powershell
python -m pytest -q
python -m ruff check .
python -m pip wheel --no-deps --wheel-dir dist .
python tools/verify_wheel.py --wheel dist/cain_research-0.4.8-py3-none-any.whl
```

Testes técnicos não validam conclusões científicas, econômicas ou a qualidade de qualquer resposta arbitrária.

## Revisão e teste ampliado — 14/09/2026

Pedido posterior: revisar as alterações da integração, corrigir falhas e testar amplamente o CAIN. Esta seção descreve um **candidato no checkout**, não uma instalação nova. Fonte em `C:/CAIN/projeto`, baseline `3f88a2535f08c70bce561cd3822e7558cebec326` com alterações locais preservadas. Recibos em `C:/CAIN/work/review-full-20260914`. A implementação, os gabaritos e a avaliação por predictor ficam no [relatório canônico de cobertura](COBERTURA_PROJETOS_20260913.md#revisão-crítica-e-teste-ampliado--14092026).

O CAIN web principal e o Ollama estavam desligados no início. Duas tentativas preliminares não chegaram à inferência: conexão recusada e runtime apontando para a pasta padrão sem os modelos existentes. O runtime local foi iniciado com os pesos já presentes em `C:/CAIN/modelos`, sem downloads de modelos ou alteração de configurações persistentes. A API de QA usa porta 8895 e bancos próprios. Não se abriu uma sessão de teste na instalação principal.

### Matriz do teste geral

| Área | Execução e resultado | Limite da conclusão |
|---|---|---|
| Suíte completa do checkout retido | **719 aprovados, 1 ignorado, 2 avisos**, Python 3.12.14/Windows; `reviewed-tests.log` e `reviewed-tests.xml`. Ruff aprovado | Testes técnicos, majoritariamente sintéticos; não aprovam toda resposta do modelo. Skip: privilégio Windows para symlink indisponível. Outras versões de Python/SOs da CI não foram executadas |
| API HTTP real | Health, OpenAPI, modelos, validação de entrada e proteção Host/Origin passaram na API isolada | Health informa que a inferência não foi exercitada por essa rota; não foi usada como prova de geração |
| Projetos, documentos e memória | CRUD exercitado com dados sintéticos; deduplicação, extensão inválida, acesso por outro usuário, precedência projeto/usuário, remoção de preferência QA, feedback e repetição de run sem duplicar turno passaram | `general-api-checks.json`; nenhum dado pessoal foi alterado para esses testes |
| Interface real | Perfil QA, cálculo `2 + 2 = 4`, criação de projeto/documento, preferência de tópicos no projeto, isolamento do Geral e persistência após recarga/reseleção passaram | Interações reais no navegador e inspeção visual; não é validação exaustiva de navegadores ou tamanhos de tela |
| Busca e citação na interface | Busca híbrida recuperou OPALA914, preservando hipótese não confirmada/coleta interrompida. Expansão de S1 mostrou texto literal, hash do documento/trecho e offsets 0:130 corretos | Recuperação e prova literal; a própria resposta indica ausência de síntese do modelo |
| Pesquisa dos três acervos | Query, inspeção, busca e cobertura passaram na API; UI mostrou BR 22/82, Crypto 31/89, Stocks 39/74, separando publicações/revisões e Snapshot/Bundle | Nenhuma dessas contagens é total de hipóteses únicas ou prova de compreensão integral. Auditor e reimportação do catálogo foram reexecutados separadamente |
| Workflows e retomada | API real completou inspeção/busca, trace, reabertura e cancelamento. Rodadas com modelo e verificação literal de checkpoints/citações ficam no relatório por predictor | Conclusão de etapas e citações válidas não certificam contestação ou síntese |
| CLI e MCP | Quatro comandos de CLI passaram com armazenamento QA. Subprocesso MCP real inicializou, listou quatro ferramentas, recuperou H4 e rejeitou troca de usuário nos argumentos | Transporte MCP local, sem conectar o acervo a outro serviço. O MCP instalado foi exercitado sobre banco/política isolados |
| Conversa livre real | Duas frases em português, resposta salva e inferência concluída com qwen3.5:4b | **Falha de precisão:** generalizou o caso fictício para impossibilidade de qualquer inferência estatística válida com amostras pequenas. Transporte/formato aprovados não aprovam essa generalização |
| Continuidade da conversa real | Na mesma sessão, respondeu que houve cinco observações e que o motivo da interrupção não foi informado | Aprovado somente neste exemplo; não comprova memória perfeita em toda conversa |
| Streaming real | Retornou exatamente `TESTE LOCAL` e evento final `done`, exit 0 | Um pedido curto aprovado, sem certificação geral de aderência |
| Visão real | Mesmo qwen3.5:4b, PNG sintético com retângulo azul: resposta `Retângulo azul.`, evento `done`, exit 0 | `--vision-model qwen3.5:4b` explícito; nenhum modelo novo. Não avalia imagens pessoais, outras tarefas visuais ou todos os modelos opcionais |
| Build e distribuição | Wheel final construído em cópia do checkout e instalação de verificação offline, não editável, em venv novo, fora do checkout | O primeiro build falhou por ausência de `setuptools` no ambiente auxiliar; repetição com ambiente de build isolado passou. Nenhum pacote foi instalado na principal |

Os dois avisos da suíte são de depreciação em Starlette/httpx e AnyIO. Não se atualizaram dependências da instalação principal para esconder esses avisos. A rodada intermediária de **721 testes** pertence à tentativa de alterar a instrução das etapas, rejeitada por regressão semântica no Brasileirão. Seus três testes específicos foram retirados junto com a abordagem rejeitada; um teste de corte induzido por limite de schema foi acrescentado. Logs e código intermediários foram preservados, sem apresentar os 721 como validação da versão retida.

O wheel retido está em `dist-reviewed/cain_research-0.4.12-py3-none-any.whl`, SHA-256 `530c11e738216a9cebc850cd39ef48137971e597f794d08a8418216d98537f08`. A versão nominal 0.4.12 não significa que esse código já esteja instalado. O pacote anterior em `dist-final`, hash `1a5826ee99bf39f4396e90ebb59397790768e7ff876e78b87d529a04f89c829e`, pertence à tentativa rejeitada e não é a entrega retida. `verify-wheel-reviewed.log` registra a verificação do pacote retido em ambiente isolado.

`wheel-reviewed-source-match.json` confirma correspondência dos 55 módulos Python do wheel com o checkout retido. No reteste final de pesquisa foram nove chamadas reais: Brasileirão completou seis etapas, mas permanece parcial; Crypto completou seis, com extrapolações em suporte/contestação apesar da síntese adequada ao núcleo selecionado; Stocks completou cinco etapas e falhou na validação da síntese de 1.092 caracteres. Não houve síntese aceita em Stocks nem aprovação agregada dos três predictors. Reabertura e citações literais passaram separadamente (`fourth-receipts-verified.json`); análise em `semantic-review.json`.

Ao terminar, a API de QA passou na última consulta HTTP e foi encerrada. O modelo foi descarregado e o runtime temporário, iniciado por esta revisão, foi encerrado após conferir a identidade do processo. Portas 8877, 8895 e 11434 ficaram sem listeners, preservando o estado inicial desligado; bancos e recibos de QA permanecem guardados. `final-preservation.json` e `listeners-after-cleanup.json` registram preservação e encerramento. Nenhuma instalação principal foi iniciada para esses testes.

Os gabaritos gerais foram registrados antes das chamadas em `general-rubrics.json`. `conversation-real.json`, `continuity-real.json`, `stream-real.ndjson`, `vision-real.ndjson` e `ui-verification.json` preservam resultados e limites. A avaliação semântica é manual, pelo assistente implementador, sem revisão humana independente. Não houve troca do modelo principal, fine-tuning, execução de experimentos científicos dos produtores ou uso de novas APIs de inferência externas.

**Documentado:** matriz, evidências e limites nesta seção e no relatório de cobertura. **Implementado:** correções no checkout. **Testado:** suíte completa local, API/CLI/MCP/UI e exemplos reais descritos. **Disponível na principal:** nenhuma alteração desta revisão. Bancos principais íntegros e linhas anteriores preservadas, política/configuração verificadas e módulos Python instalados iguais ao baseline; zero publicações do catálogo local na principal (`preservation-check.json`).

Reversão: comparar os arquivos alterados com `review-full-20260914/baseline` e retirar somente os hunks desta revisão, após conferir mudanças posteriores. Não usar restauração integral do Git, de bancos ou de configurações: havia trabalho local anterior. Preservar todos os recibos, inclusive os de falha; reverter o checkout não muda o pacote instalado.
