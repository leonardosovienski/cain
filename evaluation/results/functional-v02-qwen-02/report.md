# Demonstração funcional functional-v02-qwen-02

Provedor: `ollama`. Etapas registradas: 6/6. Verificações mecânicas: passaram. Esta execução não é resultado científico nem avaliação humana da qualidade.

Commit observado: `4b2ebd3a10683bfb639b87c03c41065244d058e6`; árvore modificada: `True`. Digest do modelo observado: `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.

| Verificação | Resultado |
|---|---|
| 01-declare:completed | passou |
| 01-declare:route | passou |
| 01-declare:format | passou |
| 01-declare:llm_generation | passou |
| 01-declare:context_preference | passou |
| 02-reopen-code:completed | passou |
| 02-reopen-code:route | passou |
| 02-reopen-code:format | passou |
| 02-reopen-code:llm_generation | passou |
| 02-reopen-code:context_preference | passou |
| 03-correct:completed | passou |
| 03-correct:route | passou |
| 03-correct:format | passou |
| 03-correct:llm_generation | passou |
| 03-correct:context_preference | passou |
| 04-reopen-summary:completed | passou |
| 04-reopen-summary:route | passou |
| 04-reopen-summary:format | passou |
| 04-reopen-summary:llm_generation | passou |
| 04-reopen-summary:context_preference | passou |
| 05-other-user:completed | passou |
| 05-other-user:route | passou |
| 05-other-user:format | passou |
| 05-other-user:llm_generation | passou |
| 06-search-source:completed | passou |
| 06-search-source:route | passou |
| 06-search-source:format | passou |
| 06-search-source:llm_generation | passou |
| 06-search-source:context_preference | passou |
| 02-reopen-code:persisted_before_input | passou |
| 04-reopen-summary:persisted_before_input | passou |
| personality_stable | passou |
| other_user_isolated | passou |
| search_source_recorded | passou |
| process_restart | passou |

## Respostas observadas

### 01-declare

Pedido: Prefiro respostas em passos. Confirme brevemente essa preferência.

Agente: `resumo`; estado: `completed`.

Entendi. Você prefere que as respostas sejam dadas em passos. Isso foi confirmado.

### 02-reopen-code

Pedido: Escreva código Python para uma função soma(a, b) que retorne a soma dos dois argumentos. Explique brevemente, considerando minhas preferências já declaradas.

Agente: `codigo`; estado: `completed`.

Com base nas suas preferências declaradas, vamos escrever a função `soma(a, b)` que retorna a soma dos dois argumentos. Como você prefere instruções em passos, vou dividir a tarefa em passos claros e diretos.

Passo 1: Definir a função `soma(a, b)` que recebe dois argumentos `a` e `b`.
Passo 2: Dentro da função, calcular a soma dos dois argumentos `a` e `b` e armazenar o resultado em uma variável chamada `resultado`.
Passo 3: Retornar o valor da variável `resultado`.

Aqui está o código Python correspondente:

```python
def soma(a, b):
    # Passo 2: Calcula a soma dos argumentos
    resultado = a + b
    # Passo 3: Retorna o resultado
    return resultado
```

Esta função `soma(a, b)` irá receber dois argumentos `a` e `b`, calcular a soma deles e retornar o resultado. Você pode chamar essa função passando dois números como argumentos para obter a soma desses números. Por exemplo, `soma(3, 5)` retornará `8`.

Lembre-se de que você pode adaptar essa função para outras operações matemáticas, como subtração, multiplicação ou divisão, apenas alterando a operação dentro da função.

### 03-correct

Pedido: Agora prefiro respostas em parágrafo. Confirme brevemente a mudança.

Agente: `resumo`; estado: `completed`.

Entendido. A partir agora, as respostas serão dadas em formato de parágrafo.

### 04-reopen-summary

Pedido: Resuma somente este texto, considerando minhas preferências já declaradas: O projeto sintético Aurora tem três etapas: planejar, executar e verificar. A etapa de verificação compara o resultado com o requisito.

Agente: `resumo`; estado: `completed`.

O projeto sintético Aurora é composto por três etapas: planejar, executar e verificar. A etapa de verificação compara o resultado obtido com os requisitos estabelecidos.

### 05-other-user

Pedido: Qual formato de resposta eu declarei preferir? Se não houver declaração minha, diga que não sabe.

Agente: `resumo`; estado: `completed`.

Não sei. Você precisa declarar os formatos de resposta que prefere no seu perfil atual.

### 06-search-source

Pedido: Busque no corpus local o código do procedimento Boreal e seu prazo. Responda com a fonte consultada.

Agente: `busca`; estado: `completed`.

Baseado no guia-funcional-cain.txt, o código do procedimento Boreal é BOREAL-731 e o prazo estabelecido no corpus é exatamente 7 dias. Essa informação foi diretamente extraída da fonte fornecida.

Fontes consultadas:
[S1] guia-funcional-cain.txt — guia-funcional-cain.txt

## Interpretação

Os checks comparam preferências persistidas, contexto realmente enviado, roteamento e referência à fonte fornecida. Isso não demonstra que as respostas seguem corretamente o formato, que o código gerado funciona ou que o resumo é fiel; essas saídas estão acima para revisão humana. Nenhum código gerado foi executado. O corpus é sintético, com fonte local identificada. O alvo muda por instrução explícita; isso é correção persistida de preferência, não aprendizagem implícita ou validade de um modelo de personalidade.

A coleta formal A/B/C continua bloqueada por protocolo, tokenização, exposição ao histórico, validade de construto e pré-registro. Os arquivos de execuções anteriores foram preservados. Seed e temperatura são solicitadas ao backend, sem garantia de determinismo.
