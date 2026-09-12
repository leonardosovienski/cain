# Entrega incremental de evidências — 2026-09-12

## Resultado e alcance

A revisão passou a recuperar campos JSON relevantes depois dos primeiros 32 campos,
valores maiores que o objeto compacto de 150 caracteres e janelas de sentenças em
parágrafos que excedem 2.200 bytes. A seleção continua literal, limitada e separada
ocasionalmente de uma resposta semanticamente correta. Não há aceite global do CAIN.

Base preservada: `0c8814901d3d365a2eec4b0c7386b59f460d349d`, checkout
`C:/CAIN/work/historian-operational-fix-20260912`, limpo na inspeção inicial.
Checkout entregue: `C:/CAIN/work/evidence-selection-20260912`, branch
`fix/evidence-selection-20260912`. A referência final é o HEAD dessa branch local.
O checkout `C:/CAIN/projeto` estava em outra linha (`2e9350c`) e não foi alterado.

O grounding anterior tem exatamente 10.749 bytes e SHA-256
`3db090cfeffefde140c6a387a1968039b00bc752f33b005f8615ebbae760c133`, igual ao módulo
caracterizado no mandato em `9001a33e89387f1d1b095ba303bc8c687d94108d`.
O ZIP, manifesto e executor originais não estavam nos Downloads. Não foi inventada
uma execução desses asserts históricos: foram criadas regressões independentes.
O documento original e o relatório anexo foram preservados sem edição.

## Evidências observadas

- Primeiras regressões na base: **8 falhas, 9 aprovações**. Falhas: G02, posições
  tardias G04/G05 e valor longo G06. G03 é contraprova pareada; não são oito defeitos.
- Contratos G01–G10 passam nas regressões novas, incluindo ordem, Unicode,
  identidade exata, ambiguidade, negação e unidade indivisível acima do orçamento.
- Suíte final Windows/Python: **485 passaram, 1 skip, 2 avisos de depreciação**.
  O skip existente continua não verificado; não equivale a execução Linux.
- Ruff dos arquivos alterados e `git diff --check` aprovados.
- API com double identificado: criar job → advance → review → cards → provider
  recebe o campo relevante após 100 auxiliares. Revogação antes/depois da inferência
  recusa o resultado; teste de paginação comprova consulta da segunda página.
- Modelo real local: duas chamadas comparando apenas seletor anterior/corrigido,
  mesmo prompt `addressable-review/5`, Qwen3.5:0.8b Q8_0, digest
  `f3817196d142eaf72ce79dfebe53dcb20bd21da87ce13e138a8f8e10a866b3a4`.
  Temperatura 0, seed 42, contexto 8192, saída 768, think=false, limite 6500 bytes,
  timeout 240 s. É desenvolvimento conhecido, sem reserva independente.
- **Caso real reprovado semanticamente nas duas condições**: a resposta afirma que
  o recorte informa tamanho da amostra, embora os dois trechos contenham apenas
  estado e trial. As respostas foram idênticas; nenhuma vantagem real foi inferida.
  Literalidade das citações e sucesso HTTP não aprovam essa afirmação.
- Controle simples disponível antes da mudança: relações literais compactas.
  Para os dois campos curtos do caso real, retorna o mesmo conteúdo necessário;
  não há evidência de superioridade do seletor corrigido nesse recorte.

Recibos privados, fontes, prompts, respostas, inventário e bancos de teste estão
somente em `C:/CAIN/work/evidence-selection-receipts-20260912`. Não são arquivos Git.
`baseline.txt`, `suite-final.txt`, `suite-final.xml`, `real-rubric.json`,
`old-selection-sent.json`, `corrected-selection-sent.json` e os dois `*-real.json`
permitem revisar os resultados. A rubrica foi gravada antes de chamar o modelo.
A comparação com fonte foi feita pelo implementador, não por juiz independente.

## Percurso e contratos

Interface `web/app.js` cria `/research/jobs` e avança `/research/jobs/{id}/advance`;
`agent_api.py` chama Workflows → analysis.review → grounding.cards → provider →
validação de IDs, offsets e política → resultado exibido. O prompt é /5 e o
workflow é /7. Workflows históricos permanecem legíveis/canceláveis, mas jobs
pendentes de outra versão não são executados sob o novo contrato.

Historian/Snapshot (`/research/explain`, historian.py) e Bundle têm outros
percursos. Não receberam este seletor. Suas suítes existentes passaram, mas uma
melhoria na revisão não demonstra correção da resposta H4 nessas rotas.

A API mantém limite do pedido, contexto serializado de 5000 bytes e validação da
resposta em 1000 caracteres; prompt antigo de 300 caracteres foi ampliado para o
limite já aceito pelo validador. Nenhum contexto/modelo/timeout foi aumentado.
O provider conserva seu próprio limite conservador de transporte e reserva de
saída. Bytes não são tokens; tokens medidos só aparecem nos recibos do modelo.

A recuperação consulta duas páginas de até 50 registros admitidos para geração;
o diagnóstico informa has_more. Formação: 100 fontes, 1 MB por fonte, 2048 campos
por fonte estruturada e 2048 janelas de prosa por fonte. Seleção: até 8 cards e
2200 bytes, configuráveis para baixo. Decisões têm log limitado a 256 linhas e
contador de linhas omitidas. Fontes/recortes não examinados continuam desconhecidos.
O arquivo inteiro pode precisar ser lido para parsing, sem ser enviado ao modelo.
A projeção do serviço ainda valida/carrega o arquivo de publicações autorizado
antes da paginação: isso não foi transformado em um banco com busca incremental.

Subpedidos são divisão heurística parcial por conjunções/pontuação; disponibilidade
lexical não equivale a suporte semântico. Não resolve taxonomia aberta nem garantia
de cobertura de toda pergunta complexa. Janelas conservam duas sentenças adjacentes
por lado e nunca cortam uma oração por tamanho; dependências discursivas longas
continuam não certificadas. Tabelas longas não receberam expansão nesta alteração.

## Lotes e missões

| Item | Implementado/testado/utilizável no recorte | Limite |
|---|---|---|
| A: seleção/revisão | Correção e regressões, API e salvaguardas testadas | Resposta real continua reprovada; manifesto histórico ausente |
| B: reranking | Não incorporado | Evidência necessária já presente no caso real; reranker não responderia a essa falha |
| B: modelos escolhidos | Inventário local registrado | Qwen3.5-4B, SmolLM3-3B e Qwen3-Reranker não instalados; sem download/serviço novo |
| C: comparação verificável | Procedimento /2 confere campos JSON, controle simples e selecionado | Não valida motivos científicos nem interpretação livre |
| C: retomada | Workflows inspect/search retomados em processos distintos; idempotência testada | Não é um executor genérico nem sandbox de código adversário |
| D: comparação ampliada | Controle simples exercitado | Hermes não instalado/executado; nenhuma superioridade de produto ou novidade científica |
| Reconstruir decisão | Estado/trial literais recuperáveis | Motivo/amostra ausentes não devem ser inventados; síntese falhou |
| Retomar trabalho | Objetivo, pendência, snapshot e passos persistidos | Sessões de processo; não uma avaliação longitudinal humana |
| Comparar/verificar | Dois campos e versões de origem conferidos | Métrica em campos literais, não taxa de afirmações corretas |
| Reutilizar procedimento | Caso, variante e recusa de ponteiro ausente testados | Disponível só no escopo documental definido no procedimento |

## Repetir e abrir

No checkout entregue, usando o ambiente de testes existente:

```powershell
$env:PYTHONPATH='C:\CAIN\work\evidence-selection-20260912\src'
& C:\CAIN\work\independent-review-env-20260911\Scripts\python.exe -m pytest -q
```

A instância isolada foi aberta em `http://127.0.0.1:8879` com `preview_app.py`
do diretório de recibos. Para reiniciar, nesse diretório e com o mesmo PYTHONPATH:

```powershell
& C:\CAIN\work\independent-review-env-20260911\Scripts\python.exe -m uvicorn preview_app:app --host 127.0.0.1 --port 8879
```

Não use os atalhos principais para abrir este candidato. Bancos originais foram
lidos para backup SQLite consistente; somente cópias receberam jobs e histórico.
Nenhuma reinstalação, push, merge, release, grant, fonte produtora ou modelo mudou.
Reversão: parar somente o servidor isolado; a instalação principal já permanece
na versão anterior. Não é necessário restaurar bancos principais.

Próximo passo delimitado: transformar a resposta de estado/trial e ausência de
campos em uma saída verificável do caminho de revisão, com teste real mantendo
fonte e configuração. A falha de síntese documentada impede aceite de produto.

## Percurso visual efetivamente observado

Navegador na instância isolada 8879: criação do job, inspect, search, entities e
support acionados pela interface; etapa support exibida após 27,74 s com modelo
real. O pedido curto solicitava estado e trial; a síntese exibiu estado e omitiu
trial. Portanto essa execução também não passou no critério de cobertura. O job
foi cancelado após 4/6 passos para não deixar testes pendentes; os quatro recibos
foram preservados em `ui-job.json`. Não houve execução de challenge/synthesis
nessa demonstração visual. A comparação controlada anterior enviou payloads,
instruções e schema byte-equivalentes nos dois seletores, confirmado ao finalizar
os recibos. O browser testou a revisão por workflows, não o botão Historian.

Runtime de teste: `C:/CAIN/work/independent-review-env-20260911/Scripts/python.exe`
com importação do `src` deste checkout. A .venv principal continua associada ao
wheel da entrega full-operational-audit anterior; `runtime.json` registra paths,
versão Python, hashes do candidato e do grounding instalado. Nenhum wheel novo
foi instalado. Os testes importam fonte candidata, não simulam teste de wheel.
