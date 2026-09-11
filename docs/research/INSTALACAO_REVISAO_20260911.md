# Publicação e instalação operacional da revisão independente

Em 11/09/2026, após a revisão independente, o usuário autorizou explicitamente
“faz push + instalaçao operacional”. Essa autorização substitui a restrição de
instalação/publicação da etapa anterior. Não houve merge em main nem alteração
nos checkouts das outras branches.

## Versão em operação

- Código testado e instalado: `86c38f8a333f278084adac3abc2ebe40c48b616c`.
- Branch publicada: `review/individual-models-20260911`; documentação posterior
  não altera o código do wheel. O recibo local de publicação registra o HEAD final.
- Pacote mantém versão 0.4.7. Wheel SHA-256:
  `ce43f2bed45be8b191da775aa85d643453e6200d94ff0e8a0044b51b3cf18600`.
- Instalação não editável: `C:\CAIN\.venv`, offline, sem reinstalar dependências.
- Novos workflows: `research-workflow/6`; prompt `addressable-review/4`.
  Jobs antigos continuam legíveis/canceláveis; não foram migrados.

Abra `C:\CAIN\ABRIR_CAIN.cmd` ou http://127.0.0.1:8877. Os atalhos e a
configuração continuam no worktree `research-capabilities-20260911`; o código
executado vem do wheel instalado, não do src daquele checkout. A origem das
correções é a branch de revisão. Não reinstalar pelo checkout antigo por engano.

## Verificação da instalação

Os 50 arquivos cain/ instalados conferiram byte a byte com o wheel. `pip check`
passou. Health HTTP e página inicial responderam após reinício. O gerador padrão
qwen3.5:0.8b respondeu OK e encerrou streaming corretamente no pacote instalado.

Os bancos operacionais permaneceram byte a byte inalterados, assim como política,
configuração e atalhos. Em uma cópia do banco, o verificador instalado confirmou
15 registros Crypto, um Stocks e três Brasileirão, hashes das fontes, reconstrução
local e restauração com todas as raízes dos produtores indisponíveis. Nenhuma
pesquisa financeira foi executada. Os 447 testes por Python 3.12/3.13 da revisão
continuam aplicáveis ao mesmo código; não se apresenta esta instalação como nova
aprovação semântica ou como CI já concluída para o commit documental final.

As limitações e falhas reais dos modelos permanecem descritas em
[REVISAO_INDEPENDENTE_20260911](REVISAO_INDEPENDENTE_20260911.md).

## Evidências e reversão

Recibos privados: `C:\CAIN\entregas\operational-review-20260911`.
`before-data` guarda os bancos anteriores; `before-files` guarda configuração,
atalhos e README anterior. `installed-receipt.json`, `installed-archives/report.json`,
`install.log` e `installed-generation.jsonl` registram as verificações. O manifesto
operacional registra arquivos e hashes; `publication.json` registra HEAD local/remoto.

Para reverter somente o código, interrompa o servidor CAIN identificado na porta
8877 e reinstale o wheel anterior, preservado com seu nome válido:

```powershell
C:\CAIN\.venv\Scripts\python.exe -m pip install --no-index --no-deps --force-reinstall C:\CAIN\entregas\operational-review-20260911\rollback\cain_research-0.4.7-py3-none-any.whl
```

Depois reinicie por `ABRIR_CAIN.cmd`. Wheel anterior SHA-256:
`31ed5526ac08a4d2a9e875de953656eeb10eff2b91dbe5a5c49690b5dc8c64e3`.
Não restaurar bancos automaticamente: a atualização não os alterou, e podem
existir novos dados de uso posteriores. As evidências da revisão anterior e seu
manifesto congelado permanecem intactos em `entregas\independent-review-20260911`.
