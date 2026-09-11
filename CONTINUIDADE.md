# Continuidade do Cain — 0.4.3

Atualizado em 2026-09-11. Este arquivo permite retomar o trabalho sem o chat.

## Instalação e entrada

Nesta máquina, a instalação principal é `C:\CAIN`. Abra `C:\CAIN\ABRIR_CAIN.cmd`;
a interface usa http://127.0.0.1:8877. O guia da instalação é `C:\CAIN\README.md`.
O checkout está em `C:\CAIN\projeto`, na branch `local/l0-historian` de
[leonardosovienski/cain](https://github.com/leonardosovienski/cain).
O código da versão instalada é o commit `67fa5953a573acbfaf00952549bab0ed8cd4d7ba`;
commits posteriores de documentação não alteram o wheel 0.4.3 instalado.

O contrato independente está em `C:\CAIN\contrato`, branch `local/l0-contract`,
commit `1ddc9a51ce14339559e9a57fe6a6760a2cac2e62`. Cada pasta tem seu próprio Git.

## Dados e execução

- `C:\CAIN\dados\workspace.db`: conversas, recibos, preferências e auditoria.
- `C:\CAIN\dados\research.db`: acervo L0 e evidências recebidas.
- `C:\CAIN\config\research-policy.json`: admissões e permissões de pesquisa.
- `C:\CAIN\.venv`: pacote instalado; Python base em `C:\CAIN\runtime\python`.
- `C:\CAIN\entregas`: wheels, fontes, testes, CI e verificações da migração.
- `C:\CAIN\historico`: entrega e prompt originais arquivados.

A instância foi transferida da pasta do chat para esta instalação independente.
O acervo Crypto tem 15 revisões; `heterogeneous` contém quatro revisões documentais
Stocks/Brasileirão. Novas importações continuam admitidas em
`C:\Cripto\cain-l0\publications`. A migração não alterou os projetos vizinhos.

## O que está pronto

Conversa e preferências por escopo; API/CLI/UI; importação, consulta, evidências,
histórico e explicação opcional L0. A 0.4.2 corrigiu seis grupos de bugs.
A 0.4.3 corrigiu as duas pendências de arquitetura: conclusão e resultado durável
na mesma transação, com histórico recuperável/idempotente, e composição de perfil
sem reconstrução do índice global. Consulte [a descrição técnica](docs/ARCHITECTURE_043.md).

Suíte da implementação: **374 aprovados e 1 skip** no Windows. CI aprovada em
Python 3.11, 3.12 e 3.13, incluindo instalação do wheel fora do checkout.
[Execução da versão](https://github.com/leonardosovienski/cain/actions/runs/34611919645).
A migração conferiu igualdade lógica e integridade dos bancos, hashes, runtime,
CLI/API e os dois acervos. Não é necessário repetir pesquisas ou testes científicos
para retomar o desenvolvimento de software.

## Limites que continuam válidos

Ollama/modelos reais continuam sem inferência verificada; nenhum peso foi baixado.
A consulta L0 funciona sem modelo. Não houve avaliação humana de utilidade nem
validação científica/econômica. A conclusão técnica não fecha pendências acadêmicas.
Se um pedido morrer antes do commit de conclusão, o recibo bloqueia repetição
silenciosa; recuperação não inventa um resultado que nunca foi confirmado.

Os relatórios 0.1–0.4.2, resultados datados, notas bibliográficas e documentos de
entrada são históricos. Suas contagens, caminhos e decisões descrevem aquela época;
não devem substituir este estado operacional. As recomendações adicionais da
[auditoria](docs/AUDIT_042.md) permanecem propostas quando não cobertas pela 0.4.3.

## Retomar

Abra este checkout, leia este arquivo e o [índice documental](docs/README.md).
Confira `git status` e a branch antes de alterar código. O ambiente instalado é
não editável: mudar fontes exige testar, gerar e instalar um novo wheel para atualizar
a aplicação. Preserve bancos e arquivos de documentos nas cópias de segurança.
