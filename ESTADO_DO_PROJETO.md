# Estado verificado do CAIN

Atualização 0.4.9: código instalado **cba4b5b0d1c0b3dd7dcbbfbaa2a22a1647ad5a20**, modelo padrão **qwen3.5:4b**, porta 8877. Leia [avaliação real da LLM](docs/LLM_CORRECOES_20260912.md). Contexto recente e roteamento de continuações corrigidos; formato estrito e cautela excessiva ainda falham em alguns casos. Backup e recibos em `C:/CAIN/work/qa-llm-20260912`. Somente o modelo mudou nas configurações.

## Registro anterior da 0.4.8 (histórico)

Referência operacional da rodada de 12/09/2026: **92b6428cb26064ed9032b0a93ccae64da7b06c3d**, CAIN **0.4.8**, instalada e retestada na porta 8877.
Commits posteriores de documentação não implicam reinstalação do pacote nem novos testes do produto.
A branch vigente é main; não usar nomes de branches presentes nos relatórios históricos como instruções atuais.

| Item | Estado verificado |
|---|---|
| Projeto principal | C:/CAIN/projeto, main |
| Checkout histórico adicional | C:/CAIN/work/cain-system-20260912; não atualizado nesta rodada |
| Instalação | C:/CAIN/.venv, wheel não editável, CAIN 0.4.8 |
| Serviço principal | http://127.0.0.1:8877/ |
| Contratos | Snapshot 1.0.1 e Bundle 1.0.0 canônicos |
| Código integrado | Conversa, aritmética exata limitada, filtro de histórico, Historian, Supply e contratos |
| Git | main; código instalado identificado acima, documentação pode ter commit posterior |

## Evidências

- [Teste integral desta rodada](docs/TESTE_INTEGRAL_20260912.md): **624 passed, 1 skipped, 2 warnings** na fonte final;
  wheel intermediário: 623 passed; 18 regressões finais focadas aprovadas; Ruff e instalação limpa offline aprovados.
- Reteste na principal: saudação, cálculo, resposta social, conversa com inferência, documentos, memória, citações e H4 por API;
  cálculo corrigido também na UI e no atalho CLI. A geração livre não é aprovação de aderência semântica.
- Os 61 arquivos do pacote coincidem byte a byte com fonte e wheel. Dependências preservadas; `pip check` aprovado.
- Bancos íntegros, sem perda/alteração de linhas preexistentes fora do QA; configurações sem alterações por hash.
- Recibos atuais: `C:/CAIN/work/qa-full-20260912`; backup completo da promoção: `promotion-backup`.

### Evidências históricas da 0.4.7

- [CI da referência anterior d604a0e](https://github.com/leonardosovienski/cain/actions/runs/34727241470): aprovada; não valida a 0.4.8.
- Rodada de perguntas compostas: 606 testes da fonte e 106 do pacote aprovados, com um skip Windows em cada bateria e dois avisos de depreciação.
- Essas contagens são da rodada anterior à promoção; a CI acima valida a referência conjunta, incluindo contratos finais e correção de imports.
- Na instalação principal: tarefa real H4, citações e offsets, saudação “oi”, consulta por CLI e verificação dos arquivos instalados aprovadas.
- Os registros e grants preexistentes foram preservados; os acervos Stocks adicionados pela tarefa de integração têm escopo próprio.

Identidade do wheel atual, contratos e verificação anterior: [manifesto operacional](operational-state.json).
Recibos locais: `C:/CAIN/work/CAIN-PROMOTION-20260912-210027/final` e `C:/CAIN/entregas/stocks-main-integration-20260912`.
Os bancos e respostas com fontes reais permanecem fora do Git.

## O que está resolvido e o que continua limitado

Instalação, atalhos e retestes locais da 0.4.8 foram concluídos.
Pedidos explícitos de campos usam extração literal; ausências e versões conflitantes permanecem visíveis.
Interpretação livre, causas, resumos e comparação semântica geral continuam limitados pelo modelo e pelo corpus.
Nesta rodada o laboratório inventou uma descrição em vez da resposta literal solicitada; a conversa livre também
não respeitou o pedido de uma única frase. Esses casos permanecem falhas semânticas registradas, não aprovados.
Não há certificação científica/econômica, avaliação humana independente ou garantia para qualquer pergunta.

Para mudanças futuras, confira o estado vivo do Git e da instalação. As identidades acima são uma verificação datada, não um monitoramento contínuo.
