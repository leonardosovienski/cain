# Comparação funcional de geradores v0.3

O módulo `cain.evaluation.quality` compara geradores diretamente por `OllamaLLM`, sem passar
pelo runtime, roteador ou recuperação adaptável do Cain. O mesmo caso fornece exatamente
as mesmas strings de prompt e contexto e, nas tarefas estruturadas, o mesmo schema JSON
a todos os modelos. Isso controla o insumo textual; não garante tokenização idêntica nem
mede o efeito da arquitetura de memória do Cain.

## Contrato e execução

É necessário integrar o adaptador com:

```python
OllamaLLM(..., think=False)  # think é omitido quando --think default
provider.generate(prompt: str, context: str = "") -> str
provider.generate_json(prompt: str, context: str, schema: dict) -> str
provider.last_metadata: dict  # observação do backend, quando disponível
```

`generate_json` deve devolver a string bruta. O consumidor verifica parse, schema e rótulo.
O comparador não usa retrieval ou gabaritos para construir o pedido. Os arquivos não contêm
nenhuma execução de modelo nem download realizado durante a implementação.

Com os modelos já disponíveis e Ollama acessível, o operador pode executar, na raiz do projeto:

```powershell
python -m cain.evaluation.quality --models qwen2.5:3b qwen3.5:4b --output evaluation/results --run-id quality-v03-dev-01 --split dev --think false
```

Depois de congelar a escolha e os parâmetros, avaliar holdout com outro ID:

```powershell
python -m cain.evaluation.quality --models qwen2.5:3b qwen3.5:4b --output evaluation/results --run-id quality-v03-holdout-01 --split holdout --think false
```

`--split all` é o padrão e executa todos os casos, adequado para uma comparação exploratória.
Se o holdout influenciar novos ajustes, ele deixa de ser confirmação intocada. Preserve esse
histórico e prepare outro conjunto antes de afirmar generalização. `--think default` omite o
parâmetro e preserva o padrão do adaptador/modelo; isso pode resultar em políticas de raciocínio
diferentes. As opções realmente expostas pelo adaptador ficam em `adapters_observed`.

Também existem `--temperature`, `--seed`, `--timeout`, `--num-ctx`, `--num-predict`,
`--max-input-bytes`, `--base-url` e `--dataset`. Não há opção de provedor fake na CLI.

## Dataset predeterminado

`evaluation/scenarios/quality-v03.json` contém 14 casos: 8 de desenvolvimento e 6 de holdout.
Abrange resumo factual com negação/restrições, formato/extensão/idioma declarados, abstenção
quando o fato falta na fonte, funções Python simples e classificação de intenção em JSON.
Os rótulos `split`, IDs, categorias e `checks` são metadados do avaliador; nunca são enviados
ao modelo. Os fatos e as referências fornecidos como entrada não são gabarito oculto: são
o material que a resposta deve respeitar. O conjunto e seu hash são copiados antes de gerar.

## O que é medido

- Determinístico: JSON estrito sem chaves duplicadas; schema limitado à estrutura usada no
  fixture; rótulo exato de intenção; pertença dos marcadores à lista de fontes fornecidas;
  contagem de palavras por regex; linhas numeradas; estrutura por linhas em branco; parse
  de Python e nomes de função/parâmetros.
- Heurístico: presença de fatos esperados e ausência de padrões proibidos. Expressões
  regulares podem aceitar uma contradição ou rejeitar uma paráfrase correta. Os rótulos
  `heuristic` permanecem nos registros e nas métricas.
- Não medido: qualidade humana, adequação linguística completa, correção semântica geral,
  fidelidade de cada afirmação à fonte, segurança ou execução correta do código gerado.

O código Python produzido é somente analisado com `ast.parse`; não é executado. Uma função
que retorna o valor errado pode passar em sintaxe e assinatura. Não existe nota geral nem
vencedor automático. `quality_winner` e `human_quality.value` permanecem nulos.

## Rastreabilidade, falhas e limites

Cada diretório de resultado é exclusivo; repetir o ID é recusado. A execução é serial por
modelo, com a mesma ordem de casos randomizada por seed. Não há inferência paralela, retry,
fallback ou instalação. Todas as tentativas são preservadas, inclusive falhas de inicialização,
erros e respostas que o backend declarou truncadas. Um erro não exclui casos posteriores.
Se o adaptador levantar `LLMTruncated`, o `partial_response` e a metadata são preservados
e a tentativa é classificada como truncada, sem retry; a resposta parcial não é promovida
a uma resposta completa nem some em uma contagem genérica de erros.

`config.json` registra configuração, ordem, dataset/hash, commit/estado da árvore, hashes do
código, versão observada do backend e dados/digest dos modelos presentes em `/api/tags`.
Campos não observados não são inventados. `raw.jsonl` preserva entrada efetiva, seu hash,
resposta, erro, tempo e cópia da metadata reportada. `metrics.json` separa dev/holdout, contagens
de status e checks. Respostas truncadas não entram nas taxas de respostas completas, mas
permanecem nas contagens e na evidência bruta. `responses.md` permite inspeção identificada
das respostas de cada modelo; não é avaliação cega ou nota humana.

Tempo de parede inclui carga do modelo e outros custos. Contagens reportadas são observações
do backend, sem inferência de tokens por caracteres. A guarda de entrada em bytes não é um
tokenizador, e a mesma entrada textual pode ter números diferentes de tokens entre modelos.
Ausência de `done_reason` deixa truncamento desconhecido; não é assumida conclusão íntegra.

Testes usam `provider_factory` injetado com `provider="injected-test"`; tentar rotular essa
execução como Ollama real é rejeitado. O comparador é instrumento de engenharia, não coleta
formal do protocolo de identidade. O resultado não demonstra validade científica ou eficácia
da arquitetura do Cain.
