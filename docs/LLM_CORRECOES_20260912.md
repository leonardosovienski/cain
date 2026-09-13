# LLM do CAIN — correções e avaliação de 12/09/2026

A versão 0.4.9 corrige a entrega de contexto recente e simplifica as instruções internas. O modelo padrão passa de qwen3.5:0.8b para qwen3.5:4b, priorizando fidelidade ao texto. Não houve treino nem alteração de pesos. O modelo continua sujeito a erros semânticos.

## Falhas corrigidas no aplicativo

- “Explique melhor” perdia o contexto quando não repetia palavras da conversa anterior. Agora são priorizados os últimos intercâmbios da mesma sessão, usuário e projeto, dentro do orçamento existente.
- Continuações reconhecidas, como “Qual das duas opções custa menos?”, seguem para conversa quando há contexto, sem pedir esclarecimento por falta de intenção.
- Artigos e instruções genéricas como “responda” não tornam uma conversa antiga relevante. Um caso real recuperava “CAIN QA” em uma pergunta posterior sobre relatório; foi adicionada regressão.
- Preferências antigas continuam excluídas dos episódios; a projeção usa o perfil ativo. Dados persistidos e auditoria não foram reescritos.
- O contexto de conversa foi reduzido: instruções longas faziam o modelo reproduzir campos internos e recusar tarefas simples. A projeção mantém personalidade, preferências e limites de bytes.
- A intenção explícita `conversa` percorre o provedor real mesmo para mensagens sociais. Saudações e aritmética automáticas existentes não contam como aprovação da LLM.

## Avaliação semântica real

Recibos completos, prompts, respostas e tempos: `C:/CAIN/work/qa-llm-20260912`. São amostras diagnósticas locais, com revisão manual; não são benchmark independente ou garantia de generalização. Os casos usados para ajustar instruções não são avaliação cega.

Uma bateria direta de 12 casos usou cópia literal, formato, cálculo, ausência de dados, negação, citação, instrução maliciosa em texto citado, contexto, inglês e JSON. Não houve FakeLLM nem respostas determinísticas do CAIN nessa bateria.

| Modelo | Resultado observado |
|---|---|
| qwen3.5:0.8b | 6 casos satisfatórios; inventou história ao copiar VENTO-926, omitiu [S1] e acrescentou fatos ao contexto. |
| qwen2.5:3b | Melhor no teste direto: copiou, preservou [S1] e respondeu ao contexto; houve pequena imprecisão chamando trial R9 de fonte. No CAIN, porém, inverteu repetidamente a proibição do lançamento. Rejeitado como padrão de fidelidade. |
| qwen3.5:4b | Na bateria direta, 11 casos satisfatórios; a citação omitiu [S1]. Melhor preservação de negações. Mais lento, sobretudo com contexto maior. |
| cain-test-smollm3:3b | Triagem interrompida após respostas exporem marcadores de raciocínio e descumprirem o formato; não se declara bateria completa. |

Trocar `/api/generate` por `/api/chat` isoladamente não corrigiu a resposta inventada do 0.8B no teste comparativo.

## Reteste do 4B com o aplicativo corrigido

Em dados isolados, usando o provedor real e contexto da 0.4.9:

| Pedido | Resultado | Tempo |
|---|---|---|
| Responda somente: CAIN QA | Exatamente CAIN QA — passou | 45,26 s |
| Relatório diz lançamento proibido até revisão externa | Respondeu que não autoriza — passou | 23,25 s |
| Copie somente NUVEM-483 | Acrescentou “A sequência solicitada é” — falhou no formato exato | 19,99 s |
| Confirme preços fornecidos de duas pedras | Recusou por não poder confirmar preço de mercado — falhou na tarefa | 36,73 s |
| Qual das duas custa menos? | Identificou topázio a 11 reais, mas acrescentou ressalva de mercado — parcialmente satisfatório | 61,48 s |

O 3B, por contraste, respondeu “o relatório autoriza o lançamento” mesmo após reforço de negações. A escolha do 4B não elimina todos os problemas: ainda há excesso de ressalvas e descumprimento de formato. O 4B não foi treinado nesta rodada.

A máquina tem aproximadamente 8 GB de RAM e a inferência foi em CPU. Com o 4B, a memória livre ficou muito baixa. Uma rodada anterior levou 136 segundos em um pedido; não prometer respostas instantâneas. Nenhum modelo foi apagado ou baixado para esta promoção.

## Verificação de engenharia e instalação

- Suite completa antes dos últimos ajustes de palavras genéricas e ordem do histórico: 629 aprovados, 1 skip de symlink Windows e 2 avisos de depreciação.
- Depois desses ajustes: 64 regressões afetadas aprovadas, incluindo busca, contexto, persistência e continuação. Ruff aprovado.
- Wheel 0.4.9 verificado em ambiente novo, offline, não editável; `pip check` aprovado.
- Código do pacote: cba4b5b0d1c0b3dd7dcbbfbaa2a22a1647ad5a20. Commits posteriores de configuração/documentação não alteram o wheel.
- SHA256 do wheel: `cce177f1e90b54e068dd98b5321299ad2faafce38d244fbb92173842a8b3bc57`.
- Os 61 arquivos do pacote instalado coincidem com fonte e wheel.
- Instalação principal em `C:/CAIN/.venv`, porta 8877; bancos mantidos em `C:/CAIN/dados`.
- Backup consistente dos bancos, configuração e wheel 0.4.8 em `C:/CAIN/work/qa-llm-20260912/promotion-backup`.
- Comparação das linhas preexistentes e integridade SQLite aprovadas. Política, atalhos, configuração local e dependências preservados. No TOML, somente `llm.model` mudou.

CI remota, avaliação humana independente e qualidade semântica geral não foram verificadas nesta rodada. O teste integral anterior de documentos, pesquisa e workflows permanece histórico; não foi repetido integralmente para certificar o novo modelo.

## Reteste na principal e falha restante de continuação

Na porta 8877, a interface iniciou com “oi” no perfil isolado `qa-llm-installed` e comparou corretamente os pacotes fictícios Alfa (19) e Beta (11). A API real preservou a proibição do relatório; a CLI instalada, com banco isolado, retornou exatamente “CAIN QA”. Os metadados registram `qwen3.5:4b` e geração concluída.

**Falhou:** “Explique melhor” na interface pediu o assunto novamente. O histórico persistido estava correto. Foi corrigida sua apresentação para ordem cronológica, com o intercâmbio mais recente ao final. No reteste real com o mesmo histórico, o modelo reconheceu explicitamente os pacotes Alfa e Beta, mas ainda pediu esclarecimento em vez de desenvolver a comparação (57 s). Portanto, entrega de contexto e roteamento estão corrigidos; a qualidade da continuação genérica permanece reprovada. Não apresentar a correção de transporte de memória como correção completa do comportamento da LLM.

Não houve restauração de dados antigos sobre dados atuais. Os perfis QA foram mantidos separados. A janela principal foi devolvida ao usuário leo ao encerrar.

Após a reinstalação do wheel final, a API recebeu a continuação 'Qual das duas opções custa menos?' na sessão da interface. HTTP 200, modelo qwen3.5:4b, 84.70 s. Identificou Beta como mais barato, mas acrescentou pedidos de esclarecimento desnecessários: resultado parcialmente satisfatório. Recibo: `primary-final-context.json`.
