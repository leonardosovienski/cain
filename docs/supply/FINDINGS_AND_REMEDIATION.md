# Findings e remediação final

Relatórios e candidatos anteriores foram preservados. F01–F10: mapa em F01_F10_MATRIX.json, relatório original em C:/CAIN/work/bundle-audit-20260912/REPORT.md e remediação histórica em C:/CAIN/work/research-bundle-v1/docs/research/BUNDLE_REMEDIATION.md.

- Distribuição: os quatro recursos de avaliação foram empacotados sem regenerar seus bytes; instalação fora do checkout e comparação com os originais passaram.
- Revisão independente R1: payload adulterado de diagnóstico era retornado como válido. Agora há recomputação dos campos estruturais e checagem de identidade. Regressões de corrupção passaram.
- R2: paginação e persistência do diagnóstico não compartilhavam snapshot. Leitura usa uma transação; criação reserva escrita antes de ler. Probe WAL com ingestão concorrente retornou snapshot coerente, depois invalidou o diagnóstico anterior.
- R3: runner excedia quota ao serializar resultados. Agora limita captura em memória, considera resultado/checkpoint/temporários, e para com LIMIT_REACHED. Probe usou 559 de 4096 bytes. Uma regressão inicial de sobrescrita de checkpoint foi corrigida e re-revisada; configurações rejeitadas preservam o checkpoint e gravam LAST_LIMIT separado.
- Identidade passou a incluir bytes de Bundle/Snapshot. Ruff dividiu imports e formatou o runner; comparação AST independente não encontrou alteração funcional.
- Linux: fixture Stocks usava diretório fixo Windows. Mudou somente a fixture em overlay isolado C:/STOCKS/work/supply-portability-20260912. Runtime e fontes Stocks permaneceram intactos.
- Ensaio Linux Bundle inicialmente escolheu destino fora da área permitida do produtor. A proteção recusou; apenas o harness mudou para destinos irmãos dos checkouts. Repetição final passou.
- Modelo: timeout de 90 s em Brasileirão foi preservado. Uma tentativa serial de 180 s passou. Não houve fallback remoto nem mudança de modelo. Citações literais passaram, mas a síntese Stocks introduziu interpretação sobre indivíduo sem apoio; continua experimental e não é recomendação.
- Comparação derivada: a primeira fixture adversarial conflitava com uma identidade/revisão já aprovada. A recusa foi correta. Nova revisão explícita da fixture permitiu testar conteúdo hostil sem reescrever a identidade anterior. Resultado estrutural neutro; contradição, revogação e restore passaram. Os seis bundles reais continuaram negando geração.
- Verificador final inicialmente exigia zero skips de qualquer espécie no Linux. Foram identificados exatamente dois testes exclusivos de launcher Windows, ambos aprovados no Windows. O verificador passou a conferir essa correspondência; nenhum gate POSIX/symlink obrigatório foi removido.

Limitações de observabilidade: RAM de pico não medida; quota de armazenamento do harness não é quota de kernel. A preservação científica combina comandos efetivamente executados, Git e hashes selecionados; não é auditoria de todos os reads/writes do sistema.
