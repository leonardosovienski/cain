# Publicacao do checkpoint local — 15/09/2026

O dono autorizou publicar o estado local e determinou expressamente que nenhum arquivo local seja apagado.

Esta publicacao parte do checkpoint `24f784c5dde1fa66c262ad5899f4fd8d02526adf`, preserva seu historico e captura 14 arquivos alterados ou novos. Durante a preparacao houve trabalho concorrente no checkout original; o dono autorizou publicar uma copia isolada do estado atual, identificada como checkpoint em andamento. Nao representa merge com main, release, instalacao principal ou validacao cientifica concluida.

## Conteudo das alteracoes preservadas

- Selecao de contexto retendo preambulo documental, identidade e revisao de registros JSON.
- Prompt de revisao com conflitos explicitos e separacao entre codigo de saida, comando e experimento.
- Preparador de catalogo com objetos JSON completos e registros JSONL separados.
- Catalogo de fontes e testes associados, incluindo referencias Stocks preexistentes. Nenhum arquivo do produtor Stocks foi alterado nesta publicacao.
- Alteracoes concorrentes capturadas: transcricao literal de tabelas de claims, qualificacao de hipoteses e testes associados. A copia publicada nao acompanha edicoes posteriores no checkout original.

Os registros de falhas semanticas e as limitacoes documentadas continuam validos ate um teste posterior demonstrar melhoria. Acrescentar fontes ou passar testes unitarios nao demonstra compreensao, reproducao de hipoteses ou aprendizado do modelo.

## Preservacao e reproducao

Historico Git de recuperacao verificado em `C:/CAIN/work/publicacao-20260915/antes.bundle`.
Recibos desta publicacao ficam na mesma pasta, fora do Git. A instalacao principal nao possui pytest; as verificacoes usam ambiente QA separado. Contratos Snapshot e Bundle vieram dos wheels de vendor; ferramentas e dependencias de teste foram instaladas somente em QA. A primeira coleta de testes sem essas dependencias falhou e seu log foi preservado.

Bancos, credenciais, modelos, ambientes, recibos privados e configuracoes pessoais permanecem locais. Esta publicacao de fontes nao e backup integral de C:/CAIN. A futura validacao com hipoteses deve separar recuperacao, interpretacao e execucao de calculos, usando corpus autorizado e gabaritos externos ao contexto do modelo.

## Verificacoes desta copia

- Suite de 792 casos: 787 aprovados, quatro falhas de subprocessos por pacote cain ainda nao instalado em QA e um skip por privilegio Windows de symlink; 295,20 s.
- Instalado o wheel da mesma copia em QA, os quatro casos foram repetidos e passaram em 23,24 s. Sao 791 casos aprovados entre as duas execucoes, nao uma suite unica sem falhas. Os logs anteriores permanecem preservados.
- Ruff e scanner de segredos aprovados; zero ocorrencias do scanner no escopo de fontes Git.
- Build aprovado; wheel `dfbae440721fa6115bcca6628bc993e720e4e7b39984c5b5b65ff89a3326a000`.
- Instalacao adicional separada: 71 arquivos identicos entre fonte, wheel e pacote instalado; CLI --help e pip check aprovados. Nenhuma instalacao principal atualizada.
- Dois avisos de depreciacao das dependencias Starlette/httpx/AnyIO permanecem registrados. Nao houve nova inferencia real nem certificacao semantica nesta publicacao.
