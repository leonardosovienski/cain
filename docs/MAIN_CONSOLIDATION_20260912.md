# CAIN consolidado em main — 12/09/2026

Esta consolidação atende à solicitação explícita de reunir o trabalho deste
chat e das demais branches do CAIN em uma única branch, `main`.

## Conteúdo e histórico

Foram inventariados os dois repositórios locais do mesmo remoto
`https://github.com/leonardosovienski/cain.git`, em `C:\CAIN\projeto` e
`C:\CAIN\work\supply-publish-20260912`, incluindo seus worktrees.
Todos estavam limpos. Não foram alterados repositórios de contratos ou produtores.

O ponto de partida foi `fbee633`: inclui o mandato integrado, Bundle, avaliação
de modelos, seleção de evidências, procedimentos retomáveis, correção de revogação,
resumos curtos literais e resposta a saudações. A antiga main remota, `2e9350c`,
já era ancestral desse trabalho.

Foram feitas integrações com dois pais, preservando histórico:

- `9001a33`: Supply, documentação, ferramentas e candidatos históricos Linux.
- `8b43282`: documentação da auditoria e instalação operacional anterior.

As demais pontas já eram ancestrais. O inventário verificável está em
[main-branch-audit.json](main-branch-audit.json): 13 nomes de branches anteriores
representados localmente, referências remotas conferidas, todos os commits finais
alcançáveis pela main e nenhum caminho de arquivo ausente em relação às pontas.
Isso preserva conteúdo e histórico; versões conflitantes não podem ocupar o
mesmo arquivo simultaneamente. Suas versões originais continuam acessíveis pelos
commits registrados no inventário.

Conflitos resolvidos: mantidas as correções recentes do Historian e a busca
literal na avaliação; diferenças somente de fim de linha não substituíram código.
A avaliação passou a registrar também a identidade da dependência research_bundle.
As versões da documentação operacional conflitante foram preservadas em
`docs/historico/consolidation-20260912`; os documentos de entrada apontam aqui.

Os workflows de reconstrução de candidatos congelados permanecem disponíveis
por workflow_dispatch, identificados como históricos. Eles não representam
validação do código atual. A CI normal testa main em Python 3.11 a 3.14,
incluindo build e verificação da instalação não editável.

## Verificação e recuperação

Suíte consolidada no Windows: **586 passaram, 1 ignorado, 2 avisos de
depreciação, 149,92 segundos**. Ruff passou. O teste ignorado requer Linux.
O resultado local não antecipa o resultado da CI remota.

Recibos locais e bundles Git completos, verificados antes da integração:
`C:\CAIN\entregas\git-consolidation-20260912`.
Arquivos `system-before.bundle` e `project-before.bundle` conservam as refs
originais e permitem reconstrução com `git clone <arquivo.bundle> <destino>`.
O inventário completo dos checkouts está em
`C:\CAIN\work\cain-system-receipts-20260912\consolidation-inventory.json`.

A remoção de branches ocorre somente depois da publicação de main e da
conferência de ancestralidade. Worktrees históricos ficam em HEAD destacado,
sem exclusão de suas pastas. `C:\CAIN\projeto` passa a acompanhar main; o
checkout desta consolidação é `C:\CAIN\work\cain-system-20260912`.
Nenhum banco, modelo ou instalação principal é substituído por esta operação Git.

Os limites semânticos dos modelos registrados em
[SYSTEM_VALIDATION_20260912.md](research/SYSTEM_VALIDATION_20260912.md) continuam
válidos. Consolidação e CI não equivalem a aprovação científica ou econômica.
O resultado final dos testes, HEAD publicado, inventário após limpeza e hash
do pacote constam no recibo de entrega desta consolidação.
