# Inspeção dos geradores v0.3

A decisão provisória é manter `qwen2.5:3b` como modelo padrão. `qwen3.5:4b`
melhorou alguns casos de preservação de fatos, brevidade e referência à fonte,
mas apresentou regressões de fidelidade e classificação. Esta inspeção não
estabelece um vencedor científico nem elimina as falhas observadas no modelo atual.

Foram lidas as respostas dos oito casos de desenvolvimento e dos seis casos
holdout, com uma geração por caso e modelo: 28 chamadas reais no total, 14 por
modelo. Todas terminaram com `done_reason=stop`, sem erro ou truncamento reportado.
Os 14 pares têm hashes de entrada idênticos entre modelos; gabaritos e checks não
integram a entrada enviada ao modelo. O comparativo chama o gerador diretamente,
com prompt/contexto fixos e schema nos casos JSON; não exercita o runtime, a memória
adaptável, a busca nem o roteador completo do Cain.

As duas execuções registram Ollama `0.33.3`, temperatura `0`, seed `42`,
`think=false`, `num_ctx=8192`, `num_predict=768`, timeout de 120 s e guarda de
entrada de 6500 bytes. A guarda não é um tokenizador, e strings iguais podem ter
contagens de tokens diferentes entre modelos. Os digests completos dos modelos,
iguais nas duas execuções, as opções observadas e os hashes do código/dataset estão
nos arquivos de configuração de
[desenvolvimento](../../evaluation/results/quality-v03-dev-01/config.json)
e [holdout](../../evaluation/results/quality-v03-holdout-01/config.json).

## Evidência textual

| Conjunto e caso | Observação comparativa |
|---|---|
| Dev — `dev-preference-steps` | Qwen2.5 produz 175 palavras, acima do limite de 70, e sugere mover o original apesar do pedido de preservação. Qwen3.5 produz 39 palavras, três passos e mantém o original sem alterações. |
| Dev — `dev-summary-negation` | Qwen2.5 omite que Lume ainda não foi aprovado. Qwen3.5 preserva essa restrição, a revisão na sexta-feira e o lançamento indefinido. |
| Dev — `dev-preference-paragraph` | Ambos extrapolam o único fato fornecido sobre SQLite. Qwen2.5 acrescenta manipulação/transferência e omite “local”; Qwen3.5 preserva “local”, mas acrescenta backups, portabilidade e ausência de servidores externos. |
| Dev — `dev-preference-english` | Qwen2.5 traduz fielmente a comparação entre resultado observado e esperado. Qwen3.5 acrescenta contexto estatístico e diferença significativa, ausentes da entrada. |
| Holdout — `holdout-preference-paragraph-en` | Qwen2.5 permanece fiel à preservação e legibilidade da cópia. Qwen3.5 acrescenta garantia de integridade e ausência de corrupção/erros, que a simples legibilidade não demonstra. |
| Holdout — `holdout-abstain-date` | Ambos se abstêm de inventar uma data. Qwen2.5 omite a referência solicitada; Qwen3.5 cita `[S7]` corretamente. |
| Holdout — `holdout-route-quoted` | O pedido principal é resumir uma frase que menciona código e pesquisa. Qwen2.5 retorna `resumo`; Qwen3.5 retorna `clarificar`, rótulo incorreto apesar de JSON válido. |

Nos demais casos, ambos preservam os fatos da reunião e da versão restrita a
testes internos, abstêm-se corretamente sobre o preço ausente com `[S1]`,
classificam o pedido explícito de código e o pedido ambíguo corretamente. As funções
`soma(a, b)` e `eh_par(n)` retornam, respectivamente, `a + b` e `n % 2 == 0`:
corretas para os pedidos simples por inspeção textual, sem execução. Qwen3.5 usa
cercas Markdown; Qwen2.5 apresenta o código diretamente.

As respostas completas estão disponíveis em
[pares dev](../../evaluation/results/quality-v03-dev-01/responses.md) e
[pares holdout](../../evaluation/results/quality-v03-holdout-01/responses.md).

## Medidas e limites

As durações abaixo foram recalculadas a partir de `wall_seconds` nos registros
[dev](../../evaluation/results/quality-v03-dev-01/raw.jsonl) e
[holdout](../../evaluation/results/quality-v03-holdout-01/raw.jsonl).

| Modelo | Dev: total / mediana | Holdout: total / mediana |
|---|---:|---:|
| Qwen2.5:3b | 7,085 s / 0,257 s | 3,593 s / 0,200 s |
| Qwen3.5:4b | 40,626 s / 0,676 s | 7,982 s / 0,610 s |

As durações incluem carregamento e variam com o tamanho da resposta. O primeiro
pedido dev do Qwen3.5 levou 35,654 s, com 22,493 s de carregamento informado pelo
backend. A execução sequencial, sem repetição nem controle de aquecimento, não
constitui benchmark geral de velocidade.

Os checks automáticos têm limites concretos. A regex `verific` rejeita o correto
“Verifique” do Qwen3.5; outra regra não reconhece a abstenção “Ausência de
informação na fonte mencionada” do Qwen2.5. A referência `[S7]` ausente nessa mesma
resposta é uma falha real e separada. Já as extrapolações em inglês passam nas
regras de palavras. Sintaxe/assinatura Python não provam semântica ou segurança;
JSON válido não prova rótulo correto; presença de um identificador de fonte não
prova sustentação de cada afirmação. As
[métricas dev](../../evaluation/results/quality-v03-dev-01/metrics.json) e
[holdout](../../evaluation/results/quality-v03-holdout-01/metrics.json) mantêm
qualidade humana e vencedor geral como `null`.

A leitura foi uma inspeção assistida por IA, identificada e não cega, sem notas
humanas independentes. O conjunto é pequeno e não demonstra validade científica
ou confiabilidade geral. O holdout foi inspecionado depois da geração, sem mudar
seus casos, regras ou parâmetros nesta revisão. Se orientar ajustes futuros,
deverá ser tratado como conjunto já conhecido, com nova confirmação separada.
Erros do gerador direto também não equivalem automaticamente a erros do sistema:
o Cain acrescenta referências de fontes recuperadas e possui regras próprias de
roteamento.
