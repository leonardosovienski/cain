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

## Recibo final

- Código instalado: `4762da0bdc39d4933cd25ae34916c61724ec6d09`.
- Wheel SHA-256: `31ed5526ac08a4d2a9e875de953656eeb10eff2b91dbe5a5c49690b5dc8c64e3`.
  Cinquenta arquivos do pacote conferidos byte a byte entre instalação, wheel e
  checkout. Instalação offline em venv vazio e pip check aprovados.
- [CI desta revisão](https://github.com/leonardosovienski/cain/actions/runs/34636221829):
  Python 3.11, 3.12 e 3.13 aprovados. A documentação posterior não muda o código.
- Backup completo e restauração aprovados em `before-backup` e `restore-check`.
  Verificação instalada dos três acervos e restauração sem pastas dos produtores
  aprovada em `installed-archives`, com 15, 1 e 3 registros, respectivamente.
- Interface reiniciada: H6 exibiu estado e trial separados sem inferência; fluxo
  antigo Stocks abriu análises/citações legíveis e preservou as duas abstenções
  históricas. Não reinterpretamos esses resultados antigos como novos sucessos.
- Em `installed-workflows`, os três fluxos novos concluíram seis etapas, com
  nove reviews aceitos por referência e sem abstenção do operador. Os registros,
  estados e cobertura permaneceram iguais. IDs: Crypto
  `dab5c4e6cc34422abf4135581f170153`, Stocks `3bee0d5507fa4e7880cfe28c27330bcd`,
  Brasileirão `d3244cc8f3314195ac8de2aa8adc4a0e`. Estão no banco de avaliação
  isolado, sem adicionar jobs de teste ao banco operacional.
- O primeiro verificador de workflows comparava também o ID aleatório da consulta;
  falhou após seis etapas Crypto. `real-final` preserva esse ensaio. A comparação
  corrigida usa registros completos, contagem e cobertura, excluindo o recibo
  variável. Nenhuma fonte foi alterada para fazer o teste passar.

Comparação estrutural no protocolo separado: 0.4.6 acertou 0/4 expectativas;
0.4.7 acertou 4/4. Ambas resolveram citações nas quatro respostas de prosa.
Isso demonstra a correção dos campos nesses casos, não ganho semântico geral.
Nas sínteses reais ainda houve mistura entre H6 e H1 e a expressão inadequada
de retornos “reais ou fictícios” no caso Stocks. As citações existem, mas não
certificam essas inferências. Qualidade interpretativa e avaliação humana ampla
continuam limitações; a entrega não as apresenta como problemas resolvidos.
