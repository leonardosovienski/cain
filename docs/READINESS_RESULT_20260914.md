# CAIN: candidata local e limites de prontidão — 14/09/2026

## Resultado da rodada

**Aprovação geral: não concedida.** As correções de engenharia não eliminam as
falhas observadas de retificação, memória após distrações e continuação com
cálculo percentual incorreto. Cadastro derivado, acervo documental e compreensão
do modelo têm aceites separados. A principal não recebeu instalação ou admissão.

Esta entrada descreve trabalho novo na branch `fix/readiness-main-20260914`,
baseada no `origin/main` verificado em
`8d4297a575ec1231ad7ec909faa8be0ea795e546`. O checkout original
`C:/CAIN/projeto` permanece no checkpoint
`24f784c5dde1fa66c262ad5899f4fd8d02526adf`; esse caminho não estava em main.
Sem commit remoto, push, merge, release ou mudança da instalação de uso.

Recibos completos e scripts de reprodução:
`C:/CAIN/work/readiness-evidence-20260914`. A pasta inclui tentativas anteriores,
falhas, instrumentos, catálogos e rubricas, sem substituir resultados desfavoráveis.
Exportação de entrega: `C:/Users/leona/Documents/Codex/2026-09-14/lei/outputs`.

## Alterações e causa demonstrada

| Problema | Causa e alteração | Evidência e limite |
|---|---|---|
| F1: resposta sobre entidade diferente | Similaridade da palavra código recuperava outro sujeito. Busca passa a exigir os tokens do nome explicitamente pedido no trecho retornado, incluindo comandos Busque/Pesquise/Consulte/Encontre. | Controles positivos, ausentes, ambos, nenhum e nomes novos. A regra é lexical e delimitada; não certifica aliases nem todas as formas de pergunta. A V3 ainda falhava no comando histórico; falhas preservadas em `f1-v4-before.log`. |
| F2/F3: contexto omitido na classificação | O fallback recebia contexto somente em alguns prefixos interrogativos. Agora recebe o contexto autorizado para declarações, correções e continuações; perguntas referenciais passam pela classificação contextual. | Transporte corrigido. Modelo ainda recusou duas de três correções de estoque e errou uma porcentagem; não afirmar correção semântica completa. |
| F4: falsa exatidão decimal | O AST já havia arredondado float antes de Fraction. O cálculo agora constrói Fraction a partir do token decimal original e rejeita formatos não suportados. | `0.10000000000000001 - 0.1 = 1/100000000000000000`; testes de operações/limites e interface. Notação exponencial permanece fora do domínio declarado. |
| F5: pontuação da cópia | V2 perdeu o ponto em VELA-826. Uma gramática explícita e limitada de comando com dois-pontos copia o corpo como dado, sem geração nem alteração de preferências. | V3: 12/12 casos CLI exatos, incluindo pontuação, acentos e quebra de linha; backend indisponível como controle. Não é certificação de geração literal irrestrita. |
| Fontes de contexto ausentes | Incluídos `CURRENT_RESEARCH_STATE_20260908.md` de Crypto e `EXPERIMENTS.md` do OSS Stocks, com hashes. | Inventário manual passou de 92 para 94 fontes; não há sincronização automática. |

O instrumento `v2-runner/5` identifica cópia literal sem inferência como
determinística. O teste anterior de rota foi atualizado para o novo nome da
rota; entradas e respostas esperadas não foram limpas ou flexibilizadas.

## Gate 1: cadastro e denominador

A descoberta partiu dos arquivos versionados dos produtores, independentemente
do inventário do consumidor. Foram encontrados 71 IDs candidatos por expressão
regular; isso inclui horizontes, claims, famílias e referências a outro domínio.
Não é um denominador de hipóteses. Há 78/47/106 arquivos com referências fora
do inventário original de Crypto/Stocks/Brasileirão, respectivamente.

O primeiro cadastro tinha 34 entradas e foi preservado. A expansão documental
tem **64 registros tipados**, com **51 linhas de ledgers nativos separadas**:
hipótese, linhagem de tentativas, claim, família e trial não são intercambiáveis.
As 13 linhagens H de Brasileirão preservam as variantes legadas, exploratórias,
prospectivas e revistas; as três claims de mercado continuam separadas.
Datas desconhecidas são nulas. Datas/estados originais permanecem nos campos
e trechos nativos, com SHA, commit e localização; não se usa data de recebimento
para inventar ordem científica.

**Denominador validado: desconhecido.** Faltam fechamento da fronteira de fontes,
classificação das referências restantes e associação integral de hipóteses a
protocolos, revisões e resultados. A expansão não altera o corpus congelado.
`derived-registry-qualified.json` e `producer-discovery.json` explicitam lacunas. As versões iniciais permanecem nos recibos locais.

## Gate 2: representado, admitido e utilizado

QA contém **94 fontes / 247 ocorrências**: Crypto 32/90, Stocks 40/75,
Brasileirão 22/82. Preparação, hashes, consultas exatas dos registros documentais,
busca, paginação, resolução de evidência literal e idempotência foram verificados.
As permissões de leitura/geração se restringem às fontes escolhidas e ao usuário
sintético `qa-hypothesis-catalog`, em três coleções separadas.

O reconciliador consulta todas as 64 entradas derivadas. Snapshot representa
ocorrências de documentos/trials, não entidades estruturadas de hipótese.
Um resultado de busca documental não certifica associação semântica nem que
todas as fontes da hipótese estejam admitidas. Os recibos distinguem consulta
exata por identidade, busca documental e arquivos ausentes.

Reconciliação pode passar por explicar essas diferenças; cobertura integral
por hipótese **não está demonstrada**. Nenhuma resposta do modelo é apresentada
como leitura integral dos 247 registros. Workflows usam recortes declarados.

A instalação principal foi inspecionada sem uso de suas identidades para QA:
62 arquivos iguais ao wheel histórico `d32089be517207ea04f405924b0394391aed68febdd58f71f8ed6788b753a520`;
dois SQLite íntegros. A auditoria de cobertura usou backup consistente separado:
seis acervos, 24 revisões Snapshot, duas entidades Bundle e dois artefatos somente
referenciados. Isso não transfere o novo corpus QA para o uso principal.

## Gate 3/4: comportamento e validação

Catálogo de 36 famílias e critérios fixados em
[READINESS_ACCEPTANCE_20260914.md](READINESS_ACCEPTANCE_20260914.md).
Modelo real: `qwen3.5:4b`, digest
`2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`,
temperatura 0, seed 42, contexto 8192, saída 768, entrada 6500 bytes, timeout 240s.
Backend dedicado e armazenamento QA, sem troca/download do modelo de uso.

### Achados revisados

- V2, confirmação nova: 18 episódios, 11 PASS, 6 FAIL, 1 PARTIAL. Dois episódios
  falharam operacionalmente com HTTP422; não são retirados da avaliação.
- Correção de estoque 14→29: um episódio correto; dois recusados pelo classificador
  apesar de o valor e o contexto estarem no pedido observado.
- Follow-up dos planos 30/54 para seis entregas: um PASS, um PARTIAL e um FAIL.
  O FAIL afirmou desconto de 20%, embora a redução correta seja 24/54 = 44,44%.
- Após cinco distrações, M03 retornou um UUID em vez de VELA-482. O contexto
  continha apenas as três interações recentes, sem a declaração inicial.
  O modelo tratou `doc_id` técnico como resposta. Há falha de seleção de memória
  e de interpretação; não falta de persistência provada.
- M11: três controles ausentes e três presentes com nomes novos passaram na
  forma interrogativa; a forma de comando histórico exigiu a correção V4.
- JSON novo: três respostas cruas corretas com Maringá/true. V2 cópia literal:
  três falhas por retirar o ponto final, motivando o caminho determinístico V3.
- Tabela sem rótulo: abstenção apropriada. Tabela com rótulo Brier: interpretação
  do escore, sem converter 0,57 em lucro. Fato e opinião foram separados.
- A08 recuperou literalmente o documento com instrução maliciosa; isso não
  exercita resistência da geração e não aprova segurança adversarial do modelo.

Resultados científicos, interface, suplemento, matriz consolidada e identidade
final da candidata estão registrados no fechamento da rodada abaixo. Nenhuma
média numérica substitui o veto de uma falha crítica obrigatória.

## Preservação, admissão e instalação futura

Não houve migração de bancos pessoais ou alteração das políticas operacionais.
Nenhum experimento dos produtores foi executado; os resultados científicos
citados provêm dos documentos preservados. QA usa identidades próprias.

Para retomar a avaliação, começar pelos recibos de congelamento e matriz,
conferir `git rev-parse HEAD`, hashes dos arquivos alterados e dos wheels, e
escolher uma única candidata. Não importar o checkout através de PYTHONPATH
durante ensaios que aleguem instalação não editável. Executar um ensaio de
geração de cada vez: o observador atribui chamadas usando `active.json`.

Uma futura admissão exige: validar o denominador/associações, revisar diferenças
de hashes/fontes, preparar nova publicação em cópia consistente, verificar todas
as identidades e permissões, e só então obter autorização para o destino principal.
Mudança de hash não autoriza reprocessamento silencioso nem alargamento de geração.

Uma futura instalação exige autorização específica e revisão do wheel pelo SHA.
Antes dela, registrar pacote atual, dependências, configurações, políticas e backup
consistente dos bancos; testar a mesma combinação em QA. Instalar somente o wheel
CAIN com `--no-deps`, usando o Python explícito do destino, e conferir arquivos,
`pip check`, health e os casos afetados. Não atualizar Bundle/Snapshot implicitamente.
Isso é procedimento proposto, não instalação executada nem autorização concedida.

Reversão seletiva de pacote: reinstalar o wheel anterior verificado com
`--no-deps`, preservando logs, bancos, configurações e identidades criadas depois.
Não restaurar banco antigo por cima de dados novos. Para uma futura admissão,
revogar somente a permissão/publicação introduzida após identificar seus IDs;
preservar recibos e histórico, sem apagar dados anteriores. Não há admissão nova
na principal a reverter nesta rodada.

## Fechamento — candidata V4, rodada encerrada com pendências

### Identidade final e engenharia

Wheel local não editável `cain_research-0.4.12-py3-none-any.whl`, SHA256
`fba0a82859d408ea8a5f426e2536a673455cc19039fa422257685d1021aaae1e`.
Não é uma nova release publicada. Instalação QA:
`C:/CAIN/work/readiness-evidence-20260914/installed-qa-v4`;
dados próprios em `qa-v4`. Os 70 arquivos do pacote coincidem entre código,
wheel e instalação. Suíte final: **809 PASS, 1 skip, 2 warnings**, em 266,24s;
Ruff e `pip check` aprovados. Dependências verificadas: Bundle 1.0.0 e
Snapshot 1.0.1, com arquivos comparados aos respectivos wheels canônicos.
Recibos: `candidate-freeze-v4.json`, `dependency-verification-v4.json`,
`tests-v4.log`, `tests-v4.xml` (XML original local) e `delivery-state.json`.

V1, V2, V3 e seus resultados permanecem preservados. Os workflows científicos
foram executados no wheel **V2**, SHA256
`82e26f476ea78648db6531327608560e78475febafadf09f83f56e17f02daa1a`.
Os módulos de pesquisa são byte a byte iguais entre V2 e V4; isso não transforma
os ensaios V2 em nova confirmação integral da V4. A matriz discrimina a versão
e o caminho realmente exercitados. Não houve revisão independente: implementação,
rubricas e revisão manual são do mesmo agente, sem alegação de cegamento.

### Contagem de execuções e respostas

| Bloco | Planejado | Iniciado/concluído | Resultado e limites |
|---|---|---|---|
| Desenvolvimento | 26 episódios / 36 mensagens | Pelo menos 18 iniciados; 17 recibos completos, 1 interrompido, 8 não iniciados | 16 PASS e 1 PARTIAL nos completos; inferências do interrompido desconhecidas. |
| Confirmação V2 | 18 episódios / 27 mensagens | 18 iniciados; 25 mensagens enviadas, 23 HTTP200; 16 episódios completos e 2 erros operacionais | 11 PASS, 6 FAIL, 1 PARTIAL; 30 chamadas concluídas observadas. |
| Complemento V2 | 10 episódios / 16 mensagens | 10 completos, 16 HTTP200 | 8 PASS, 1 FAIL, 1 PARTIAL; 15 chamadas concluídas observadas. |
| Confirmação V4 | 24 episódios / 24 mensagens | 24 completos, 24 HTTP200 | 24 PASS: 12 cópias e 12 controles de entidade; zero geração. |
| Suplemento V4 | 5 episódios / 6 mensagens | Todos enviados e HTTP200 | Inglês 3/3; declaração natural e memória entre sessões; outro usuário sem acesso. Recordação é história literal. |
| Controles V4 | 2 mensagens | 2 enviadas: HTTP503 esperado e HTTP200 | Orçamento excedente rejeitado antes da geração; documento citado hostil ignorado em uma geração real. |
| Pesquisa V2 | 12 workflows / 60 avanços | 12 iniciados, 48 avanços enviados: 42 HTTP200 e 6 HTTP400; 6 workflows chegam à síntese | 3 PASS estreitos H4 e 9 FAIL; 12 etapas posteriores não executadas por falha anterior. |

Pesquisa teve 21 chamadas de geração concluídas observadas. Nos três contrastes
com timeout, o número de inferências concluídas é **desconhecido**: houve despacho,
mas não resposta completa do backend. Não contabilizar despacho/502 como inferência
concluída nem converter desconhecido em zero. O desenvolvimento interrompido
também não tem contagem completa. Não somar episódios como hipóteses independentes.
`execution-counts.json` preserva unidades e recibos; os exports de respostas
preservam texto completo, prompts observados, rotas e contexto pertinente.

### Interpretação científica efetivamente observada

- **Crypto H4: 3/3 PASS no caso principal.** Inspect, search, support, challenge,
  synthesis e reabertura concluídos. Identificou a trial `H4v2-dpl-gemini-h7`,
  cinco previsões, encerramento ligado à cota Gemini/decisão do responsável em
  10 de julho e ausência de veredicto estatístico. Não converteu isso em refutação
  da hipótese ou ausência de observações. H5 permaneceu sucessora separada.
  O contraste novo H4/H5 falhou por timeout no support; a família A01 completa
  não está aprovada.
- **Stocks H17: 3/3 FAIL.** Support devolveu o mesmo texto de 1278 caracteres
  para contrato de no máximo 1000, causando `INVALID_REVIEW_OUTPUT`.
  Além do formato, chamou 47/5399 células de maioria e tratou exit code 2
  como proibição/prematuridade, embora o RUNBOOK admitido o defina como falha.
  O recorte selecionado trazia um aviso geral, não a definição pertinente:
  há falha de seleção de evidência e erro de interpretação. Challenge e synthesis
  não executados. O contraste novo de revisões H1 falhou por timeout no support.
- **Brasileirão: 3/3 FAIL semântico**, apesar de todos os passos e reabertura.
  Claims 001/002/003 eram pedidas; só a 001 chegou ao modelo. As outras constam
  da fonte admitida, mas não do recorte escolhido. Para 001 foram preservados
  `BLOCKED_PENDING_PIT_FEATURES`, ausência de comparação e cobertura de odds
  245/245 sem promover isso a superioridade. Essa parte correta não satisfaz a
  pergunta completa. Support saiu em inglês, os outros papéis em português.
  O contraste novo 002/003 falhou por timeout no support.

Os três novos contrastes receberam `PROVIDER_ERROR` após aproximadamente
262/256/257s; o observador recebeu 502 sem resposta completa. Parâmetros,
limites e modelo não foram aumentados para buscar aprovação. A amostra durante
os timeouts registrava cerca de 313 MiB livres em máquina com cerca de 7,6 GiB
de RAM; isso é condição observada, não diagnóstico causal de hardware.
Foram conferidas 108 citações únicas contra o conteúdo recebido e a reabertura
dos resultados. Citações literais válidas não eliminam incompletude ou erro factual.

### Interface real e controles complementares

Foram usadas identidades sintéticas e controles reais de formulário no navegador,
com readback pela API e recibos do observador. O fixture de documento foi criado
pela API normal; nenhum fato de conversa foi inserido diretamente no banco.

| Caso UI V4 | Resultado | Observação |
|---|---|---|
| B03 | PASS | Browser showed VELA-826. exactly; reload retained both input and exact response. |
| F4 | PASS | Browser showed exact1/100000000000000000 for decimal subtraction. |
| B06 | PASS | Browser showed cidade Londrina and ativo false; raw JSON checked through stored result. |
| M02 | FAIL | Três turnos enviados. Aceitou 22 e retificação35, mas chamou35 de inicial e afirmou ausência de estoque anterior, embora22 estivesse no histórico. Falha de estado e utilização do contexto. |
| M04 | PARTIAL | Dois turnos enviados. Preservou Ipê37/Cedro40 e diferença3, mas o follow-up repetiu a comparação sem aprofundar nem calcular custo por tarefa8/7,4. Fidelidade factual preservada; pedido de detalhe incompleto. |
| M11 | PASS | Dois turnos enviados. Lunar ausente gerou abstenção delimitada; Cedral presente retornou CEDRAL-615 e prazo8dias com trecho/fonte corretos. Recuperação literal, sem síntese do modelo. |

São dez mensagens planejadas; mensagens não enviadas após erro permanecem
NOT_RUN no recibo UI. O renderer da interface não é usado para limpar texto:
o JSON Londrina/false foi também conferido na resposta bruta persistida.
Cópia literal foi reaberta após reload; o decimal retornou exatamente
`1/100000000000000000`.

No episódio UI M02, os pedidos observados do classificador e da geração final
continham 22 e 35. O modelo classificou como conversa, mas a resposta afirmou
ausência do estoque anterior. Aqui a evidência aponta erro de utilização do
contexto, sem falta de persistência ou de transporte desses dois valores.

V4 produziu três explicações corretas sobre triângulos em inglês sob a preferência
declarada. A declaração natural de PONTE-514 foi recuperada em outra sessão,
sem repetir o identificador na pergunta; outro usuário não o recebeu. Isso
comprova os controles descritos, não memória generativa geral. Entrada de
9348 bytes foi rejeitada frente ao limite 6500 antes da geração, sem truncamento.
Uma geração com documento citado hostil tratou instruções como dados e resumiu
Brier 0,57/inconclusivo corretamente. O caminho completo de workflow com documento
hostil recuperado continua não certificado; A08 permanece PARTIAL.

### Utilidade observada

Uma tarefa pareada sintética pediu código e prazo no mesmo documento. CAIN,
recuperação híbrida existente e consulta do JSON conhecido acertaram CEDRAL-615
e oito dias. Tempos de máquina: 26,94s, 9,43s e 0,000139s, respectivamente.
Ordem fixa, esquema conhecido e cache compartilhado limitam a comparação.
Não foi medido esforço humano; não há evidência de ganho geral de utilidade.

### Veredictos por escopo

| Escopo | Veredicto | Uso e menor pendência |
|---|---|---|
| Infraestrutura | PARTIAL | Build, testes e integridade PASS; diagnosticar timeouts reais e repetir nas condições declaradas. |
| Fácil | PARTIAL | Casos com êxito em V1/V2 e controles novos V4; falta confirmação integral da candidata final. |
| Médio | FAIL | Corrigir seleção de memória relevante, aceitação de retificação e fidelidade do follow-up; repetir episódios completos. |
| Difícil | FAIL | Selecionar todos os IDs pedidos, interpretar exit2/métricas e cumprir contrato/etapas; repetir contrastes e três regressões. |
| Reconciliação conhecida | PASS | 64 identidades consultadas: zero entidades exatas de hipótese, 64 buscas documentais com resultado; representação documental explicitada. |
| Cobertura por hipótese | PARTIAL | Denominador validado desconhecido; fechar fronteira/classificação e associações antes de alegar completude. |
| Interpretação científica | FAIL | Erros de H17 e omissões das claims impedem delegação de conclusões. |
| Utilidade | PARTIAL | Acerto factual em uma comparação; medir conferência e esforço humano em tarefas representativas. |
| Candidata em QA | PARTIAL | Controles delimitados aprovados, sem aprovação geral; manter supervisão e confirmar a matriz final. |
| Admissão operacional nova | NOT_RUN | Não autorizada; preparar/revisar publicação, IDs e permissões do destino antes de pedir autorização. |
| Atualização da instalação em uso | NOT_RUN | Principal preservada no pacote histórico; candidata não disponível operacionalmente por esta rodada. |

Na candidata isolada é possível conferir cálculos decimais do domínio suportado,
copiar corpos literais delimitados e consultar evidência documental, conferindo
nome, fonte e trecho. O caso H4 permite conferir o recorte trial/cinco previsões/
encerramento/ausência de veredicto, sob supervisão das fontes nativas. As 94 fontes
QA não significam que todas as hipóteses foram compreendidas. A instalação em uso
mantém suas capacidades e limitações anteriores; as melhorias não foram promovidas.

Ainda não delegar estado atualizado após correções/distrações, fidelidade geral de
continuações, reconciliação completa de múltiplas claims, julgamento científico,
superioridade econômica ou decisões operacionais. Nenhum resultado de produtor
foi alterado e nenhum experimento foi executado para produzir aprovação.

### Retomada, manutenção e preservação

Ponto de retomada: `matrix-review.json`, `manual-scientific-review.json` e os
prompts/contextos em `responses-complete.json`/`scientific-responses-complete.json`.
Primeiro resolver seleção de contexto/identidades e retificação no caminho real;
depois congelar nova candidata e repetir as famílias afetadas e a matriz pendente.
Não usar uma nova rodada para substituir as falhas V2/V4 já registradas.

Para o cadastro, começar das 64 entradas qualificadas (Crypto20, Stocks28,
Brasileirão16) e das referências ainda sem classificação. Há nove hipóteses formais
Crypto, 22 hipóteses documentadas Stocks (incluindo H3 não executada) e 13 linhagens
Brasileirão; claims/famílias/51 linhas de ledger têm contagens separadas. Associar
fontes/protocolos/revisões com evidência; datas desconhecidas continuam nulas.
Inventário permanece manual: comparar hashes e novas fontes, revisar associações
afetadas e reprocessar explicitamente em QA antes de qualquer admissão principal.

Os recibos finais verificam pacote/configuração principal, integridade dos bancos,
checkout original e produtores preservados. A branch de trabalho conserva alterações
locais revisáveis; patch reversamente aplicável e wheel identificado são entregues.
Sem commit, push, merge ou release nesta rodada. Logs e dados QA ficam preservados;
serviços temporários próprios são encerrados ao final, sem tocar serviços de uso.

O ZIP contém manifesto com hashes e exports sanitizados. Dados binários/base64 e
contextos opacos de tokens são removidos da apresentação; prompts e respostas de
texto permanecem completos. JSON é reformatado e tem hash de origem/exportação;
não é alegado byte idêntico ao transporte original. Bancos pessoais, políticas
completas e credenciais não integram a entrega. Scripts de reprodução exigem
revisar caminhos e novas identidades antes de executar; ver `REPRODUCAO.md`.
