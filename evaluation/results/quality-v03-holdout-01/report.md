# Comparação de geradores quality-v03-holdout-01

Provedor: `ollama`. 6 casos por modelo. Mesmos prompt, contexto e schema por caso; nenhum gabarito foi enviado. O runtime e a recuperação do Cain não participam desta comparação.

| Modelo | Completas | Erros | Truncadas reportadas |
|---|---:|---:|---:|
| qwen2.5:3b | 6 | 0 | 0 |
| qwen3.5:4b | 6 | 0 | 0 |

Os resultados individuais estão em raw.jsonl. metrics.json separa desenvolvimento e holdout e mostra cada check sem compor uma nota geral. Resultados truncados/erros não entram nas taxas das respostas completas, mas permanecem nos denominadores de status e nos registros brutos.

Presença/ausência de fatos por expressão regular é heurística e pode produzir falsos positivos ou negativos. Identificadores de fonte corretos não provam sustentação das afirmações. Validade de JSON, rótulo exato, contagem/formato textual e sintaxe/assinatura de Python são verificações limitadas ao que explicitamente medem. Nenhum código gerado foi executado.

Qualidade humana não foi medida. Não há vencedor automático e não foi realizada coleta científica formal. Idioma apropriado requer revisão; palavras esperadas não substituem essa avaliação. Tempos incluem carga do modelo; não são um benchmark controlado de velocidade.

A divisão holdout deve permanecer intocada durante ajustes. Se ela influenciar ajustes de prompt/modelo, registre a reutilização e trate seus resultados como exploratórios. Seeds e opções são registradas, sem promessa de determinismo. A guarda em bytes não é tokenização.

[Abrir respostas pareadas para inspeção](responses.md)
