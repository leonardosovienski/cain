# Estado verificado do CAIN

Referência operacional verificada em 12/09/2026: **d604a0ed359528acfcf4272d8f2a8ecc11774e65**, publicada e instalada.
Commits posteriores de documentação não implicam reinstalação do pacote nem novos testes do produto.
A branch vigente é main; não usar nomes de branches presentes nos relatórios históricos como instruções atuais.

| Item | Estado verificado |
|---|---|
| Projeto principal | C:/CAIN/projeto, main |
| Segundo checkout de uso | C:/CAIN/work/cain-system-20260912, main |
| Instalação | C:/CAIN/.venv, wheel não editável, CAIN 0.4.7 |
| Serviço principal | http://127.0.0.1:8877/ |
| Contratos | Snapshot 1.0.1 e Bundle 1.0.0 canônicos |
| Código integrado | Saudações, Historian, consultas compostas, Supply e contratos |
| Git | Publicação conferida e branches integradas removidas na promoção |

## Evidências

- [CI da referência operacional](https://github.com/leonardosovienski/cain/actions/runs/34727241470): aprovada.
- Rodada de perguntas compostas: 606 testes da fonte e 106 do pacote aprovados, com um skip Windows em cada bateria e dois avisos de depreciação.
- Essas contagens são da rodada anterior à promoção; a CI acima valida a referência conjunta, incluindo contratos finais e correção de imports.
- Na instalação principal: tarefa real H4, citações e offsets, saudação “oi”, consulta por CLI e verificação dos arquivos instalados aprovadas.
- Os registros e grants preexistentes foram preservados; os acervos Stocks adicionados pela tarefa de integração têm escopo próprio.

Identidade exata dos três wheels e caminhos dos recibos: [manifesto operacional](operational-state.json).
Recibos locais: `C:/CAIN/work/CAIN-PROMOTION-20260912-210027/final` e `C:/CAIN/entregas/stocks-main-integration-20260912`.
Os bancos e respostas com fontes reais permanecem fora do Git.

## O que está resolvido e o que continua limitado

Publicação, instalação, atalhos e a consulta composta que motivou a correção foram concluídos.
Pedidos explícitos de campos usam extração literal; ausências e versões conflitantes permanecem visíveis.
Interpretação livre, causas, resumos e comparação semântica geral continuam limitados pelo modelo e pelo corpus.
Não há certificação científica/econômica, avaliação humana independente ou garantia para qualquer pergunta.

Para mudanças futuras, confira o estado vivo do Git e da instalação. As identidades acima são uma verificação datada, não um monitoramento contínuo.
