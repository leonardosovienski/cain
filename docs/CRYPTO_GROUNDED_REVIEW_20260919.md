# Revisão de respostas fundamentadas — 19/09/2026

Esta mudança incorpora somente a parte reutilizável da campanha isolada de QA
com evidências Cripto. Bancos, fontes do produtor, respostas brutas, caminhos
locais, launchers e resultados científicos permanecem fora do repositório.

## Problemas corrigidos antes da publicação

- A tentativa original de ranking focado dependia de uma assinatura de inspeção
  incompatível com o `main` atual e não melhorava a cobertura final. Ela foi
  descartada; a busca corrente não mudou.
- A aplicação de memória aprovada incluía a pergunta do usuário como se fosse
  evidência. Agora a pergunta é apenas o pedido; somente a síntese previamente
  aprovada é entregue como evidência.
- O adaptador local continha nomes e hashes de pesos específicos de uma máquina.
  Agora o chamador declara explicitamente o nome esperado do arquivo carregado,
  e o transporte aceita somente loopback.
- Respostas podiam conter texto fora dos campos pedidos ou citar uma fonte vazia.
  Esses casos agora são rejeitados estruturalmente.

## Capacidades adicionadas

- `num_batch` opcional e validado no transporte Ollama e na configuração.
- Serialização opt-in para um Qwen 3.5 instalado com template prompt-only, com
  recusa de dupla serialização e de delimitadores reservados no conteúdo.
- Transporte opt-in para `llama.cpp`, restrito a loopback, com verificação do
  arquivo de modelo carregado, limite de entrada, schema JSON e truncamento
  explícito.
- Propostas fundamentadas em JSON ou prosa com evidência identificada, hashes,
  projeção declarada de listas longas e estado semântico sempre pendente.
- Triagem conservadora de números, métricas e alegações econômicas. Alertas são
  roteamento para revisão; ausência de alerta nunca é aprovação.
- Recuperação de memória apenas quando existe aprovação explícita e as fontes
  continuam acessíveis sob a política atual. Toda nova aplicação é persistida
  como proposta não aprovada.

## Validação

- 18 testes direcionados cobrem transporte, identidade do modelo, parsing,
  evidência vazia, preâmbulo não analisado, números com sinal/unidade, memória
  aprovada e não herança de aprovação.
- Suíte completa do `main`: **889 aprovados, 1 ignorado e 2 avisos de
  dependências**.
- `ruff check .` aprovado.

As primeiras tentativas da suíte completa falharam durante a coleta porque os
executores escolhidos não continham todas as dependências de desenvolvimento.
Elas não foram contadas como falhas do código. A execução final compôs os
ambientes locais já existentes, sem instalar sobre a distribuição principal.

## Limites

Os testes de transporte usam respostas simuladas. A última tentativa real com
o modelo corrigido foi recusada pelo gate de RAM antes do carregamento. Portanto,
esta publicação valida contratos de engenharia e contenção; não valida qualidade
semântica do modelo, hipótese científica, rentabilidade ou lucro.

Os novos módulos são opt-in. Nenhum fluxo existente passa a exibir ou aprovar
automaticamente suas propostas. Consumidores devem usar `user_response` para um
estado seguro e conservar a proposta bruta somente como artefato de auditoria.
