# Busca híbrida v0.3

Este módulo acrescenta similaridade por embeddings à busca lexical. O runtime escolhe explicitamente o modo e fornece apenas os arquivos autorizados para o projeto. O módulo não descobre diretórios, não baixa modelos e não substitui uma falha de embeddings por busca lexical.

## Composição

```python
from cain.search import HybridDocumentRetriever, LocalDocumentRetriever, OllamaEmbedding

# Modo lexical permanece independente do servidor de modelos.
lexical = LocalDocumentRetriever(paths=project_source_paths)

# O runtime consulta a identidade do modelo e fornece seu digest real.
embedding = OllamaEmbedding(
    model="qwen3-embedding:0.6b",
    model_digest=resolved_model_digest,
    base_url="http://127.0.0.1:11434",
    timeout=30,
)
hybrid = HybridDocumentRetriever(
    paths=project_source_paths,
    embedding=embedding,
    cache_path=derived_embedding_cache_path,
)
results = hybrid.search("Como lembrar configurações entre sessões?", k=3)
```

`SearchProvider.search(query, k=3) -> list[SearchResult]` continua sendo o contrato de recuperação. `AutoRetriever` aceita qualquer um dos modos como sua fonte local; sua política de URLs explícitas permanece separada.

`OllamaEmbedding` requer `model_digest` não vazio. Esse valor deve corresponder ao modelo efetivamente servido. A API `/api/embed` retorna nome e vetores, não o digest dos pesos: o runtime deve atualizar a identidade quando substituir o modelo. Não há descoberta automática, download ou garantia de correspondência do digest apenas por este adaptador.

O `EmbeddingProvider` injetável expõe `model`, `model_digest` e `embed(texts)`. Vetores precisam ter dimensão comum, componentes numéricos finitos e norma positiva; o módulo normaliza em L2. `dimensions` pode ser configurado em `OllamaEmbedding`; na ausência dele, a primeira dimensão observada passa a ser obrigatória nas chamadas seguintes.

## Ranking e limites

1. Recarregar somente as fontes explicitamente configuradas, em UTF-8, com extensões `.md`, `.txt` e `.rst`. Uma pasta explicitamente configurada inclui suas fontes textuais, com proteção contra links que escapem dela.
2. Dividir o texto em trechos de até 1.500 caracteres, com avanço de 1.200. A busca lexical mantém seu snapshot de construção; a híbrida atualiza o snapshot a cada busca.
3. Gerar ou consultar embeddings do texto integral de cada trecho. Apenas a consulta recebe a instrução de recuperação, em inglês, configurável por `query_instruction`; documentos não recebem essa instrução.
4. Combinar cobertura lexical e cosseno positivo: `0,45 * cobertura + 0,55 * max(0, cosseno)`. Os pesos são normalizados se configurados de outra forma; ambos devem ser positivos.
5. Priorizar primeiro a quantidade de identificadores exatos da consulta encontrados no trecho. São tokens com sublinhado ou números de pelo menos três caracteres, como `ERR-401`; o limite de palavra evita confundir `ERR-401` com `ERR-4012`. Isso protege códigos mesmo quando um vizinho semântico recebe similaridade maior.
6. Sem cobertura lexical nem identificador exato, exigir cosseno de pelo menos `0,35`. Desempatar por fonte, início do trecho e identificador do trecho.

Os pesos, a prioridade de identificadores e o limiar são heurísticas do protótipo, não probabilidades calibradas. Resultados ordenados por identificador exato podem ter `score` numérico menor que os seguintes. O metadado `exact_identifier_matches` explica essa prioridade.

Limites padrão: 200 arquivos, 262.144 bytes por arquivo, 1.000 trechos, 4.096 caracteres por consulta híbrida. No adaptador: 8.192 caracteres por entrada, lotes de no máximo 32 entradas, timeout de 30 segundos por chamada e resposta HTTP de no máximo 4 MiB. Limites excedidos falham explicitamente; o pedido usa `truncate: false`. O limite em caracteres é uma barreira operacional e não estima tokens. A primeira indexação pode exigir várias chamadas sequenciais.

## Cache derivado

`SQLiteEmbeddingCache(provider, cache_path)` guarda somente vetores e hashes, usando como chave o nome do modelo, digest, dimensão configurada e SHA-256 do texto exato enviado ao embedding. A instrução da consulta faz parte desse texto e, portanto, da chave.

Repetir um texto reutiliza seu vetor, inclusive entre instâncias. Editar um trecho gera cache miss apenas para o texto alterado; trechos idênticos podem ser reutilizados mesmo que o hash do documento mude. Mudar modelo, digest ou dimensão configurada cria outro namespace. Entradas antigas permanecem dispensáveis e não alteram a recuperação: o conjunto candidato vem exclusivamente das fontes atualmente configuradas. Cache corrompido ou vetores incompatíveis causam erro explícito. Conexões SQLite são fechadas a cada operação.

O cache não é uma fonte de identidade nem uma autorização para acessar documentos. Pode ser apagado e reconstruído; não deve conter informações autoritativas do perfil.

## Evidência reproduzível e interface

`SearchResult(source, title, text, score=0.0)` mantém compatibilidade posicional. Acrescenta `chunk_id`, `document_hash`, `start_offset`, `end_offset` e `metadata`, todos opcionais.

Para arquivo local, `document_hash` é SHA-256 dos bytes completos, incluindo BOM e quebras de linha. O texto é decodificado com `utf-8-sig`, preservando as quebras de linha; offsets são índices de caracteres Unicode desse texto decodificado, com fim exclusivo. Para corpus em memória, o hash usa o texto codificado em UTF-8. URLs usam hash do texto extraído, identificado por `document_hash_basis`; não se trata de hash da resposta HTTP bruta.

O identificador do trecho combina fonte, hash do documento e offsets. A evidência persistida em `message.metadata["retrieval_sources"]` contém:

- `citation` e `source`, preservando os campos anteriores;
- `title`, `text` e `excerpt` com o trecho efetivamente enviado à síntese;
- `document_hash`, `chunk_id` e `excerpt_hash`;
- `start_offset` e `end_offset` do trecho efetivamente incluído, `chunk_end_offset` antes do corte;
- `excerpt_truncated`, `score` e metadados do ranking/modelo.

A interface deve mostrar o trecho salvo dessa resposta. Se o arquivo tiver mudado, o hash diferente sinaliza outra versão; não se deve substituir a evidência histórica pelo texto atual. Fontes legadas sem offsets recebem hash e identificador derivados do texto disponível, mantendo offsets nulos.

O orçamento compartilhado de evidências continua em 2.400 caracteres. Arquivos/URLs têm prioridade sobre histórico; cortes e omissões continuam registrados. Hashes e metadados extras ficam disponíveis à aplicação, sem aumentar a carga de evidências enviada ao modelo. A aplicação acrescenta as referências, e marcadores bibliográficos inventados pelo modelo continuam sendo rejeitados.

## Isolamento e identidade

O histórico de busca exige correspondência de `user_id` e `project_id`. Projeto `None` significa apenas histórico legado/global (chave ausente ou nula); não inclui histórico de projetos nomeados. Um projeto nomeado não incorpora automaticamente o histórico global. O agente verifica os campos novamente mesmo após aplicar filtros no índice.

Entradas da decisão atual e memórias de declarações de preferências continuam excluídas. Texto recuperado é evidência não confiável: instruções de arquivos não modificam o perfil nem substituem suas preferências canônicas. Selecionar os arquivos e inserir o `project_id` correto na mensagem são responsabilidades do runtime.

## Verificação e limites conhecidos

Os testes usam vetores injetados e HTTP simulado: paráfrase sem interseção lexical, identificadores exatos, desempate, edição de arquivo, invalidação por modelo, lotes, falhas externas, cache inválido, limites, isolamento e reprodução do trecho cortado. Esses testes verificam o mecanismo; não medem qualidade semântica, latência ou VRAM do Qwen3-Embedding nesta máquina. Nenhum modelo foi baixado ou executado para esta implementação.

Não há índice ANN, reranker, crawler, recuperação de documentos por embedding fora do projeto, aprendizado a partir das fontes ou migração automática de cache. A comparação da qualidade da busca real fica para avaliação posterior com casos definidos.

Fontes primárias consultadas em 7/9/2026: [API de embeddings Ollama](https://docs.ollama.com/api/embed) e [card Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B). O card documenta embeddings de até 1.024 dimensões, instrução na consulta e normalização; suas métricas publicadas não foram reproduzidas aqui.

### Execução integrada posterior

A integração foi verificada com o embedding real em seis consultas sintéticas.
Nas cinco consultas com fonte relevante, a busca híbrida encontrou a fonte em
primeiro lugar em 4/5 e entre os três primeiros em 5/5; a lexical obteve 2/5 nos dois
critérios. Uma paráfrase recebeu primeiro lugar incorreto e ambas recuperaram um
trecho irrelevante no caso sem fonte. Veja o [diagnóstico completo](../../evaluation/results/retrieval-v03-01/summary.md).
Isso complementa os testes com vetores injetados descritos acima; não valida
qualidade geral nem transforma o ranking em probabilidade calibrada.


### Orçamento integrado da geração

Além do teto de 2.400 caracteres de trechos, SearchAgent usa o orçamento de entrada
informado pelo adaptador Ollama: o menor entre `max_input_bytes` e
`num_ctx - num_predict - 256`, tratado conservadoramente como bytes. Reserva o
pedido, o contexto de identidade e as instruções fixas; ajusta somente o JSON
derivado de evidências ao espaço restante. A medição inclui UTF-8, escapes,
rótulos e flags. Trechos e rótulos podem ser abreviados, e fontes finais podem ser
omitidas, preservando a ordem. Hash do trecho, offsets, flags e contadores refletem
o material efetivamente enviado. O pedido e as preferências essenciais nunca são
cortados para ocultar um excesso de entrada. Isso não substitui tokenização exata.
