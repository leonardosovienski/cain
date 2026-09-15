# Consolidacao em main — 15/09/2026

O dono autorizou conferir todas as branches, integrar o conteudo util e manter somente main. Nenhuma pasta de trabalho, banco, configuracao ou modelo deve ser apagado.

## Revisao das branches

| Branch | Conclusao |
|---|---|
| checkpoint/conversa-v2-parcial-20260914 | Commit 24f784c ja estava incorporado a main pelo PR 2. |
| checkpoint/stocks-remediation-20260915 | Mesmo commit 24f784c, sem commits exclusivos; edicoes nao commitadas continuam preservadas na pasta original. |
| fix/readiness-main-20260914 | Oito commits adicionais com memoria, contexto, selecao de evidencias, testes e historico V4-V8; incorporados integralmente. |
| publish/cain-checkpoint-20260915 | Acrescenta tabelas literais, contexto documental/JSON, catalogo e testes; integrado ao trabalho V8, preservando ambos os historicos. |

O merge `b8373ea` conserva ambas as linhas de desenvolvimento. Os conflitos foram resolvidos combinando balanceamento por identidade, motivos de encerramento e resultados explicitos da V8 com preambulos, contexto de registros JSON e tabelas literais do checkpoint. O catalogo preserva a identidade nativa H17 e as fontes adicionais. O prompt combinado e `addressable-review/17`; a selecao e `identity_balanced_excerpts/10`.

## Estado local e recuperacao

Main e validada em `C:/CAIN/work/consolidacao-main-20260915/source`. As pastas anteriores com trabalho pendente permanecem intactas, desvinculadas das branches removidas (HEAD destacado). Isso preserva seus arquivos sem misturar edicoes ainda nao commitadas com a integracao testada.

Bundle de recuperacao: `C:/CAIN/work/consolidacao-main-20260915/antes.bundle`, conferido antes da integracao. Os recibos, as copias das edicoes pendentes e o manifesto de preservacao ficam no mesmo diretorio, fora do Git.

A instalacao principal continua separada desta consolidacao de codigo. Testes de engenharia e merge nao certificam compreensao, execucao de hipoteses, aprendizado ou resultado economico. As falhas semanticas historicas permanecem documentadas.

## Validacoes da integracao

- 132 testes direcionados aprovados apos resolver os conflitos.
- Suite completa: 854 aprovados, um skip de symlink por privilegio Windows, zero falhas, 293,04 s. Dois avisos de depreciacao das dependencias foram preservados.
- Ruff, diff check e scanner de segredos aprovados; zero ocorrencias do scanner nas fontes Git.
- Build e instalacao isolada aprovados; 71 arquivos iguais entre fonte, wheel e instalacao; CLI --help aprovada.
- Wheel SHA256: `9e3465d565df90599961c59d09424d349e732bbb28e76a3a35bae8a4849316fa`.
