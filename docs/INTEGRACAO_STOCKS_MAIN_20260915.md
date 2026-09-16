# Integração Stocks com main — PR #3

A PR apresentava seis conflitos porque `main` incorporou a consolidação V8 e
outra continuação de pesquisa depois da criação da candidata Stocks. Esta revisão
concilia os commits `2bdb5705b8b4819ab9886f0e963befad4e7bd389` (main) e
`f6c86d32fc7ef92e0fab5d8bc01f6a19cfc31f47` (Stocks), preservando ambas as histórias.

## Resolução

| Área | Resultado |
|---|---|
| Revisão de pesquisa | Mantém integralmente `analysis.py` da main: tabelas literais, cobertura por identidade, orçamento e prompt `/17` |
| Seleção | Mantém balanceamento por identidade, motivos, resultados e contexto compartilhado da main; incorpora filtro por documento, listas JSON literais e termos genéricos da candidata Stocks |
| Catálogo | Mantém integralmente o catálogo da main, inclusive H17 `observation_jsonl` com identidade nativa e as fontes de todos os projetos |
| Exportador | Preserva os modos combinados e passa a `/4`, evitando reutilizar `/3` para duas implementações diferentes |
| Consulta de campos | Mantém a proteção literal `/3`, sem transformar `false`, `null` ou códigos em veredictos |
| Testes | Conserva as regressões dos dois lados, incluindo listas, revisões, tabelas e contexto |
| Markdown | Atualiza entradas de navegação e estado; identifica relatórios anteriores como históricos, sem reescrever seus recibos |

As regras de bytes congelados foram respeitadas: análise e catálogo permanecem
idênticos aos da main, e grounding conserva sua convenção de final de linha.
Não houve atualização de produtores, banco principal, instalação ou configuração.
Nenhum arquivo local, branch ou artefato foi excluído.

## Validação desta composição

- Suíte completa: **861 aprovados, 1 pulado, 2 avisos de depreciação**, em 149,43s.
- Ruff e verificação de whitespace aprovados; nenhum marcador de conflito restante.
- Os 15 links locais das entradas correntes de documentação foram conferidos.
- `analysis.py` e catálogo conferidos byte a byte contra a main de partida.
- Catálogo Stocks: **48 fontes, 87 ocorrências**, todos os hashes conferidos;
  inclui `EXPERIMENTS.md` acrescentado pela main às 47 fontes da candidata anterior.
- Contrato Bundle vendorizado no PYTHONPATH; nenhuma dependência instalada.

Logs locais: `C:/CAIN/work/stocks-remediation-20260915/merge-main-tests.log` e
`merge-main-verification.json`. A CI remota valida também build e instalação
do wheel fora do checkout nas versões Python 3.11–3.14; seu resultado fica na PR.

O [recibo Stocks anterior](STOCKS_QA_20260915.json) continua ligado à candidata
`f6c86d3`: seus 794 testes e respostas reais não são resultados desta composição.
A conciliação não executa nova inferência e não certifica raciocínio livre,
compreensão geral, hipóteses ou retorno econômico. A consulta técnica segura
continua sendo leitura literal com abstenção de interpretação.

## Entrega e retomada

O commit de conciliação é publicado na branch da
[PR #3](https://github.com/leonardosovienski/cain/pull/3), que registra o estado
de integração em main e os checks remotos. Integração Git não instala a candidata
na máquina. O checkout desta tarefa permanece em
`C:/CAIN/work/stocks-remediation-20260915/checkout`; outros checkouts locais
podem permanecer em versões diferentes e não foram restaurados ou limpos.
