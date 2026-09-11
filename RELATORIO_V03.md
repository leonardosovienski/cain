# Cain v0.3 — entrega funcional

> Registro histórico da entrega indicada neste documento. Para estado e caminhos atuais, consulte [Continuidade](CONTINUIDADE.md).

Concluída em 7/9/2026, horário de Brasília. Os artefatos usam timestamps UTC.

Abra [ABRIR_CAIN.cmd](ABRIR_CAIN.cmd) para usar a interface local. O código continua
no [repositório privado](https://github.com/leonardosovienski/cain).

## Entregue

A interface permite criar projetos e conversas, importar documentos de texto,
consultar fontes, inspecionar e remover preferências, definir validade e avaliar
respostas por motivo. Histórico e feedback ficam no SQLite local. As mensagens
exibem o texto preservado de cada fonte, seu hash e os offsets usados na síntese.

Preferências seguem a precedência resposta, conversa, projeto e usuário. A
preferência temporária é endereçada pelo identificador da resposta; ao acabar
seu contexto, deixa de valer nos próximos pedidos. Remoção e expiração revelam
o valor inferior. Perguntas diretas sobre preferências consultam o estado real,
sem pedir que o LLM invente o próprio perfil.

A busca híbrida combina cobertura lexical com embeddings de `qwen3-embedding:0.6b`.
O cache é derivado, separado da identidade, e inclui modelo, digest e hash do texto.
Arquivos, candidatos e histórico são selecionados pelo projeto antes do ranking.
Identificadores literais como `ERR-401` recebem prioridade sem confundir `ERR-4012`.

Foram corrigidas a criação concorrente de perfis, a identidade dos turnos no
histórico e consultas de sessão que criavam conversas vazias. A API valida
Host/Origin; o frontend trata respostas e documentos como texto, sem executar HTML.

## Modelo de resposta: manter Qwen2.5 3B

Os modelos Qwen2.5 3B e Qwen3.5 4B foram executados localmente nos mesmos 14 casos:
oito de desenvolvimento e seis de confirmação separados. Foram 28 chamadas reais,
sem erros ou truncamento reportado. Parâmetros permaneceram congelados entre as
rodadas: `think=false`, temperatura 0, seed 42, contexto 8192 e saída máxima 768.

O Qwen3.5 preservou melhor algumas negações, foi mais breve no pedido de três
passos e citou corretamente uma fonte ausente na resposta do Qwen2.5. Porém
acrescentou informação não fornecida em dois casos em inglês e errou um rótulo de
roteamento que o Qwen2.5 acertou. Ambos extrapolaram um fato sobre SQLite.

A decisão é manter o padrão atual e deixar o Qwen3.5 disponível para experimentos.
Não houve vencedor científico. A [inspeção identificada dos modelos](docs/research/inspecao-modelos-v03.md)
explica os casos, falsos positivos/negativos das regras e links para todas as respostas.

## Verificação realizada

- **281 testes automatizados passaram** em Python 3.12, incluindo contratos, persistência, concorrência, escopos, busca, API e avaliação. Dois avisos de depreciação vêm das dependências de TestClient.
- Ruff, checagem de sintaxe JavaScript e `git diff --check` passaram.
- O pacote Python wheel foi construído; os três arquivos da interface fazem parte do pacote.
- A interface foi servida em `127.0.0.1:8000`, com retorno HTTP 200, e o inicializador foi executado. Não houve inspeção visual nem teste de interação no navegador. A integração WebMCP opcional também não foi exercitada em navegador compatível.
- A [verificação final da API com modelos reais](evaluation/results/api-v03-02/verification.json) passou em 14 verificações mecânicas: precedência, exceção temporária, nova conversa, evidências reproduzíveis, feedback, IDs e reabertura. Foram quatro gerações e uma resposta autoritativa de perfil, com três preferências e dados sintéticos em banco separado. A execução anterior em `api-v03-01` permanece preservada.
- O [diagnóstico de recuperação](evaluation/results/retrieval-v03-01/summary.md) executou seis consultas sobre seis fontes sintéticas. Nas cinco com fonte relevante, o primeiro resultado acertou 2/5 na busca lexical e 4/5 na híbrida; entre os três primeiros, 2/5 e 5/5. A híbrida errou o primeiro lugar em uma paráfrase. No caso sem fonte, ambas recuperaram um trecho irrelevante; isso foi registrado separadamente, sem interpretar recuperação como resposta ou alucinação.

A primeira consulta híbrida, incluindo indexação, levou cerca de 21 s; as seguintes variaram
com cache e carregamento. Esses tempos não são um benchmark controlado. Pesos,
limiar e prioridade do ranking continuam heurísticos. O diagnóstico pequeno não
demonstra desempenho geral nem autoriza ajustar parâmetros ao próprio gabarito.

Para repetir verificações em novas pastas, com Ollama ligado:

```powershell
python scripts/verify-api-v03.py --output evaluation/results/api-v03-replay
python scripts/verify-hybrid-v03.py --execute --output evaluation/results/retrieval-v03-replay
python -m cain.evaluation.quality --models qwen2.5:3b qwen3.5:4b --output evaluation/results --run-id quality-v03-replay --split all --think false
```

As pastas de evidência existentes não são sobrescritas. O conjunto de confirmação
agora é conhecido; qualquer ajuste motivado por ele exige nova confirmação separada.

## Limites e próximos passos

A preferência enviada ao modelo não garante obediência na resposta. Na primeira
verificação real, o estado registrou passos/tópicos corretamente, mas algumas
respostas não seguiram esse formato. Essa diferença entre memória correta e
qualidade da geração continua exigindo avaliação.

A guarda de entrada é conservadora e medida em bytes, não por tokenizador exato.
O contexto derivado de identidade/histórico tem limite de 2.000 bytes UTF-8;
o JSON de evidências é ajustado ao espaço restante, incluindo rótulos e escapes,
sem cortar o pedido ou as preferências essenciais. Hashes e offsets correspondem
ao trecho realmente enviado. Texto grande demais para os campos essenciais é
recusado explicitamente. Arquivos aceitos são `.txt`, `.md` e `.rst`,
até 256 KiB e 200 documentos por projeto; PDF/OCR não estão implementados.
A interface mostra até 100 conversas por projeto e as 100 interações mais recentes
da conversa; registros anteriores continuam armazenados. Não há streaming.

O painel mostra registros atuais por escopo e valores usados em cada resposta;
a auditoria completa permanece no banco. Feedback é armazenado para revisão,
sem aprendizagem automática. A API é local, sem autenticação, e o isolamento lógico
por usuário/projeto não substitui contas de acesso em uma implantação pública.

Faltam validação de uso com pessoas, avaliação independente de fidelidade, casos
maiores e representativos de recuperação e calibração do orçamento de contexto.
Memória procedural, grafos, execução de código e ajuste de pesos ficam para outras
etapas. O caminho acadêmico da UFPR e os ADRs científicos continuam provisórios.
Os cinco anexos originais e os resultados das versões anteriores foram preservados.

