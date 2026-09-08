# Respostas observadas — quality-v03-holdout-01

Comparação identificada para inspeção; não são notas humanas nem avaliação cega.

## holdout-code-even (holdout)

Pedido: Escreva a função eh_par(n), que retorna True se o inteiro n for par e False caso contrário.

### qwen2.5:3b — completed

def eh_par(n):
    return n % 2 == 0

### qwen3.5:4b — completed

```python
def eh_par(n):
    return n % 2 == 0
```

## holdout-preference-paragraph-en (holdout)

Pedido: Explique em inglês, com até 45 palavras: a cópia de segurança preserva uma versão dos arquivos; verificar essa cópia confirma que ela pode ser lida.

### qwen2.5:3b — completed

Backing up preserves files' versions; verifying confirms the backup can be read.

### qwen3.5:4b — completed

A backup copy preserves file versions, and verifying it confirms readability. This process ensures data integrity by checking if the stored files can be accessed without corruption or errors.

## holdout-abstain-date (holdout)

Pedido: Em que dia será a entrega do projeto Maré? Indique a fonte.

### qwen2.5:3b — completed

Ausência de informação na fonte mencionada.

### qwen3.5:4b — completed

Não há informação disponível sobre o dia da entrega do projeto Maré, pois a data da entrega não foi definida.

Referência: [S7] Registro artificial: O projeto Maré está em planejamento. A data da entrega não foi definida.

## holdout-route-quoted (holdout)

Pedido: Resuma este texto: 'Escreva código Python e pesquise na internet' é a frase usada no exemplo de uma documentação.

### qwen2.5:3b — completed

{
  "agent": "resumo"
}

### qwen3.5:4b — completed

{
  "agent": "clarificar"
}

## holdout-summary-release (holdout)

Pedido: Resuma em uma frase: A versão 2.4 do sistema Delta está disponível apenas para testes internos. Não foi liberada para produção. O piloto envolve duas equipes.

### qwen2.5:3b — completed

A versão 2.4 do sistema Delta está disponível apenas para testes internos em duas equipes, não sendo liberada para produção.

### qwen3.5:4b — completed

A versão 2.4 do sistema Delta, destinada a testes internos e não liberada para produção, está sendo pilotada por duas equipes.

## holdout-route-ambiguous (holdout)

Pedido: Pode cuidar disso para mim?

### qwen2.5:3b — completed

{"agent": "clarificar"}

### qwen3.5:4b — completed

{
  "agent": "clarificar"
}
