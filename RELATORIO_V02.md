# Cain 0.2 — implementação funcional

> Registro histórico da entrega indicada neste documento. Para estado e caminhos atuais, consulte [Continuidade](CONTINUIDADE.md).

Atualização de 7 de setembro de 2026, horário de Brasília.

Os quatro passos técnicos foram implementados: modelo real, atualização de
preferências, política de memória e agentes com capacidades concretas.
O Cain já pode ser usado localmente para conversar, gerar código, resumir textos
e consultar documentos ou URLs públicas indicadas no pedido.

## Abrir e experimentar

Nesta máquina, abra [INICIAR_CAIN.cmd](INICIAR_CAIN.cmd). O Python, Ollama e modelo
estão instalados; o inicializador inicia o serviço local quando necessário.

1. Diga: `Prefiro respostas em passos.`
2. Peça: `Escreva código Python para somar dois números.`
3. Encerre com `/sair` e abra novamente.
4. Diga: `Agora prefiro um parágrafo.`
5. Use `/perfil` para consultar o estado e `/esquecer format` para remover essa preferência.

O perfil persiste em SQLite. Remover uma preferência atual não apaga o histórico
de auditoria. Os comandos e a API local estão descritos no [README](README.md).

## O que passou a funcionar

| Passo | Entrega |
|---|---|
| Modelo real | Ollama 0.33.3 e Qwen 2.5 3B instalados, com inferência local na GPU. Configuração em `cain.toml`, metadados de geração registrados e falhas explícitas. |
| Preferências | Reconhecimento conservador de declarações de formato, extensão e idioma; correção, procedência, revisão, consulta e remoção por usuário. Não há treinamento dos pesos do modelo. |
| Memória | Perfil atual prioritário, recuperação lexical limitada por usuário e exclusão de episódios com preferências antigas do contexto recuperado. Estado e sinais são gravados em uma transação. |
| Agentes | Busca em arquivos e URLs públicas com fontes; Código gera ou analisa código; Resumo condensa textos fornecidos. Regras de roteamento e classificador LLM opcional escolhem a capacidade. |

O agente Código não executa os programas gerados. A consulta a URLs recebe um
endereço explícito; não é um mecanismo de pesquisa geral na internet.
Preferências são extraídas da entrada do usuário, separando conteúdo citado e
respostas dos agentes. A personalidade permanece separada dessas preferências.

## Evidência observada

A [verificação final da versão](evaluation/results/verification-v02-final/verification.json)
registrou **149 testes aprovados**, Ruff sem erros e disponibilidade do modelo.
Os testes cobrem persistência, correção, remoção, isolamento, contratos da API,
roteamento, recuperação de fontes e limites de entrada.

A [demonstração funcional final](evaluation/results/functional-v02-qwen-02/report.md)
executou **seis processos distintos e seis chamadas reais ao Qwen**, todas encerradas
normalmente. A preferência por passos estava presente antes de uma nova sessão;
a correção para parágrafo também sobreviveu ao reinício. Um segundo usuário
permaneceu sem as preferências e memórias do primeiro.

Na busca, o modelo respondeu corretamente `BOREAL-731` e `7 dias`, fatos existentes
no documento sintético fornecido. A aplicação anexou a fonte `[S1]` correspondente
ao registro recuperado. Os [resultados brutos](evaluation/results/functional-v02-qwen-02/raw.jsonl)
preservam entradas, respostas, contextos e metadados; as [métricas](evaluation/results/functional-v02-qwen-02/metrics.json)
distinguem verificações mecânicas de qualidade humana e validade científica.

A primeira [execução real](evaluation/results/functional-v02-qwen-01/report.md)
revelou um marcador de citação inventado, `[F1]`. Essa execução foi preservada.
A correção separou a síntese do modelo da lista de fontes montada pela aplicação
e passou a rejeitar marcadores bibliográficos gerados no corpo. A segunda
execução confirmou a ausência desse erro no exemplo avaliado.

A [verificação das interfaces](evaluation/results/live-interfaces-v02/results.json)
também registrou uma consulta real bem-sucedida a `https://example.com`, com fonte
correta. Nessa mesma verificação, uma pergunta informacional simples recebeu um
pedido desnecessário de esclarecimento; esse caso motivou o ajuste final do roteador.
Após o ajuste, [duas perguntas claras chegaram à busca e uma vaga pediu esclarecimento](evaluation/results/live-interfaces-v02/route-rule-final/results.json).
Essa classificação foi feita por regra; o Qwen realizou as duas sínteses. A segunda
síntese contém uma contradição: primeiro lista formato, idioma e extensão, depois
afirma que só idioma e formato podem ser alterados. O registro foi mantido integralmente.

O [teste do inicializador](evaluation/results/launcher-v02/results.json) abriu a
conversa, registrou a preferência por respostas curtas, exibiu o perfil, removeu a
preferência e encerrou normalmente. Essas confirmações são determinísticas e não
foram contadas como inferências do modelo.

## Limites que continuam relevantes

- O modelo pequeno pode alongar respostas, errar gramática ou não seguir o formato
  em todas as respostas. A confirmação inicial da demonstração veio em parágrafo
  mesmo após declarar passos; a explicação do código ficou longa para “brevemente”.
- O reconhecimento de preferências usa uma gramática limitada. Preferências
  temporárias de uma tarefa e permanentes ainda precisam de distinção mais refinada.
- O roteamento por linguagem natural também tem limites. A tentativa de resolver
  as perguntas claras apenas alterando o prompt do Qwen continuou pedindo
  esclarecimentos; os [três casos foram preservados](evaluation/results/live-interfaces-v02/route-prompt-attempt/results.json).
  Perguntas informacionais com assunto explícito passaram a ter uma regra própria.
- A busca é lexical. Não há memória semântica, retenção temporal automática,
  exclusão definitiva de todo o histórico ou execução de código.
- A janela configurada é 8.192 tokens, com até 768 de geração. O limite adicional
  de entrada de 6.500 bytes é conservador e **não substitui um tokenizer** nem
  estabelece equivalência de orçamento entre condições experimentais.
- Os resultados são evidência de funcionamento nas entradas avaliadas. Não há
  avaliação humana independente nem comprovação de eficácia ou validade de identidade.
  A aprovação do protocolo, orientação e vínculo com a UFPR continuam pendentes.

O [ADR 0012](docs/adr/0012-preferencias-explicitas-e-memoria.md) registra a decisão
de engenharia como provisória. Os anexos originais, resultados anteriores e
pendências metodológicas foram preservados.

Os binários do Ollama, os pesos e os bancos pessoais não acompanham o ZIP ou Git.
Em outro computador, siga a instalação no README. A configuração local desta
máquina utiliza os recursos preparados no diretório de trabalho do Codex.
