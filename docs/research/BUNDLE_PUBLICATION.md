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
