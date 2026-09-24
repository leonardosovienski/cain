# Histórico documental preservado

Para o estado atual, leia [ESTADO_DO_PROJETO.md](../../ESTADO_DO_PROJETO.md).
Relatórios datados e evidências congeladas mantêm seus bytes e o escopo da rodada. Referências a branches removidas continuam úteis como histórico de commits.

## Documentos de entrada substituídos

A revisão documental de 12/09/2026 consolidou README, CONTINUIDADE, ESTADO_DO_PROJETO, PUBLICATION_STATUS, SETUP_GITHUB e os índices docs/README e docs/supply/README.
As versões completas anteriores estão no commit [d604a0e](https://github.com/leonardosovienski/cain/tree/d604a0ed359528acfcf4272d8f2a8ecc11774e65), nos mesmos caminhos.
Para recuperar um documento sem substituir o arquivo atual:

```powershell
git show d604a0ed359528acfcf4272d8f2a8ecc11774e65:CONTINUIDADE.md
```

O README anterior da raiz C:/CAIN e cópias dos índices foram preservados localmente em `C:/CAIN/historico/CAIN-DOCS-20260912-212110`.
O [estado e documento mestre anteriores](estado-antes-da-revisao-20260912.md) e o [README anterior da instalação](instalacao-antes-da-revisao-20260912.md) também foram copiados integralmente para este diretório.
Nessas cópias, links e caminhos conservam o contexto original; use a referência Git acima para navegar a árvore daquela versão.

## Recortes anteriores

- [Consolidação inicial em main](../MAIN_CONSOLIDATION_20260912.md).
- [Supply](../supply/README.md) e [handoff da rodada](../supply/FINAL_HANDOFF.md).
- [Entrega 0.4.7 original](../DELIVERY_047.md).
- [Auditoria Brasileirão de 16/09/2026](brasileirao_auditoria_20260916/README.md): os nove documentos da branch `checkpoint/brasileirao-auditoria-20260916` (commit `e402de5`), cujo código já estava em `main` desde `7d64d4c`. Copiados byte a byte dos blobs daquela branch. O `PUBLICATION_SHA256.json` original confere para `README.md` e `test_cain.py`; cinco arquivos conferem só ao reconverter para CRLF (foram registrados no Windows e a branch os guardou com LF) e `PROMPT_INICIAR_CAIN.md` não confere em nenhuma forma, então seu hash registrado descreve outra versão. Rodada científica não executada; caminhos locais e a branch do `brasileirao-predictor` são referências históricas.
- [Manifesto operacional de 13/09/2026](operational-state-20260913-0.4.12.json): fotografia da instalação 0.4.12 no commit `5364c3b`, antes na raiz como `operational-state.json`; bytes preservados.
- Documentos originais em importacao e documentação conflitante preservada em consolidation-20260912.

Esses registros não são instruções atuais de instalação. Contagens antigas, modelos observados e pendências de uma rodada não devem ser somados ou promovidos a validação atual.
