# CAIN: teste geral e correções — 12/09/2026

Execução local na branch `validation/cain-system-20260912`, derivada de
`082aee2f12db0e74e8067fcdcf438160cbccd5ad`, em
`C:\CAIN\work\cain-system-20260912`.
Evidências: `C:\CAIN\work\cain-system-receipts-20260912`.

## Problemas reproduzidos e corrigidos

1. O caminho geral do Historian recusava documentos grandes mesmo quando a
   justificativa relevante cabia no contexto. Agora utiliza o seletor existente
   de trechos quando o documento integral excede 6.000 bytes. Expõe a cobertura,
   aceita somente citações efetivamente enviadas ao modelo e se abstém sem
   inferência quando nenhum trecho cabe. Fontes pequenas mantêm o caminho integral.
2. Uma revogação durante a resolução das citações podia passar pela última
   conferência. A autorização é verificada antes da inferência e depois da
   resolução, bloqueando a resposta e atualizando os fatos disponíveis.
3. Em inferência real, o resumo de uma frase transformou “produção continua não
   autorizada” em “continua em produção sem autorização externa”. Uma tentativa
   de reforçar o prompt não resolveu e foi revertida. Pedidos explícitos
   `Resuma:`, `Resuma texto:` ou `Resuma o texto:` com texto de até 240 caracteres,
   sem preferência de inglês, agora preservam literalmente o conteúdo e mostram
   o aviso “Texto já conciso; preservado literalmente”. Isso protege este caminho
   delimitado; não certifica a fidelidade de resumos longos ou outras formulações.

Nove regressões foram acrescentadas: três identidades distintas em fontes
grandes, revogação tardia, abstenção por orçamento, rejeição de citação fora do
trecho selecionado e três frases com negação, condição ou data. Os quatro primeiros
casos do Historian falharam na base antes da correção (`new-baseline.txt`).
Fixtures existentes que precisavam exercitar inferência foram reformuladas,
mantendo suas verificações de contexto, preferências e quantidade de chamadas.
O teste do CLI passou a verificar explicitamente o novo modo literal.

## Validação e limites

| Área | Evidência desta execução |
| --- | --- |
| Suíte completa | Base: 566 passaram, 1 ignorado. Pacote final: **575 passaram, 1 ignorado, 2 avisos, 207,08 segundos**; `verified-final.txt` e `verified-final.xml`. |
| Qualidade estática | `ruff check .` e `git diff --check` sem erros. |
| API com modelos reais | 17 verificações passaram em `real-api-literal/verification.json`: preferências, escopos, reabertura, documentos, busca, embeddings reais, hashes, histórico e feedback. |
| MCP real por stdio | Inicialização, inventário, consulta sintética e rejeição de alteração de escopo; `mcp.json`. |
| Interface | Preview isolado em `http://127.0.0.1:8884`; resumo observado preservando “a publicação não foi autorizada”. |
| Historian com fonte grande | 0,8B produziu citação inválida e foi bloqueado (`UNSUPPORTED_QUOTE`). 4B retornou literalmente a justificativa correta em um caso sintético. |
| Visão e streaming reais | Imagem sintética vermelha: 0,8B respondeu “Roxo”; 4B respondeu “Vermelho”. Transporte e encerramento funcionaram; a qualidade do 0,8B falhou nesse caso. |
| Código gerado | Função simples recebida na API real; não foi executada como prova de correção. |
| Bundle, políticas, arquivos, workflows, CLI e demais módulos | Cobertura da suíte automatizada existente; não equivale a testar cada combinação possível na interface ou com inferência real. |

Os testes reais usam dados sintéticos. Os recibos das tentativas que falharam
foram preservados (`real-api`, `real-api-corrected`, `general-historian-real.json`,
`vision-stream.json`). Uma resposta correta do 4B não constitui benchmark amplo
nem justificativa para promovê-lo; houve pressão de memória e lentidão nesta
máquina. O modelo padrão não foi alterado.

O teste dependente de Linux permanece ignorado no Windows; não houve execução
Linux nesta rodada. Os avisos de depreciação FastAPI/Starlette são registrados
no log final. Qualidade generativa geral, visão e desempenho permanecem sujeitos
a avaliação mais ampla. Nenhum teste comprova validade científica ou econômica.

O ZIP, o manifesto e o probe originais mencionados no mandato continuam ausentes;
por isso não se afirma reprodução exata desse pacote histórico. Os trabalhos de
Bundle e comparações de modelos da rodada anterior permanecem na ancestralidade
da branch e em seus relatórios, sem reclassificar limitações como concluídas.

## Reprodução e entrega

O wheel final fica em `dist-verified`, com instalação isolada em
`verified-runtime`, ambos na pasta de evidências. A suíte usa o Python de
`C:\CAIN\work\supply-final-20260912\venv\Scripts\python.exe`,
`PYTHONPATH` apontando para `verified-runtime`, e
`python -m pytest tests -q -o pythonpath= --junitxml=<recibos>\verified-final.xml`.
O lint usa o ambiente `C:\CAIN\work\independent-review-env-20260911`.
O ensaio real adicional está em `extended.py`; a API real usa
`scripts/verify-api-v03.py`. O preview usa `preview_app.py`, `preview.toml` e
bases próprias na pasta de evidências.

Não houve push, merge na branch principal, instalação no CAIN principal,
alteração de grants de produtores ou promoção de modelo. A entrega é uma
candidata local corrigida e testada. O serviço principal da porta 8877 não foi
substituído. A cópia entregue ao usuário registra o HEAD final e o hash do wheel.
