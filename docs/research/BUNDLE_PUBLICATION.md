# Publicação autorizada e validação Linux — 12/09/2026

O dono autorizou os commits e o push dos cinco repositórios após o bloqueio local.
As branches existentes são preservadas, sem merge, tag, release ou ativação.
O relatório BUNDLE_REMEDIATION.md e o manifesto congelado descrevem o estado
histórico anterior ao commit; não são reemitidos para apagar essa proveniência.

A CI CAIN Supply Linux gate reconstrói exatamente o candidato
`74da061d1be17326d07d333b7923a717c6ce21c41d6f65f00c5d3947b6d2f248`
usando HEADs anteriores e overlays SHA256, antes de executar testes em Ubuntu
24.04 como usuário comum, Python 3.13/3.14, filesystem Linux nativo.

Os pushes dos produtores suprimem suas CIs gerais. A CI central executa somente
os exportadores e o seletor de metadados, sem campanhas científicas/coortes.
O workflow registra equivalência, ambiente, builds novos, segurança, regressão,
consumo instalado, restore offline e mini-auditoria. Resultados ainda precisam
ser observados; publicação de código não significa estabilização.

## Resultado observado após publicação

Os cinco pushes foram concluídos nas branches de trabalho autorizadas.
A CI geral do CAIN passou em
https://github.com/leonardosovienski/cain/actions/runs/34674661122.
O gate dedicado falhou nas duas versões de Python na etapa `full`:
https://github.com/leonardosovienski/cain/actions/runs/34674661161.

No artefato 3.13: SOURCE_EQUIVALENCE=PASS; 187 testes direcionados passaram,
sem skips, incluindo o teste obrigatório de escape por symlink. Ambiente:
Ubuntu 24.04.5, kernel 6.17.0-1022-azure, x86_64, uid 1001, umask 022,
Python 3.13.15, filesystem reportado por stat como ext2/ext3.
A suíte completa teve 547 passes, 13 falhas, 4 erros e 2 skips.
As falhas/erros observados são FileNotFoundError para os cenários
`evaluation/scenarios/scenarios.json` e `quality-v03.json` na instalação
isolada do wheel; classificação inicial: empacotamento/localização de recursos.
A classificação não significa que o produto foi corrigido.

O fail-fast impediu as etapas posteriores de E2E instalado, restore offline,
testes dos produtores e mini-auditoria nesta execução dedicada. Não se atribui
PASS a essas etapas com base em testes Windows anteriores. Os dois skips da
suíte completa ainda exigem análise. Estabilização: NÃO APROVADA.
Os artefatos originais foram preservados no GitHub; cópia do ZIP 3.13 e dos
logs está em C:\CAIN\work\bundle-linux-ci-20260912.
