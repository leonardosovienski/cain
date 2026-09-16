# Correção da prontidão Stocks — 15/09/2026

A auditoria encontrou apenas um registro Snapshot na coleção Stocks principal,
proveniente de `STOCKS_CURRENT_STATE.md`. Um Bundle adicional continha dois
artefatos `reference_only`: referências não são dados recebidos. A instalação
também não correspondia às correções integradas na main.

## Correções desta revisão

- Campos JSON herdam os rótulos do objeto que os contém e de seus ancestrais.
  Elementos irmãos não compartilham identidade; uma identidade mais específica
  substitui a identidade do ancestral. `hypothesis_id` é reconhecido literalmente.
- Um título que menciona explicitamente a hipótese continua elegível quando
  começa pelo identificador do relatório, como `R5 — resultado da H22`.
- Caminhos de documentos citados não são reinterpretados como hipóteses por
  conterem datas ou números.
- Termos solicitados no conteúdo têm prioridade sobre metadados incidentais.
  Uma pequena lista explícita de termos de campos em português/inglês auxilia
  a busca; não mapeia estados nem inventa equivalências científicas.

Seleção: `identity_balanced_excerpts/11`. Não há alteração de protocolos,
resultados históricos, dados do produtor ou autorização de operação financeira.

## Verificação e limites

Os 78 testes direcionados de seleção, instruções e leitura literal passaram,
com dois avisos de depreciação de dependências. A suíte completa da revisão será
verificada pela CI, em Python 3.11–3.14, incluindo o wheel fora do checkout.
Uma suíte local intermediária foi interrompida para incorporar a correção de
caminhos datados e não conta como validação final.

O catálogo preparado em QA tem 48 fontes e 87 ocorrências com hashes conferidos.
H1–H22 têm trechos recuperáveis, mas isso não prova completude dos insumos de
experimento ou compreensão. O teste do filtro `source_id=H1` não é equivalente
à pergunta sobre H1: o filtro identifica registros, cujos IDs podem incluir
caminho e revisão. A matriz de perguntas sem esse filtro é a referência correta.

O primeiro piloto foi interrompido pelo ambiente sem resposta. A tentativa
seguinte falhou no inventário de um Ollama ainda inicializando. Ambas permanecem
registradas; nenhuma delas é aprovação semântica. Novos resultados de interpretação
devem ser examinados contra os trechos efetivamente enviados.

Evidências locais: `C:/CAIN/work/stocks-study-20260915`. Bancos de QA, políticas,
copias de recuperação e modelos não acompanham este documento público. A atualização
da instalação e a admissão no acervo principal exigem recibos próprios, distintos
do commit de código. Nenhum novo backtest ou resultado econômico é declarado aqui.
