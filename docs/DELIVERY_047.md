# Cain 0.4.7 — integração, extração literal e debate com fontes

Entrega de 11/09/2026. Integra a arquitetura `2e9350c` ao worktree
`C:\CAIN\work\research-capabilities-20260911`, branch
`feature/research-capabilities-20260911`. Factories compartilhadas, preflight de
permissões e proteção do histórico revogado agora convivem com as capacidades
da [versão 0.4.6](DELIVERY_046.md). O checkout `C:\CAIN\projeto` foi preservado.

## O que mudou

- JSON e tabelas de duas colunas usam extração literal, sem chamada ao modelo.
  Caminhos JSON distinguem estado de trial; `false`, Unicode e strings escapadas
  mantêm seus valores e trechos originais. JSON com chaves duplicadas é ambíguo.
- Em texto livre, relações continuam propostas pelo modelo e exigem suporte
  literal. Nenhuma relação proposta é promovida ao grafo factual.
- Suporte, crítica e síntese selecionam IDs curtos. O consumidor recupera a
  citação exata e seus offsets e revalida o acesso. IDs inventados são recusados.
  A análise recebe instrução explícita de idioma. Uma limitação da fonte pode
  ser uma resposta válida; ausência de evidência recebida produz abstenção.
- A interface mostra análises, campos e citações antes do recibo JSON completo.
- Novos workflows fixam `research-workflow/4` e `addressable-review/2`. Jobs
  antigos continuam consultáveis/canceláveis; seus prompts não são trocados
  durante a retomada. Crie um novo fluxo para usar esta versão.

O seletor de trechos é lexical, limitado a oito excertos e 2.200 bytes. O recibo
mostra a cobertura; não afirma leitura integral. Citação correta não certifica
interpretação correta. Os papéis usam o mesmo modelo local, sem independência.

## Verificação reproduzível

425 testes locais passaram, um teste foi pulado no Windows e duas advertências
de depreciação vieram do cliente de testes. Ruff passou. O protocolo
[grounded-analysis-disjoint/1](../evaluation/grounded-analysis-20260911.json)
foi congelado antes da implementação e inclui quatro casos estruturais e dois
casos de prosa com perguntas PT/EN. Os quatro casos estruturais passaram e as
quatro respostas resolveram citações recebidas. Estados das fontes preservados.

Os casos foram escritos pelo implementador: são avaliação automática separada
dos casos anteriores, não avaliação humana independente. A resposta ao teste de
injeção não prometeu lucro, mas sua interpretação em inglês permaneceu imprecisa;
esse resultado não é prova de robustez geral contra injeção ou de qualidade
semântica. Nenhuma superioridade geral é alegada.

Recibos em `C:\CAIN\entregas\0.4.7`. `disjoint-new` preserva o primeiro ensaio:
o harness misturava duas revisões sintéticas de K17 no mesmo banco. A correção
usa um banco por caso em `disjoint-isolated`, sem mudar casos nem expectativas.
`disjoint-baseline` mede a versão instalada anterior com os mesmos casos.
`real-workflows.json` preserva a revisão inicial dos prompts, que confundia
insuficiência da fonte com abstenção do assistente; o protocolo /4 elimina esse
campo de decisão. O conteúdo do modelo continua uma proposta não certificada.

```powershell
python tools/verify_grounded_analysis.py --protocol evaluation/grounded-analysis-20260911.json --config cain.toml --output CAMINHO_NOVO
python tools/verify_grounded_workflows.py --db C:\CAIN\dados\research.db --policy C:\CAIN\config\research-policy.json --config cain.toml --protocol evaluation/agent-capabilities-20260911.json --output OUTRO_CAMINHO_NOVO
```

## Cobertura das propostas

| Família pertinente | Entrega acumulada |
|---|---|
| Memória e histórico | Preferências, sessões, revisões, proveniência, linha do tempo, comparação e backup/restauração |
| Recuperação | Documentos e L0, busca lexical/híbrida, embeddings locais, filtros e cobertura |
| Análise com fontes | Dossiê, relações literais/propostas, suporte, crítica e síntese citados |
| Execução de análise | Seis etapas registradas, persistência, retomada, cancelamento, falhas e abstenção explícita |
| Interface e modelos | Playground, texto/imagem local, streaming, interrupção e seleção de modelos |
| Integração e diagnóstico | CLI/API, MCP local, traces OTLP, métricas, protocolos de avaliação e wheel offline |
| Arquitetura | Providers compartilhados, isolamento de acervos, admissão antes da leitura e revogação |

O inventário histórico dos rivais está em
[capability-inventory](research/capability-inventory-20260911.md). Estas são as
capacidades implementadas no mandato de consulta e análise. Não constituem
paridade integral com produtos comerciais. Valuation com novos dados, feeds
pagos, ordens, apostas, backtests e execução científica dos produtores exigem
outro mandato e dados próprios. Hospedagem distribuída e troca de frameworks
não são necessárias ao uso local. Avaliação humana independente não pode ser
substituída por mais testes escritos pelo próprio implementador.

Abra `C:\CAIN\ABRIR_CAIN.cmd`, porta 8877. Dados permanecem em `C:\CAIN\dados`;
não publique bancos, políticas ou respostas privadas no GitHub. Modelos e runtime
permanecem locais, com a configuração e licenças descritas na entrega anterior.
