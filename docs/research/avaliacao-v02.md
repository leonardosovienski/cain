# Avaliação funcional v0.2

O novo modo `functional` registra respostas de um LLM real e verifica mecanismos observáveis
de persistência, correção de preferência, isolamento de usuários e passagem pelos três agentes.
Ele mantém a distinção entre funcionar mecanicamente e responder bem. Não é coleta formal
A/B/C e não aceita ADRs automaticamente. Os resultados e os insumos das execuções antigas
permanecem preservados nos seus diretórios originais.

## Executar com Ollama

Na raiz do projeto, com o modelo já instalado e o serviço disponível:

```powershell
python -m cain.evaluation --mode functional --provider ollama --model qwen2.5:3b --output evaluation/results --run-id functional-v02 --timeout 120
```

A CLI recusa provedor fake nesse modo. Não instala modelos nem troca silenciosamente de
provedor. O adaptador programável aceita dublê somente com a identificação `injected-test`,
usada nos testes mecânicos; o relatório marca explicitamente que não é LLM real.

## Plano fixado antes da execução

| Etapa | Pedido e observação |
|---|---|
| 1 | Alice declara preferência por passos; o estado explícito deve armazenar `steps`. |
| 2 | Outro processo abre o mesmo banco, em nova sessão; antes do pedido de código, `steps` já deve estar carregado. |
| 3 | Outro processo recebe correção explícita para parágrafo; o estado passa a `paragraph`. |
| 4 | Outro processo abre nova sessão e resume texto controlado; `paragraph` deve existir antes da entrada. |
| 5 | Bruno pergunta por sua preferência; seu estado permanece vazio e o contexto não contém o identificador de Alice. |
| 6 | Alice pede busca de um fato sintético; o LLM recebe a passagem real e a resposta identifica o arquivo consultado. |

Cada etapa real executa em subprocesso Python separado, fecha o runtime e usa o mesmo arquivo
SQLite. Não se trata apenas de trocar o identificador de sessão. Os PIDs observados e os
estados antes/depois são preservados. As chamadas de teste com dublê reiniciam somente o
runtime; seu check de reinício de processo fica nulo, com explicação.

O plano, o corpus sintético e seus identificadores são escritos em `inputs/` antes das respostas.
O corpus declara o código artificial `BOREAL-731`, prazo de 7 dias, na fonte
`guia-funcional-cain.txt`. Essa fonte é fornecida ao runtime, sem busca externa ou documentos
particulares. A evidência original injetada e a resposta do agente ficam registradas.

## O que os checks estabelecem

Os checks automáticos comparam os valores de formato no estado, sua presença no contexto
efetivamente enviado ao modelo, a persistência antes de processar a nova entrada, o isolamento
do usuário, o agente selecionado, a geração concluída e a fonte identificada. A personalidade
é comparada entre todos os estados observados e deve permanecer estável.

Esses checks não atestam que uma resposta segue o formato esperado, que um resumo preserva
todos os fatos ou que o código gerado funciona. As respostas integrais estão no relatório
para revisão humana. Nenhum código gerado é executado pelo harness. O check de fonte só
comprova que o modelo recebeu a evidência e a saída identifica o documento; atribuição fiel
de cada afirmação ainda exige inspeção. As métricas de qualidade humana ficam nulas.

## Rastreabilidade e falhas

`config.json` contém commit observado, estado limpo/modificado da árvore, hashes dos arquivos
Python, hash do plano, temperatura e seed solicitadas. O digest do modelo é observado em
`/api/tags` e a versão do serviço em `/api/version`; se não for possível observá-los, o campo
fica nulo com motivo. Esses dados não são inventados a partir do nome do modelo. Seed não
garante determinismo do backend.

As opções locais efetivas do adaptador também são registradas: janela `num_ctx`, limite de
geração `num_predict` e guarda conservadora `max_input_bytes`, além de temperatura, seed e
timeout. A guarda é em bytes UTF-8 e **não é tokenizador**. Cada chamada preserva uma cópia
independente de `last_metadata`, quando o adaptador a fornece: modelo reportado, motivo do fim,
contagens de tokens reportadas pelo backend, durações e tamanho da entrada. O dublê não
preenche essas contagens. Valores ausentes ficam nulos ou vazios conforme a resposta observada.

Cada etapa tem `stages/*-request.json` e `*-result.json`; `raw.jsonl` reúne os resultados,
estados e contextos. `decisions.jsonl` preserva a trilha auditável. Se uma etapa falhar,
`failure.json` registra a falha e lista as etapas não executadas. A execução para sem criar
respostas para elas. O relatório mantém os resultados anteriores à falha e a CLI retorna erro.
Reutilizar um `run_id` existente é recusado.

O harness funcional não corta globalmente o contexto. Os serviços aplicam os limites de
recuperação documentados, e o adaptador recusa entradas acima da guarda em bytes. Essas
unidades não estabelecem equivalência de tokens entre braços.

## Mudança na medida de preferência do smoke

O fixture v0.2 explicita a declaração de formato no começo do pedido. O ground truth de agente
permanece o mesmo. O vetor `[steps, paragraph]` é obtido diretamente do formato armazenado;
ausência e valores fora dessas duas categorias ficam nulos, em vez de receber vetores inventados.
A distância à preferência declarada é calculada apenas quando as sessões têm observações
compatíveis. Esse resultado descreve regras de armazenamento de preferências explícitas,
sem estabelecer aprendizagem implícita ou adaptação psicológica. Um vetor correto que permanece
correto tem redução de distância zero: não se premia mudança arbitrária.

Na demonstração funcional o alvo muda deliberadamente de passos para parágrafo. Não se calcula
convergência ao longo desse alvo móvel; cada etapa é comparada com sua declaração vigente.

## Limites ainda abertos

O formato preferido pode se sobrepor à superfície usada para avaliar estilo. IDs distintos
de sondas não demonstram independência de construtos. Expertise e metas não são aprendidas
pelo extrator de preferências desta versão. O protocolo formal A/B/C continua bloqueado por
pré-registro, validação do instrumento, decisões metodológicas e equivalência de tokens e
exposição ao histórico. C pode recuperar interações de sua própria sessão e B recebe somente
sessões anteriores no smoke: essa diferença impede atribuir resultados à estrutura da identidade.

Testes com dublê validam os mecanismos e os arquivos do instrumento. Apenas a execução real
produz saídas reais; nem essa execução, por si só, demonstra qualidade, satisfação ou validade
de construto.
