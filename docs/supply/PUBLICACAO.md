# Publicação final e retomada — CAIN Supply

O código final está diretamente em `src/` na branch `validation/cain-supply-completion-20260912`, commit de runtime **f1f1f5632fe5b6856c31abf6d96c4f0af5780004**. O commit posterior a esse runtime registra somente documentação e o arquivo dos scripts locais de entrega; consulte o HEAD da branch para sua identidade atual.

As duas validações desse commit terminaram com sucesso:

- [CI da árvore normal: lint, testes, build e wheel](https://github.com/leonardosovienski/cain/actions/runs/34704404633).
- [CI do candidato exato: matriz e integrações](https://github.com/leonardosovienski/cain/actions/runs/34704404603).

No Windows, o checkout normal executou 513 testes aprovados e um skip de privilégio de symlink. A contagem anterior de 575 também incluía os testes compartilhados do contrato Bundle; não são populações diferentes por remoção de testes. O código preserva os bytes registrados pelo candidato `d00bbc6fb910b3c51be6720d21012f4655258468adb7d7335451974929c58752`; Git confere os 66 arquivos pertinentes, incluindo finais de linha. O diff volumoso em parte do código decorre dessa preservação dos bytes CRLF.

A revisão suplementar de 33 documentos reais permanece uma avaliação Windows separada. As publicações recebidas com restrição de divulgação, seus bancos/CAS, pesos de modelos e saídas privadas não foram enviados ao GitHub. Estão preservados localmente conforme [LOCAL_LAYOUT.json](LOCAL_LAYOUT.json). A fonte científica e a instância ativa permaneceram intactas.

## Onde continuar no computador

- Entrada: `C:/CAIN/entregas/supply-20260912/LEIA_PRIMEIRO.md`.
- Checkout Git: `C:/CAIN/work/supply-publish-20260912`.
- Candidato instalado e evidências completas: `C:/CAIN/work/supply-final-20260912`.
- Recibo final com igualdade local/remoto: `C:/CAIN/entregas/supply-20260912/GIT_DELIVERY.json`.
- Cópia do código: `cain-source-<HEAD>.zip` na pasta de entrega; wheel e dependências em `pacotes/`.
- [Guia manual](USER_ACCEPTANCE.md), [handoff](FINAL_HANDOFF.md), [fechamento do mandato](FECHAMENTO_DO_PROMPT.md) e [mandato original preservado](evidence/MANDATO_ORIGINAL.md).

Os scripts em `.ci/completion/local-delivery-harness.zip` preservam o trabalho de engenharia. Alguns têm paths e commits históricos fixos ou destinos que precisam ser novos; não executá-los em lote. A existência de scripts não substitui os recibos de execução registrados. O runner finito já completou seu ensaio e não continua rodando.

Não houve merge para main, tag, release, instalação ativa ou scheduler. A entrega segue pronta para revisão de congelamento delimitada e preview limitado em staging. Ganho estrutural neutro e interpretação semântica inconclusiva foram preservados como resultados, sem promover aprovação científica.