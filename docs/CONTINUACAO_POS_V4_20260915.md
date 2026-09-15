# Continuação após V4 — 15/09/2026

## Identidade e escopo

- Checkout: `C:/CAIN/work/readiness-main-20260914`, branch `fix/readiness-main-20260914`.
- Checkpoint local V4: `ad21220`; base anterior `8d4297a575ec1231ad7ec909faa8be0ea795e546`.
- Alterações desta continuação permanecem locais, posteriores ao checkpoint.
- Evidências: `C:/CAIN/work/readiness-continuation-20260915`.
- Candidata V6 preservada: wheel 0.4.12, SHA-256 `3c8eef21262dc2c4039d4330ee92846b7d4255d6317e8d156b373461e6f7244e`.
- Instalação QA: `installed-qa-v6`; armazenamento: `qa-v6/runtime`, ambos na raiz de evidências.
- A versão nominal não identifica o pacote: 70 arquivos foram comparados entre fonte, wheel e instalação. Dependências e modelos permanecem nas versões da V4.
- Corpus QA: 95 fontes nativas, 249 ocorrências; um documento hostil sintético adicional tem identidade e coleção QA próprias.
- Nenhum push, merge, release, experimento de produtor ou implantação principal foi autorizado ou realizado.

## Mudanças

A V5 falhou no navegador durante a classificação da pergunta de estoque. A V6 limita a justificativa estruturada do classificador a seis códigos finitos; mantém as rotas, modelo e parâmetros. O diagnóstico da mesma pergunta com o novo classificador distinguiu 18 iniciais de 26 atuais, mas não substitui confirmação no navegador. A falha V5 foi preservada em `ui-v5-result.json`.


A memória seleciona declarações relevantes antes dos distratores recentes, preserva ordem de registro e escopo de usuário/projeto e mantém IDs técnicos no armazenamento de auditoria. Recuperação factual usa declarações do usuário; respostas anteriores do modelo são incluídas quando necessárias para continuar ou revisar sua redação. Isso evita reutilizar uma resposta anterior errada como fato. Não há migração de banco nem novo sistema de conhecimento.

A continuação preserva o assunto, separa total e custo unitário e explicita o denominador quando se pede porcentagem. Não há gabaritos dos casos nem números dos exercícios embutidos no produto.

A seleção científica expande listas explícitas de IDs, registra ambiguidades de sufixos, reserva evidências por identidade e mantém cabeçalhos, offsets, revisões e lacunas. Resultados relatados e definições numéricas pedidas têm prioridade sobre parágrafos procedimentais. IDs nomeados apenas como restrição são distinguidos dos assuntos pedidos. O limite de 1.000 caracteres permanece; respostas inválidas não são truncadas nem reparadas para receber PASS.

O importador existente recebe observações JSONL com revisão, status e relógio nativos. As duas observações H17 permanecem separadas. Isso não transforma observação inconclusiva em P&L executável nem associa protocolos por semelhança de nomes.

## Retificações da entrega anterior

- As nove saídas reais anteriores de H4 contêm `v2-dpl-gemini-h7`. Nenhuma contém `H4v2-dpl-gemini-h7`: a concatenação era do relatório, preservado sem edição. Evidência: `h4-literal-id-audit.json`.
- M07 corresponde ao isolamento entre usuários; M08, entre projetos; M12, à falha explícita do backend. Precedência de preferências e orçamento continuam como controles adicionais.
- As 64 entradas são 44 identidades H documentadas, cinco famílias AR/BR e 15 claims. As 51 linhas de ledgers nativos permanecem em outro denominador. Nenhuma dessas somas demonstra independência científica.
- As 71 referências candidatas e os 231 arquivos externos ao inventário original receberam classificação e proveniência. Relação literal não equivale a identidade científica; ambiguidades restantes bloqueiam a alegação afetada.

## Validação

Os 44 episódios gerais da V6 terminaram: 35 PASS no recorte e nove falhas (três restrições verbais, três aprofundamentos numéricos e três não numéricos). M02 e M03 passaram nas três repetições; o navegador também distinguiu os valores inicial e atual. Os workflows científicos V6 não foram iniciados: a rodada parou nessa fronteira para diagnosticar e corrigir M04 antes de outro congelamento. Não há aprovação geral.

O aprofundamento numérico calculou corretamente os valores, mas chamou 16,7% de quase um terço. A ablação de uma única instrução adicional do aplicativo produziu os cálculos completos sem essa interpretação falsa. No caso não numérico, a premissa do usuário estava presente, mas a expressão `Explique` não ativava a inclusão da resposta anterior: o aplicativo pedia para explicar uma resposta que omitia. O controle com a resposta anterior real restaurada deixou de recusar e explicou a escolha. Esses diagnósticos não são confirmação de um produto já corrigido. Os recibos, desenhos e falhas V6 permanecem em `readiness-continuation-20260915`.

Os testes de contexto foram atualizados para a representação com papéis separados e sem UUID no texto do modelo. O teste de reconstrução inclui o relógio que a projeção agora preserva. Um teste que exigia a expressão antiga `exclusive explanation` passou a conferir as instruções equivalentes contra causas inventadas e tradução de rótulos indefinidos; o resultado anterior da suíte permanece nos recibos. Essas verificações de engenharia não certificam a interpretação da LLM.

Engenharia V6: 821 testes aprovados, um pulado, dois avisos; lint aprovado. Fonte, wheel e instalação não editável coincidem nos 70 arquivos. Não houve alteração do produto após esse congelamento.
