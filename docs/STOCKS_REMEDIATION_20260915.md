# Stocks: leitura literal e contexto histórico — 15/09/2026

Documentos JSON eram cortados em blocos inválidos e ledgers JSONL eram tratados
como um único JSON. O seletor também perdia avisos iniciais de revisão e completava
o contexto com trechos históricos pouco relacionados à pergunta. Isso contribuiu
para respostas que apresentavam estados antigos como atuais.

## Alterações

- `json_document` conserva o objeto inteiro; `jsonl` conserva cada observação e
  seus offsets. Ambos rejeitam objetos ambíguos e valores JSON não finitos.
- Identidade, revisão, data e estado explícitos do objeto acompanham métricas.
- Listas JSON simples permanecem valores nomeados literais, inclusive listas
  vazias, valores nulos e repetições; `replay_exit_codes: [2, 2]` não desaparece.
- Aviso inicial acompanha seções históricas, inclusive H2/H3 antes de H1. Se o
  contexto obrigatório não cabe, a afirmação associada é omitida. Hipóteses irmãs
  nomeadas não são tomadas como contexto uma da outra.
- Perguntas com correspondência de vários termos não recebem preenchimento
  adicional baseado em uma palavra genérica. Identificadores explícitos conservam
  sua seleção própria. A cobertura registra `weak_query_overlap`.
- Caminho de documento explicitamente citado na pergunta filtra as fontes e
  mantém suas revisões; não o transforma em identidade de hipótese. A cobertura
  registra as exclusões como `explicit_source_mismatch`.
- Instrução do modelo exige preservar conflitos e distinguir código de saída,
  comando e execução. Não há vereditos Stocks embutidos no código.
- Consultas com pelo menos dois nomes explícitos de campos `snake_case` recebem
  os valores JSON selecionados e abstenção expressa de interpretação. Caminhos,
  versões, repetições, `false` e `null` são preservados. A resposta não transforma
  um código em sucesso/falha econômica. Este modo literal usa zero chamadas de
  modelo; não certifica nem corrige o raciocínio livre do LLM.
- Seleção Stocks: 39 para 47 fontes. Depois de preservar JSON completo, são
  86 ocorrências; não são 86 hipóteses. As contagens anteriores 85/87 correspondem
  a etapas históricas e foram preservadas.

## Isolamento

Base: `24f784c5dde1fa66c262ad5899f4fd8d02526adf`. Branch de entrega:
`checkpoint/stocks-remediation-20260915`. Produtor lido:
`3066321e599ee15dd0ace4167d2791545ce6eb95` no Stocks.

Uma tarefa concorrente passou a alterar o checkout compartilhado durante o teste.
A candidata Stocks foi reconstruída do patch preservado e das correções desta
etapa em worktree isolada; não inclui essas alterações concorrentes. Nenhum arquivo
do checkout compartilhado foi restaurado, excluído ou limpo.

QA usa identidade `qa-stocks-remediation`, banco próprio e publicações próprias;
nenhum gabarito entrou no corpus, nenhum banco principal ou instalação foi alterado.
Ollama usa porta própria 11437, Qwen3.5:4b existente, temperature 0, seed 42,
num_ctx 8192, num_predict 768, think=false, orçamento 6500 bytes. Timeout 600s
somente em QA; não houve download de modelo ou mudança de configuração principal.

## Validação

Os resultados finais e tentativas anteriores estão no [recibo de QA](STOCKS_QA_20260915.json).
Suíte final da candidata: **794 aprovados, 1 pulado, 2 avisos de depreciação de
dependências**, em 113,86s. Ruff e verificação de whitespace aprovados. A suíte
rodou com o contrato Bundle vendorizado no PYTHONPATH, sem instalar dependências.
As respostas são revisadas contra os trechos efetivamente entregues, não apenas
pela presença de citações. Testes reais conhecidos não são amostra independente.

- A02 inicial: timeout de transporte a 240s; tentativas posteriores apresentaram
  contradições temporais, que permanecem registradas como reprovações.
- Teste final anterior: interrompido pela troca do ambiente, sem resposta; não passou.
- Tentativas no checkout concorrente não homologam a candidata isolada.
- Na consulta genérica sobre H19/código 2, a busca não entregou a decisão e a
  resposta reconheceu falta de suporte; também respondeu em inglês. Isso não é
  aprovação da recuperação ou da adequação linguística. A consulta com caminho
  explícito e nomes de campos é um caso separado, sem ocultar a limitação genérica.
- Suíte de 786 aprovados/1 pulado anterior às últimas mudanças é histórica.
- A02 e H17 finais conservaram os limites dos trechos selecionados. H17 recebeu
  uma revisão observada; isso não atesta comparação completa entre revisões.
- A resposta livre final sobre reprodução continuou semanticamente incorreta,
  mesmo recebendo a lista de códigos. O mesmo enunciado agora recebe leitura
  literal e abstenção, verificadas separadamente, sem ocultar essa reprovação.
- A primeira suíte isolada foi interrompida depois de revisão adicional dos termos
  de busca; seu log parcial foi preservado e não conta como suíte final aprovada.

Arquivos completos de QA permanecem em `C:/CAIN/work/stocks-remediation-20260915`;
o recibo público contém resultados, respostas, hashes e limites, não bancos, políticas
pessoais, modelos ou corpos extensos das publicações. Nada local foi apagado.

## Limites e entrega

O manifesto de fontes e a auditoria científica ficam no repositório Stocks,
`docs/audit/2026-09-15-review/README.md`. Os 794 hashes não comprovam leitura
semântica integral; dados líquidos, cadeias societárias e janela prospectiva
continuam com suas limitações. A adequação pessoal foi excluída pelo usuário.

Publicar esta branch não faz merge em main, não instala a candidata e não valida
lucro. Uma futura integração deve reconciliar as mudanças concorrentes e repetir
os testes afetados. Os protocolos e resultados negativos foram preservados.
