# Reteste real da LLM — 12/09/2026 (horário local)

CAIN 0.4.9, modelo qwen3.5:4b, instalação principal na porta 8877. Código e configuração não foram alterados. Testes por API real, com usuários QA separados; comparação e continuações compartilham uma conversa nova. Nenhum teste de interface ou CLI foi repetido nesta rodada.

**Resultado: 4 de 6 testes com inferência aprovados; 2 falharam.** A saudação automática também passou, mas não conta como teste da LLM.

| Caso | Resultado | Tempo |
|---|---|---|
| Saudação automática | Passou | 0.12 s |
| Comparação inicial Alfa/Beta | Passou | 95.25 s |
| Explique melhor | Falhou | 69.97 s |
| Qual das duas opções custa menos? | Passou | 64.70 s |
| Cópia exata NUVEM-483 | Falhou | 14.92 s |
| Cópia exata LAGO-752 | Passou | 14.17 s |
| Preservar proibição do lançamento | Passou | 18.14 s |

## Respostas observadas

### Saudação automática

Oi! Como posso ajudar você?

### Comparação inicial Alfa/Beta

No exemplo fictício apresentado, o pacote **Beta** custa menos (R$ 11,00), pois é inferior ao preço do pacote Alfa (R$ 19,00).

### Explique melhor

Para explicar melhor, preciso saber **sobre qual tópico** você gostaria de obter uma explicação detalhada.

Como o histórico anterior tratava apenas de um exemplo fictício sobre preços de pacotes (Alfa e Beta), não tenho informações suficientes para expandir qualquer outro assunto. Por favor, especifique o tema ou forneça os dados necessários para que eu possa prosseguir.

### Qual das duas opções custa menos?

No exemplo fictício apresentado anteriormente, o pacote **Beta** custa menos (R$ 11,00), pois é inferior ao preço do pacote Alfa (R$ 19,00).

### Cópia exata NUVEM-483

A sequência solicitada é: NUVEM-483.

### Cópia exata LAGO-752

LAGO-752

### Preservar proibição do lançamento

Não, o relatório não autoriza o lançamento porque ele permanece proibido até a revisão externa.

## Conclusão

A falha em “Explique melhor” foi reproduzida: o modelo reconheceu o assunto anterior, mas pediu esclarecimento desnecessário. A cópia exata continua inconsistente; NUVEM-483 recebeu texto extra, enquanto LAGO-752 foi copiado corretamente. A continuação explícita sobre as duas opções e a preservação da negação passaram.

Latência das inferências: 14,17 a 95,25 segundos. Amostra diagnóstica pequena, com casos de regressão já conhecidos; não representa certificação geral.

Integridade e preservação de linhas preexistentes verificadas; somente dados sintéticos de QA foram acrescentados. Recibos completos: C:/CAIN/work/qa-llm-retest-20260913. Código verificado: cba4b5b0d1c0b3dd7dcbbfbaa2a22a1647ad5a20; HEAD antes deste registro: 57702e1742b4c688ad7f0bbe01bd5143ee587391.
