# Campanha de conversa Stocks — 16/09/2026

Rodada nova, em QA, distinta da campanha de leituras literais e reproduções.
O registro local completo fica em `C:/CAIN/work/stocks-conversation-20260916`;
entradas e verificações do produtor em `C:/STOCKS/work/cain-conversation-20260916`.
Bancos, fontes privadas, pesos e respostas integrais não são publicados no GitHub.

## Protocolo e estado

Campanha finita: duas perguntas para cada H1–H22, mais seis controles (50 casos).
O conjunto cobre regra, critério, dados, cronologia, resultados, motivos, limites,
próximo teste, identidade inexistente, lucro absoluto versus incremento, janela
prospectiva, aritmética, busca documental e conversa comum sem consulta automática.
Avaliação semântica manual compara a resposta com o contexto realmente fornecido;
JSON válido, citações e testes verdes não constituem aprovação.

**Campanha em andamento; não há aprovação semântica geral.** O relatório final
deve registrar cada caso, inclusive falhas, interrupções e abstenções. Não somar
repetições ou versões de modelo como evidência econômica independente.

O runner `tools/run_research_conversation.py` utiliza os componentes reais do CAIN.
As respostas de `research.review` são registradas como tais na conversa de QA;
isso não significa que o agente de conversa comum tenha consultado o acervo.
Respostas brutas, prompts efetivos, schema, metadados, inventário/digest do modelo,
fontes e hashes são preservados. Falhas aparecem como registros de execução,
nunca como respostas inventadas do modelo. A escrita do resultado em arquivo
precede a projeção no histórico, permitindo recuperar falhas de armazenamento.

Os escopos são explícitos: projeto de documentos
`4c57f901-f8fb-455e-ad5b-453a6f41b9e0`; pesquisa `stocks` com projeto vazio.
O acervo de QA acrescentou os 15 relatórios históricos de veredito e o design que
define H3. A admissão documental não reabre protocolos nem valida seus resultados.
O projeto de QA contém 128 documentos; não presumir essa população no principal.

## Correções em validação

- Contexto seleciona revisões literais distintas antes de campos repetidos.
- O orçamento final remove duplicatas antes de eliminar uma revisão e se abstém
  quando não consegue preservar as revisões selecionadas.
- Contextos compartilhados são recalculados após cada exclusão, evitando apontar
  para um trecho que saiu do prompt.
- Busca reconhece palavras internas de chaves `snake_case`, preserva campos
  explicitamente pedidos e contempla termos como limitação e confiabilidade.
- Até quatro páginas/200 registros são examinados; limites e omissões permanecem
  declarados. O limite de fontes do seletor não é uma alegação de leitura integral.
- Instruções distinguem veredicto/reliabilidade, lucro/incremento e motivo
  histórico/requisito futuro. Essas instruções não garantem obediência do modelo.

## Tentativas preservadas e limites

O piloto com `qwen3.5:4b` encontrou falta de memória. `qwen2.5:3b` produziu três
respostas, ainda sem aprovação semântica geral: H22 confundiu a rejeição histórica
com validação futura; H1/H17 ampliaram afirmações de ausência além do recorte.
Uma tentativa com `qwen3.5:0.8b` falhou no carregamento e foi encerrada.
A primeira campanha foi interrompida após a pré-verificação revelar perda de
qualificações com as novas fontes; também registrou bloqueios SQLite durante QA
concorrente. A seguinte usa cópias exclusivas. Nada foi apagado.

Os 31 testes stdlib e as reproduções H21/H22 foram novamente executados em QA:
H21, 8 cenários/16.400 pontos; H22, 24 avaliações/30.226 pontos, incluindo duas
inviáveis. São os mesmos resultados históricos, sem evidência independente nova.
H1–H20 não receberam novos experimentos econômicos por essa repetição.
H22 conserva rejeição histórica; H21 conserva resultado condicional e janela
prospectiva até a primeira sessão em/após 10/09/2027.

Não houve ordens, contas financeiras, automações recorrentes, instalação do
runtime Stocks no Windows ou alteração dos 12 bancos originais do produtor.

## Retomada

Verificar `campaign2.log`, `campaign-2/completed.json` e os arquivos por caso antes
de executar qualquer nova inferência. Arquivo `STOP` no diretório da rodada
interrompe o runner entre casos. Não apagar nem reutilizar diretórios de saída.
O runner recebe caminhos explícitos de cópias de QA; não aponta implicitamente
para bancos principais e não inicia servidor/modelo por conta própria.

Antes da entrega principal, verificar testes/CI no SHA exato, reavaliar o estado
concorrente, criar cópias consistentes de recuperação e conferir preservação dos
documentos/turnos anteriores. Publicação de código, instalação, entrega documental
e aprovação semântica são recibos diferentes.
