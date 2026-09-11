# Auditoria completa do Cain — 0.4.2

## Resultado e alcance

Base examinada: `c09d818dbbd4a4dfea3843a01ec9b8e90af60289`, branch
`local/l0-historian`. A suíte inicial passou com 350 testes e um skip. A revisão
acrescentou 14 regressões: a suíte final passou com **364 testes e um skip**.
Há dois avisos de depreciação nas dependências HTTP de teste, não falhas do produto.

Foram revisados composição, configuração, CLI, API, inicializador Windows, workspace,
identidade/memória, persistência/auditoria, busca lexical/híbrida/URL, embeddings,
transporte de geração, pesquisa L0, interface, avaliação, distribuição e CI.
Os testes reais usam Windows/Python 3.12.14; inferência de modelo continua não verificada.
O exportador independente do Crypto passou novamente nos dez testes delimitados com
Python 3.13.14. Não foram executados pipelines, backtests, holdouts ou suítes científicas
dos predictors. A revisão integral do Cain não é uma certificação desses outros projetos.

## Bugs corrigidos

| Prioridade | Falha reproduzida | Correção e regressão |
|---|---|---|
| P1 | Historian retornava fatos anteriores à revogação se o provider falhasse antes da verificação de permissões no caminho de sucesso | Todas as saídas de falha refazem a consulta com a política atual; timeout após revogação agora devolve zero registros acessíveis |
| P1 | Documento enviado ao workspace podia mudar no disco sem que o catálogo acusasse divergência do hash recebido | Snapshot verifica tamanho, hash e localização controlada; o retriever recebe os próprios bytes verificados em memória, sem uma segunda leitura mutável |
| P2 | Documentos cadastrados com banco relativo quebravam ao reabrir de outro diretório | Caminho do banco é resolvido e documentos são localizados por IDs da aplicação; registros legados com paths relativos continuam resolvíveis |
| P2 | Configurações inválidas eram aceitas: paths textual virava uma lista de caracteres, limites/tipos inválidos chegavam ao runtime | Seções, campos, listas, booleanos, números finitos, reserva de contexto e URL são validados na carga e nos overrides CLI; seis casos inicialmente falharam e depois passaram |
| P2 | CLI/API preparavam busca/embeddings mesmo para uma operação de código ou resumo | Recuperação é inicializada somente quando usada; composição do retriever é compartilhada; busca indisponível ainda falha explicitamente, sem fallback |
| P2 | Transporte do LLM lia resposta HTTP sem teto e aceitava redirects automáticos | Leitura limitada a 4 MiB + sentinela, rejeição do excesso e de redirects; testes de transporte sem modelo real |

Os dez testes iniciais da auditoria falharam na implementação anterior. O caso de
revogação com timeout foi reproduzido separadamente. Os demais controles novos validam
paridade CLI/API, limite de resposta e recusa de redirect. As falhas de reprodução
ficaram preservadas nos XMLs; não são contabilizadas como sucessos.

Um teste preexistente esperava 503 ao resumir texto quando uma fonte de busca estivesse
ausente. Essa expectativa codificava o acoplamento corrigido. Ele agora exige resumo
200 **e** busca 503, mantendo a recusa quando a operação realmente depende da fonte.

## Arquitetura: problemas observados que permanecem

### P1 — conclusão do orquestrador e persistência da UI têm fronteiras distintas

Em banco descartável, a injeção de falha em `WorkspaceStore.record_turn` produziu HTTP
503 e zero turnos na UI, enquanto o DecisionLog já continha `mediated` e `completed`.
`completed` representa o orquestrador, não uma resposta entregue e recuperável na UI.
Isso pode levar o usuário a repetir um pedido já processado.

Caminho: `api.py:run → runtime.run → workspace.record_turn`. Os commits do histórico,
identidade e DecisionLog não formam uma transação de aplicação única. Não reescrevi essa
fronteira silenciosamente: ela exige definir quais efeitos devem sobreviver à falha e
preservar a auditoria append-only. Prioridade sugerida: recibo idempotente de requisição
e resultado durável recuperável, com estados separados de processamento e entrega.
Aceitação: falhar antes/depois de cada commit, reabrir o processo e recuperar o mesmo
resultado sem regeneração ou duplicação de preferências.

### P2 — leitura de perfil reconstrói índice global sem necessidade

Uma requisição a `/profile/new-profile` percorreu **500 documentos sintéticos de outro
perfil** na reconstrução do índice, embora a operação só precisasse da identidade.
Tempo observado nesse ensaio: aproximadamente 0,111 s; não é benchmark de capacidade.
Nenhum conteúdo de outro perfil foi exposto na resposta. O problema demonstrado é
trabalho desnecessário, não vazamento observado.

Caminho: `runtime_for_profile → build_cain → memory.rebuild_from → iter_documents`.
Separar a composição de inspeção de perfil da composição conversacional e carregar
memória por usuário/projeto reduziria custo e retenção incidental. Aceitação: inspeção
de perfil sem leitura de sinais; busca conversacional preservando isolamento e resultados.

## Melhorias priorizadas, sem alegação de bug reproduzido

1. **Recuperação completa do workspace:** SQLite e `knowledge/` são objetos distintos.
   Um backup somente do banco não contém documentos enviados. Criar manifesto consistente
   de banco + arquivos, verificar hashes e restaurar ambos em outro diretório. A pesquisa
   L0 já preserva seus objetos dentro do próprio banco, mas o workspace legado não.
2. **Escala e limites:** o L0 revalida publicações e projeções por consulta. É uma escolha
   simples e verificável para o piloto, mas custa proporcionalmente ao acervo. Medir
   latência/memória antes de propor cache; qualquer otimização precisa invalidar por
   conteúdo e política atual, sem reintroduzir falsa ausência ou acesso revogado.
3. **Prontidão operacional:** distinguir configuração, processo vivo, disponibilidade de
   provider/embedding, fonte legível e inferência executada. Ampliar `doctor` e evitar
   reutilizar uma instância na mesma porta apenas pelo identificador de serviço quando
   configuração ou banco forem diferentes. O cenário de duas instâncias não foi
   reproduzido nesta rodada.
4. **Distribuição e dependências:** CI agora inclui wheel não editável instalado em venv
   limpo fora do checkout. O script foi executado localmente, offline com o wheel do
   contrato. A execução desse novo gate no GitHub deve ser conferida separadamente; aprovação local não equivale a CI remota.
   Acrescentar Windows à matriz e um conjunto de versões travadas para reprodução;
   conservar uma faixa de compatibilidade testada separadamente.
5. **Semântica e tempo:** citação válida e trecho exato não provam que a síntese está
   sustentada. Manter explicação como proposta, construir avaliação humana e testar
   orçamento total de tempo, além do timeout de socket. Não há evidência de ganho
   comparativo ou de inferência real nesta auditoria.

## Verificações da entrega

- Suíte completa: 364 aprovados, 1 skip de privilégio de symlink no Windows.
- Revisão final direcionada: 34 aprovados; lint completo e sintaxe JavaScript aprovados.
- Exportador Crypto: 10 aprovados, sem ciência nova.
- Wheel 0.4.2: instalação não editável offline em venv limpo, fora do checkout;
  recursos web/contrato, CLI, workspace e `pip check` verificados.
- Aplicação instalada 0.4.2: consulta H6 e abertura da evidência conferidas na interface real em `http://127.0.0.1:8877`; importação, reimportação, rebuild, backup/restauração, CLI e API passaram no smoke instalado.
- Os testes HTTP usam TestClient e servidores locais delimitados, não inferência real.
- As observações de arquitetura usam dados sintéticos descartáveis e falha injetada.

Os XMLs, observações estruturadas, patch e wheel acompanham o relatório local da
auditoria. Limites observados foram mantidos explícitos; a aprovação da suíte não
significa ausência de bugs, recuperação física certificada ou validação econômica.
