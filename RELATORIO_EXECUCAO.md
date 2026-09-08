# Cain — relatório da execução

**Data:** 07/09/2026. **Resultado:** repositório inicial implementado, executado e testado.
Esta entrega concretiza as três frentes preparatórias do mestre; não conclui o TCC,
não comprova a hipótese de pesquisa e não representa coleta científica.

## O que foi entregue

| Frente | Entrega | Limite |
|---|---|---|
| Literatura | 13 notas, auditoria das afirmações, propostas de posicionamento e 15 entradas BibTeX | Revisão focal; leituras e comparações adicionais continuam necessárias |
| Esqueleto | Contratos, SQLite, índice reconstruível, log imutável por operações SQL, três agentes, roteador, identidade, CLI e API FastAPI | Modelo/adaptação/roteamento continuam provisórios; adaptação no-op |
| Harness | A/B/C, seis cenários, três sessões, sondas, rubrica, métricas, exportação pareada e chave separada | Smoke sintético executado; piloto de validade com LLM real pendente |
| UFPR | Caminhos de consulta, fontes oficiais e mensagem preparada | UFPR é destino desejado; matrícula, orientador e elegibilidade não confirmados |

Os cinco arquivos enviados estão preservados em `docs/historico/importacao/`, com
manifesto SHA-256. Somente ADRs 0009, 0010 e 0011 vieram no ZIP. Os textos dos
ADRs 0001–0008 e os três documentos históricos anteriores não foram fornecidos.
Não foram fabricados nem marcados como aceitos.

## Verificação executada

- Python **3.12.10**, Windows; dependências registradas em `requirements-dev.lock`.
- **30 testes passaram**. Incluem persistência após reabertura, `drop()/rebuild_from()`,
  isolamento entre usuários, proteção do log contra UPDATE/DELETE/REPLACE, falhas
  sem retry, inclusão de novo agente, contrato HTTP Ollama, CLI, API e harness.
- **Ruff passou**. Pytest emitiu dois avisos de depreciação das dependências de teste
  Starlette/httpx/AnyIO; não houve falha.
- Um pedido pela CLI percorreu as **oito etapas** e deixou estado pronto para outra sessão.
- A API foi exercitada com TestClient, incluindo dois pedidos em sessões diferentes e
  entrada inválida. Nenhum servidor foi deixado rodando em segundo plano.
- O adaptador Ollama foi testado contra servidor HTTP de teste. O serviço Ollama real
  não estava disponível na máquina e nenhum modelo foi instalado ou executado.

Evidência: [verificação](evaluation/results/verification/verification.json),
[saída dos testes](evaluation/results/verification/check-2.txt) e
[pedido completo](evaluation/results/verification/check-3.txt).

## Smoke publicado

`run_id`: **smoke-20260907**. Código executado: commit **b719bf7**.

Foram preservados **324 registros**: 6 cenários × 3 sessões × 3 braços ×
(1 tarefa + 3 sondas de estilo + 2 sondas de perfil). O log possui **216 eventos**
das 108 chamadas ao Cain, com etapas e motivo de delegação.

As 18 tarefas do braço C alcançaram o agente previsto nos exemplos técnicos:
9 usaram intenção explícita, 9 usaram regras de inferência. Esse resultado testa
o encadeamento do roteador provisório e não estima eficácia em tarefas reais.

Coerência, convergência do perfil, satisfação, concordância e validade de construto
estão **nulas com justificativa**, pois não foram medidas. O FakeLLM sinaliza a
simulação nas respostas. O modo formal retorna bloqueio explícito.

Ver [relatório do smoke](evaluation/results/smoke-20260907/report.md),
[métricas](evaluation/results/smoke-20260907/metrics.json) e
[decisões](evaluation/results/smoke-20260907/decisions.jsonl).

## Correções e riscos já identificados

A [auditoria de fontes](docs/research/auditoria-fontes.md) corrige a atribuição dos
três ciclos DSR a Hevner 2007, restringe as conclusões sobre identity drift aos
protocolos estudados e registra capacidades documentadas de memória/estado/seleção
no AutoGen. O argumento de novidade e a impossibilidade de avaliar roteadores LLM
não estão demonstrados pelos anexos.

O smoke usa limite em caracteres, não equivalência de tokens. C pode recuperar
interações da sessão atual, enquanto B recebe sessões anteriores. Além disso,
preferências de formato podem se sobrepor às métricas de estilo. Essas ameaças
constam do harness e precisam de tratamento antes da comparação científica.

## Próximas etapas concretas

1. Definir se o objetivo na UFPR é graduação, coorientação de TCC ou mestrado;
   consultar o caminho preparado em [caminho-ufpr.md](docs/research/caminho-ufpr.md).
2. Completar a revisão de trabalhos próximos e redigir os ADRs ausentes. Fechar
   modelo de identidade e adaptação com alternativas e evidências verificáveis.
3. Disponibilizar Ollama/modelo e executar o piloto de três sondas com personas
   contrastantes. Validar rubrica com avaliadores antes de aceitar o instrumento.
4. Igualar exposição à informação entre B/C, adicionar contagem de tokens do modelo,
   separar operacionalmente perfil e estilo e documentar as decisões institucionais.
5. Só então aceitar o ADR-0010, registrar o protocolo definitivo e iniciar coleta.

ChromaDB e adaptador comercial não foram implementados. O índice lexical atual é
um dublê do contrato de recuperação, e a Busca acessa corpus local. O agente Código
nunca executa o código gerado. Não foram enviados e-mails nem feitas inscrições.

## Uso

Siga o [README](README.md) para instalar e rodar CLI/API. Para repetir o smoke,
use outro identificador para preservar a execução anterior:

```powershell
python -m cain.evaluation --mode smoke --output evaluation/results --run-id smoke-local-02
```

O repositório GitHub desta entrega é `leonardosovienski/cain`, privado inicialmente.
O resultado do workflow remoto deve ser consultado no GitHub Actions; os números
acima são da verificação local registrada, independente do estado remoto.
