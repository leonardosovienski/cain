# CAIN — testes individuais em 11/09/2026

**Veredito: a suíte automatizada passou; ainda há falhas de interpretação nas respostas dos modelos. As correções candidatas não foram promovidas à instalação principal.**

Avaliação técnica de desenvolvimento. Não é validação científica ou econômica.

## Suíte e escopo

- Python 3.12.14 e 3.13.12: **430 testes aprovados e um skip Windows em cada versão**. Ruff aprovado; wheel instalada e verificada offline fora do checkout. Dois avisos de depreciação do TestClient foram registrados. O skip foi a criação de link simbólico, sem privilégio disponível neste Windows.
- Dois geradores locais: Qwen3.5:0.8b e Qwen2.5:3b. Qwen3-embedding:0.6b foi testado em vetores e busca. Ollama observado: 0.34.0.
- 19 relatos admitidos: 15 Crypto, um Stocks, três Brasileirão. Duas rodadas × dois geradores = **76 análises individuais**. Isso cobre os relatos importados, não todas as hipóteses existentes nos repositórios produtores.
- **35 verificações funcionais aprovadas por gerador**, em seis processos distintos: persistência/correção de preferências, isolamento, roteamento por regras e busca da fonte sintética. Guardar/injetar uma preferência não prova que a resposta a obedece.
- Quatro casos estruturais aprovados por rodada de validação: JSON aninhado, Unicode, false e chave JSON duplicada. A extração é determinística, não inferência do modelo. Quatro respostas de prosa PT/EN por gerador tiveram citações resolvidas; interpretação não certificada.
- Streaming terminou corretamente nos dois geradores; visão identificou a imagem vermelha no Qwen3.5. Visão não se aplica ao Qwen2.5; geração de texto não se aplica ao modelo de embeddings.
- Embeddings: vetores normalizados de 1024 dimensões, cache idêntico, par semântico PT/EN acima do par não relacionado e identidade preservada na busca dos 19 relatos. São verificações pontuais, não benchmark geral de recuperação.
- Fontes ausentes causaram abstenção sem chamada ao modelo. Na correção candidata, os seis fluxos de três coleções × dois geradores completaram suas seis etapas e mantiveram as etapas ao retomar. Na rodada original, um dos seis fluxos falhou e sua falha foi preservada.

## O que foi corrigido e por que não foi promovido

Correções candidatas: foco na chave exata da hipótese em JSON, caminhos separados para estado e nome do experimento, recusa de JSON ambíguo, extração literal de tabelas com várias colunas e controles explícitos de geração no harness funcional. Foram acrescentados cinco testes de regressão.

As misturas de IDs detectadas em H1–H9 caíram de sete para zero. Porém, a reprodução literal de estados passou de 8 para 9 casos no Qwen3.5 e **caiu de 7 para 3** no Qwen2.5. As respostas ainda apresentam afirmações sem suporte. **Isso não permite promover a alteração como uma melhoria geral de qualidade.**

O código testado está no commit `dc114fc` (SHA completo no JSON de recibos). Os prompts candidatos usam `addressable-review/3` e os fluxos, `research-workflow/5`. Fluxos pendentes antigos exigem uma nova execução explícita com o novo protocolo; não são continuados silenciosamente com outros prompts.

Não houve instalação da candidata, push, merge, release ou nova CI remota. Foram mantidos commits locais revisáveis. A condição anterior para publicar, de estar tudo bom, não foi satisfeita pela qualidade dos modelos. A instalação principal continua na 0.4.7 anterior, com seu código, configuração, política e registros preservados.

## Geradores: diagnóstico antes e depois da correção

| Rodada | Modelo | Respostas | Citações exatas | Estado literal mencionado | Mistura de IDs H1–H9 | Fluxos completos |
|---|---|---:|---:|---:|---:|---:|
| baseline | qwen3.5:0.8b | 19/19 | 19/19 | 8/19 | 5 | 2/3 |
| baseline | qwen2.5:3b | 19/19 | 19/19 | 7/19 | 2 | 3/3 |
| corrected | qwen3.5:0.8b | 19/19 | 19/19 | 9/19 | 0 | 3/3 |
| corrected | qwen2.5:3b | 19/19 | 19/19 | 3/19 | 0 | 3/3 |

Os estados acima reproduzem os campos recebidos, sem completá-los: CLAIM-CR-H6 já chegou com um campo de estado parcial. A análise individual inclui sua evidência anexada; isso não constitui correção do produtor.

Citação exata verifica o trecho e seus offsets. Menção literal e outros IDs são diagnósticos automáticos; nenhum deles certifica a interpretação.

## Cada relato na rodada corrigida

| Coleção / identidade | Estado original | Qwen3.5: literal / citação / outro ID | Qwen2.5: literal / citação / outro ID |
|---|---|---|---|
| crypto / CLAIM-CR-COSTS | SUPPORTED_UNDER_ASSUMED_COST_MODEL | não / sim / nenhum | não / sim / nenhum |
| crypto / CLAIM-CR-DPL | SUPPORTED | não / sim / nenhum | não / sim / nenhum |
| crypto / CLAIM-CR-H6 | INCONCLUSIVE_DUE_TO_POWER (gate operacional de n>=30 atingido em | não / sim / nenhum | não / sim / nenhum |
| crypto / CLAIM-CR-HMM | REFUTED | não / sim / nenhum | não / sim / nenhum |
| crypto / CLAIM-CR-LLM | REFUTED (H5), INCONCLUSIVE_DUE_TO_POWER (H4) | não / sim / nenhum | não / sim / nenhum |
| crypto / CLAIM-CR-TREND | CLOSED_BY_SCOPE / INCONCLUSIVE — decisão de escopo não é refutação | não / sim / nenhum | não / sim / nenhum |
| crypto / H1 | CLOSED_NO_GO | sim / sim / nenhum | não / sim / nenhum |
| crypto / H2 | CLOSED_NO_GO | sim / sim / nenhum | não / sim / nenhum |
| crypto / H3 | CLOSED_NO_GO | sim / sim / nenhum | sim / sim / nenhum |
| crypto / H4 | CLOSED_INSUFFICIENT_SAMPLE | sim / sim / nenhum | não / sim / nenhum |
| crypto / H5 | CLOSED_NO_GO | sim / sim / nenhum | sim / sim / nenhum |
| crypto / H6 | CLOSED_INSUFFICIENT_SAMPLE | sim / sim / nenhum | não / sim / nenhum |
| crypto / H7 | REGISTERED_NOT_ACTIVATED | sim / sim / nenhum | não / sim / nenhum |
| crypto / H8 | REGISTERED_NOT_ACTIVATED | sim / sim / nenhum | não / sim / nenhum |
| crypto / H9 | CLOSED_INSUFFICIENT_SAMPLE | sim / sim / nenhum | não / sim / nenhum |
| stocks / Retorno líquido pessoal e operação real | Não aptos: custos, eventos, cenário pessoal e observações insuficientes | não / sim / nenhum | não / sim / nenhum |
| brasileirao / CLAIM-BR-MARKET-001 | BLOCKED_PENDING_PIT_FEATURES | não / sim / nenhum | não / sim / nenhum |
| brasileirao / CLAIM-BR-MARKET-002 | BLOCKED_PENDING_PIT_FEATURES | não / sim / nenhum | sim / sim / nenhum |
| brasileirao / CLAIM-BR-MARKET-003 | BLOCKED_PENDING_PIT_FEATURES | não / sim / nenhum | não / sim / nenhum |

## Hipóteses funcionais do CAIN

| Verificação | Qwen3.5 | Qwen2.5 |
|---|---|---|
| 01-declare:completed | True | True |
| 01-declare:route | True | True |
| 01-declare:format | True | True |
| 01-declare:llm_generation | True | True |
| 01-declare:context_preference | True | True |
| 02-reopen-code:completed | True | True |
| 02-reopen-code:route | True | True |
| 02-reopen-code:format | True | True |
| 02-reopen-code:llm_generation | True | True |
| 02-reopen-code:context_preference | True | True |
| 03-correct:completed | True | True |
| 03-correct:route | True | True |
| 03-correct:format | True | True |
| 03-correct:llm_generation | True | True |
| 03-correct:context_preference | True | True |
| 04-reopen-summary:completed | True | True |
| 04-reopen-summary:route | True | True |
| 04-reopen-summary:format | True | True |
| 04-reopen-summary:llm_generation | True | True |
| 04-reopen-summary:context_preference | True | True |
| 05-other-user:completed | True | True |
| 05-other-user:route | True | True |
| 05-other-user:format | True | True |
| 05-other-user:llm_generation | True | True |
| 06-search-source:completed | True | True |
| 06-search-source:route | True | True |
| 06-search-source:format | True | True |
| 06-search-source:llm_generation | True | True |
| 06-search-source:context_preference | True | True |
| 02-reopen-code:persisted_before_input | True | True |
| 04-reopen-summary:persisted_before_input | True | True |
| personality_stable | True | True |
| other_user_isolated | True | True |
| search_source_recorded | True | True |
| process_restart | True | True |

Persistência de personalidade mede valores armazenados, não coerência percebida de personalidade. Preferências explícitas e roteamento são verificações mecânicas; satisfação humana e superioridade arquitetural B/C não foram estabelecidas. ADR-0010 permanece Proposto.

## Falhas semânticas observadas

Inspeção do assistente sobre respostas registradas, não avaliação humana cega independente. Exemplos que impedem declarar tudo aprovado:

- Na rodada original, o Qwen3.5 atribuiu também CLOSED_INSUFFICIENT_SAMPLE a H8, cujo estado recebido era REGISTERED_NOT_ACTIVATED.
- Na rodada corrigida, o Qwen3.5 afirmou em CLAIM-CR-DPL que consumidores reais fora do repositório haviam sido testados. A fonte informa que nenhum segundo consumidor real fora do repositório foi confirmado.
- Na rodada corrigida, o Qwen3.5 incluiu CLOSED_NO_GO em H1, mas disse que a fonte não fornecia esse estado literal. Isso mostra por que a métrica de presença textual não certifica a resposta.

## Qualidade dos geradores: oito casos de desenvolvimento por modelo

As 16 gerações terminaram sem erro de transporte ou truncamento. O conjunto holdout não foi executado. Saída gerada com sucesso não equivale a cumprir o pedido.

| Modelo | Caso | Checks que sinalizaram falha |
|---|---|---|
| qwen3.5:0.8b | dev-preference-paragraph | heuristic:required_fact_3 |
| qwen3.5:0.8b | dev-preference-english | heuristic:required_fact_2, heuristic:required_fact_3 |
| qwen3.5:0.8b | dev-code-sum | nenhum |
| qwen3.5:0.8b | dev-route-code | deterministic:route_label_exact |
| qwen3.5:0.8b | dev-preference-steps | nenhum |
| qwen3.5:0.8b | dev-abstain-price | deterministic:required_citations_present |
| qwen3.5:0.8b | dev-summary-meeting | nenhum |
| qwen3.5:0.8b | dev-summary-negation | heuristic:required_fact_1, heuristic:required_fact_2 |
| qwen2.5:3b | dev-preference-paragraph | nenhum |
| qwen2.5:3b | dev-preference-english | nenhum |
| qwen2.5:3b | dev-code-sum | nenhum |
| qwen2.5:3b | dev-route-code | deterministic:route_label_exact |
| qwen2.5:3b | dev-preference-steps | deterministic:word_count_within_limit |
| qwen2.5:3b | dev-abstain-price | nenhum |
| qwen2.5:3b | dev-summary-meeting | nenhum |
| qwen2.5:3b | dev-summary-negation | nenhum |

Os checks heurísticos também têm falsos alarmes: por exemplo, a busca de “local” não aceitou “locais”. Não são notas de qualidade ou prova de sustentação semântica.

Falhas confirmadas pela leitura das respostas:

- Ambos escolheram `busca` em vez de `codigo` no caso de roteamento por JSON. O roteamento por regras do teste funcional passou; são testes diferentes.
- Qwen3.5 respondeu em português quando o caso exigia inglês e omitiu uma citação exigida no caso de preço ausente.
- Qwen2.5 sugeriu **remover o arquivo original**, contrariando a instrução de mantê-lo intacto, e excedeu o limite de palavras. Essa sugestão não foi executada.
- No funcional, Qwen3.5 registrou corretamente a preferência de passos, mas sua resposta disse que usou parágrafo.

Os códigos Python gerados foram inspecionados quanto a sintaxe/assinatura no harness; não foram executados. As evidências não estabelecem um vencedor geral entre os modelos.

## Artefatos e reprodução

Código corrigido: `C:\CAIN\work\individual-model-tests-20260911`, branch `validation/individual-models-20260911`.
Instalação principal: `C:\CAIN\work\research-capabilities-20260911`, versão 0.4.7; não foi substituída por estes testes.
Resultados completos, respostas e bancos isolados: `C:\CAIN\entregas\individual-models-20260911`.
Protocolo: `evaluation/individual-models-20260911.json`. Runner: `tools/verify_individual_models.py`.
Reprodução serial desta rodada: `C:\CAIN\work\individual-validation-20260911\run_remaining.py` (nomes existentes devem ser substituídos por novas saídas; nenhuma sobrescrita/repetição oculta).

Nenhuma pesquisa financeira foi reexecutada. Foram usados apenas os 19 relatos admitidos na cópia do CAIN. As falhas da rodada anterior e os estados originais foram preservados.
