# Repositório e verificação

O repositório está publicado em [leonardosovienski/cain](https://github.com/leonardosovienski/cain).
As correções atuais estão na branch `fix/historian-integrity-20260912`,
checkout `C:/CAIN/work/historian-operational-fix-20260912`. O código instalado
é `0c8814901d3d365a2eec4b0c7386b59f460d349d`; os commits posteriores de
Markdown documentam a entrega. Consulte [CONTINUIDADE.md](CONTINUIDADE.md)
para wheel, testes, recuperação e verificação exata do remoto. Não presuma
que main ou outra branch contém estas correções.

As branches `local/l0-historian`, `feature/research-capabilities-20260911` e
`architecture/complete-20260911` registram entregas anteriores. A branch
`validation/cain-supply-completion-20260912` é outra linha de trabalho;
a publicação desta correção não promove automaticamente a arquitetura Supply.

O primeiro commit preserva os documentos de entrada. Os seguintes registram
instrumentos e implementação. Um commit local datado não demonstra, sozinho,
um pré-registro científico independente. O smoke usa dados sintéticos e não
substitui a aceitação do ADR-0010 nem uma coleta definitiva.

Depois de clonar, seguir o README. O workflow CI roda lint e testes. Logs de
testes e smoke local ficam em `evaluation/results/` com classificação explícita.
