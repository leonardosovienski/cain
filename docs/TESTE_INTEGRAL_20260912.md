# Teste integral de uso do CAIN — 12/09/2026

Rodada iniciada em 12/09 no fuso America/Sao_Paulo, com conclusão após meia-noite UTC.
Checkout: `C:/CAIN/projeto`, main inicialmente `c449390756752117cfe813e83547e415591bd5bb`, igual ao remoto após fetch.
A fonte inicial, o pacote 0.4.7 instalado e os hashes registrados pelo processo 20532 coincidiam.
`pip check` e integridade dos bancos estavam aprovados.

## Falhas encontradas e correções

1. **Conversa tratada como pesquisa:** na interface 8877, depois de buscar um documento sintético,
   “Quanto é 2 + 2?” retornou o histórico dessa busca. A seleção LLM só dispunha de busca, código e resumo.
   A versão 0.4.8 registra conversa como capacidade própria, disponível também por intenção explícita na API e CLI.
2. **Histórico irrelevante usado como citação:** artigos e palavras de comando bastavam para recuperar uma conversa antiga.
   A busca agora exige interseção de termos relevantes antes de admitir um hit de histórico.
3. **Cálculo com extrapolação do modelo:** o primeiro candidato respondeu 4, mas inventou cenários adicionais incorretos.
   Cálculos simples reconhecidos usam AST restrita e frações exatas, sem eval, chamadas, nomes ou inferência.
   Há limites de tamanho, quantidade de nós e magnitude; divisão por zero e operações não suportadas são recusadas.
4. **Interação social com pressuposição indevida:** o modelo interpretou “Tudo bem?” como afirmação do estado do usuário.
   Cumprimentos sociais curtos e agradecimentos recebem resposta local, sem essa inferência.

As demais conversas continuam usando o modelo local configurado. Não houve troca de modelo, pesos ou política.
Não se adicionou execução de código gerado nem pesquisa externa automática.

## Matriz de verificação

| Área | Resultado e evidência |
|---|---|
| Interface principal 8877 | “oi” → “Oi! Como posso ajudar você?”, perfil QA separado |
| Projetos e documentos | Projeto QA criado; texto sintético salvo; busca híbrida retornou JADE731 e preservou “não está autorizada” |
| Citações de documentos | Detalhe S1 abriu; trecho, SHA-256 e offsets 0–119 corretos; verificação programática adicional na API |
| Memória e conversas | Preferência de tópicos no projeto; consulta de preferências e nova conversa herdaram o escopo correto |
| Conversa livre final | Inferência e persistência funcionaram; o pedido de uma única frase não foi respeitado pelo modelo, registrado como falha de aderência |
| Memória pela API isolada | Criação/remoção por escopo, precedência projeto/usuário, retorno ao padrão e isolamento entre usuários aprovados |
| API de documentos e histórico | Deduplicação, extensão inválida, acesso por outro usuário, feedback e repetição do run sem duplicar turno aprovados |
| Pesquisa e Historian | H4 em cópia do acervo: estado e trial com fonte; motivo/amostra explicitamente não localizados; dossiê e busca aprovados |
| Bundle | Consulta real de metadados; importação, autorização, migrações, artefatos e linhagem cobertos pela suíte sintética |
| Workflows | Fluxo completo H4: 6/6 etapas, crítica e síntese geradas; reabertura pela UI aprovada; API verificou checkpoints, trace e cancelamento |
| CLI instalada | Ajuda, doctor, saudação e query H4 aprovados; comandos mutáveis usaram bancos isolados |
| Segurança e erros da API | Validação 422, Origin 403 e Host inválido 400 aprovados; restauração/falhas induzidas cobertas em dados temporários |
| Streaming de texto | Transporte terminou com evento done; **falhou a aderência semântica** ao pedido “Responda somente: CAIN QA” |
| Visão e qualidade geral | Não houve nova avaliação real de imagens nem certificação da interpretação livre; testes técnicos não atestam qualidade geral do modelo |

O laboratório gerou uma descrição inventada de empresa em vez do texto solicitado. Esse resultado foi preservado como
limitação do modelo; não foi contado como aprovação semântica nem ocultado por uma resposta simulada.
Sem alterar o modelo/configuração do usuário, esta rodada não resolve a confiabilidade geral da geração livre.

## Baterias e artefatos

- Baseline: 606 passed, 1 skipped, 2 avisos de depreciação.
- Candidato intermediário em wheel estável: 623 passed, 1 skipped, 2 avisos.
- Fonte final: **624 passed, 1 skipped, 2 warnings**, 216,50 s. Regressões finais focadas: 18 passed.
- Regressões novas: conversa, cálculo, histórico irrelevante, API, limites aritméticos e entradas executáveis recusadas.
- Lint Ruff aprovado; wheel validado em venv novo, offline, não editável e fora do checkout.
- Um ensaio intermediário teve `ModuleNotFoundError: cain.research` porque o ambiente de teste estava sendo reinstalado
  enquanto um subprocesso iniciava. A execução foi invalidada, o grupo de 10 testes passou novamente e a bateria foi
  repetida sem reinstalação concorrente. Não se atribuiu essa falha ao produto.
- O skip de Windows é o ensaio de symlink sem privilégio disponível. Os avisos são de Starlette/httpx e AnyIO.

## Dados, configuração e reprodução

Recibos privados, logs e scripts: `C:/CAIN/work/qa-full-20260912`.
Interface isolada usada: porta 8891, bancos copiados para `isolated`, política copiada para `backup`.
Perfil sintético adicionado na principal: `qa-cain-20260912`; não reutilizar como perfil pessoal.
Backup SQLite consistente inicial em `backup`; backup de promoção com bancos, documentos e pacote anterior em `promotion-backup`.
Nenhum banco, resposta real de pesquisa ou configuração privada foi incluído neste commit.
Os dados existentes são conferidos por comparação de linhas e integridade; configurações por hash.

## Promoção e reteste principal

Código: `92b6428cb26064ed9032b0a93ccae64da7b06c3d`. Wheel 0.4.8:
`ae5d6e658b8c8690cacbd5e760938eb9aa0f10b2992b52ef56dd18a89b02542d`.
Os 61 arquivos instalados foram comparados com o wheel e a fonte, sem diferenças.
Processo principal reiniciado pelo launcher padrão: PID observado 24896, loopback 8877, health 0.4.8.
O reteste da pergunta original na mesma conversa retornou `2 + 2 = 4.` sem a citação irrelevante.
Saudação, resposta social, memória de projeto, busca híbrida, hash da citação, Historian H4 e atalho CLI passaram.
Inferência livre funcionou, mas a aderência de formato segue limitada como registrado acima.
`preservation-final.json` confirmou integridade dos bancos, nenhuma linha preexistente ausente/alterada fora do QA,
configurações idênticas e nenhuma mudança de dependência além do próprio CAIN.
O histórico da resposta errada foi preservado; a correção vale para novos pedidos.

Comandos de desenvolvimento em ambiente separado:

```powershell
python -m pytest -q
python -m ruff check .
python -m pip wheel --no-deps --wheel-dir dist .
python tools/verify_wheel.py --wheel dist/cain_research-0.4.8-py3-none-any.whl
```

Testes técnicos não validam conclusões científicas, econômicas ou a qualidade de qualquer resposta arbitrária.
