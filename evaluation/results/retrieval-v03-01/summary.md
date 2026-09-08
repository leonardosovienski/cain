# Verificação sintética de recuperação lexical e híbrida

Seis consultas e seis fontes inventadas, rotuladas antes da execução. Este diagnóstico não mede qualidade geral nem foi separado como holdout.
Não houve geração de respostas, teste de alucinação ou uso de documentos pessoais.

Modelo de embedding: `qwen3-embedding:0.6b`; digest: `ac6da0dfba84a81fdbfbaf330198c33cd77c4cdfc53e8bc50eb581914a15621d`.

| Caso | Tipo | Lexical: primeiro documento | Híbrida: primeiro documento | Lexical ms | Híbrida ms |
|---|---|---|---|---:|---:|
| p01 | paraphrase | nenhum candidato | d01 | 0.14 | 21313.63 |
| p02 | paraphrase | nenhum candidato | d02 | 0.12 | 38.88 |
| p03 | paraphrase | nenhum candidato | d01 | 0.12 | 35.68 |
| i01 | literal_identifier | d04 | d04 | 0.16 | 4641.04 |
| i02 | literal_identifier | d05 | d05 | 0.29 | 34.55 |
| a01 | absence | d06 | d06 | 0.14 | 40.85 |

## Interpretação

Os acertos e MRR em `results.json` consideram apenas as cinco consultas com fonte relevante rotulada. O caso de ausência apenas mostra quais candidatos o retriever devolveu. Recuperar um trecho nessa consulta não significa que o sistema respondeu ao pedido nem que alucinou.

Os valores de score pertencem a algoritmos distintos e não são probabilidades comparáveis. Identificadores exatos têm prioridade no ranking híbrido; o metadado explica essa prioridade.

O cache derivado começa vazio neste diretório. A primeira consulta híbrida inclui o cálculo dos embeddings dos documentos; as seguintes reutilizam esses vetores e calculam apenas novas consultas. A residência prévia do modelo na GPU não foi controlada. As latências são observações desta ordem de execução, sem conclusão geral de desempenho ou comparação justa de estados frios/quentes.

`dataset.json` preserva textos e rótulos; `source-manifest.json` preserva arquivos/hashes; `cases/` preserva rankings, offsets, trechos, configuração do modelo e erros. `embedding-calls.json` registra chamadas ao provider, não pensamentos nem respostas de LLM.
