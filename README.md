# Cain 0.2 — identidade persistente e agentes locais

Cain usa um LLM local para responder, guarda preferências explícitas em SQLite e
coordena agentes de Busca, Código e Resumo. O perfil sobrevive ao encerramento do
programa. A personalidade fica separada das preferências de formato, extensão e idioma.

## Usar nesta máquina

Abra **`INICIAR_CAIN.cmd`** para conversar. O inicializador reutiliza o Python,
Ollama e Qwen 2.5 3B configurados durante esta execução. Inicia o serviço local em
segundo plano se necessário. Digite `/sair` para encerrar a conversa.

Exemplo:

```text
Prefiro respostas em passos. Resuma: SQLite guarda os dados do Cain.
/sair
```

Abra novamente e peça:

```text
Escreva código Python para somar dois números.
Agora prefiro um parágrafo. Resuma: contratos definem entradas e saídas.
/perfil
```

O Cain deve usar a preferência registrada e aplicar a correção mais recente.
`/esquecer format` remove a preferência atual de formato. Também existem
`verbosity` e `language`. O histórico de auditoria permanece armazenado.

## Instalar em outro computador

Python 3.11+ e Ollama são necessários para inferência local:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
ollama pull qwen2.5:3b
.\.venv\Scripts\python -m cain doctor
.\.venv\Scripts\python -m cain chat --user leo
```

[Ollama para Windows](https://docs.ollama.com/windows) ·
[Modelo Qwen 2.5 3B](https://ollama.com/library/qwen2.5:3b).
Os binários e pesos não fazem parte deste repositório/ZIP.

## Configuração e comandos

`cain.toml` escolhe modelo, endpoint, SQLite e fontes locais. Os caminhos relativos
são resolvidos em relação ao arquivo de configuração. `CAIN_PROVIDER`, `CAIN_MODEL`,
`CAIN_DB` e `CAIN_OLLAMA_URL` podem substituir essas opções.

```powershell
python -m cain run "Resuma este texto: ..." --user leo --intent resumo
python -m cain profile --user leo
python -m cain profile --user leo --forget format
python -m cain run "Busque nos documentos como o perfil é atualizado" --source docs/architecture
python -m cain run "Consulte https://example.com e explique o que informa" --intent busca
```

`--source` pode ser repetido para arquivos `.md`, `.txt`, `.rst` ou diretórios.
`--no-web` desativa consultas a URLs públicas. Sem URL, Busca usa as fontes locais
configuradas. URLs explícitas são lidas com limites de conteúdo/tempo; o agente
inclui as fontes consultadas. Isso não é um mecanismo de busca geral na internet.

O agente Código gera/analisa texto e não executa o código. Resumo condensa o texto
fornecido. O roteador reconhece ordens e separa o pedido do texto citado; pedidos
ambíguos pedem esclarecimento. Perguntas fora das regras podem ser classificadas pelo LLM;
essa opção é controlada por `orchestration.llm_routing`. `--intent` seleciona uma capacidade explicitamente.

## Preferências suportadas

| Campo | Valores | Exemplos de declaração |
|---|---|---|
| Formato | passos, parágrafo, tópicos | “Prefiro respostas em passos”; “Agora prefiro um parágrafo” |
| Extensão | curta, detalhada | “Prefiro respostas curtas”; “Quero respostas detalhadas” |
| Idioma | português, inglês | “Quero respostas em inglês”; “Responda em português” |

A atualização usa padrões explícitos e conservadores. Citações, conteúdo de fontes
e texto gerado pelos agentes não são evidência de preferência. A declaração mais
recente prevalece; o perfil registra origem e revisão. Memórias que contenham
preferências antigas são excluídas do contexto para reduzir sua reintrodução.

## API local

```powershell
powershell -File scripts/start-cain.ps1 -Mode api
```

Abra `http://127.0.0.1:8000/docs`.

- `POST /run`: `user_id`, `session_id`, `payload`, `intent` opcional.
- `GET /profile/{user_id}`: perfil e procedência.
- `DELETE /profile/{user_id}/preferences/{key}`: remove uma preferência atual.
- `DELETE /profile/{user_id}/preferences`: remove todas as preferências atuais.

A API é local, sem autenticação. O inicializador usa `127.0.0.1`.

## Testar e demonstrar

```powershell
python -m ruff check .
python -m pytest -q
python -m cain.evaluation --mode functional --provider ollama --model qwen2.5:3b --output evaluation/results
```

O modo `functional` abre processos separados, registra respostas reais e verifica
persistência, correção, isolamento e fontes. A inspeção de qualidade deve considerar
as respostas brutas, não apenas os checks mecânicos. O modo `smoke` continua usando
um dublê identificado para testar o instrumento A/B/C sem executar o modelo.

## Estado da pesquisa

O comportamento implementado é experimental. A revisão de literatura é focal;
novidade, eficácia e independência das métricas de identidade/adaptação ainda
precisam de validação. A coleta formal permanece condicionada ao protocolo.

- [Resultado da versão 0.2](RELATORIO_V02.md)
- [Política de adaptação e memória](docs/architecture/adaptacao-v02.md)
- [Avaliação funcional](docs/research/avaliacao-v02.md)
- [Auditoria bibliográfica](docs/research/auditoria-fontes.md)
- [13 notas de leitura](docs/research/notas/README.md)
- [Caminho para a UFPR](docs/research/caminho-ufpr.md)
- [ADRs disponíveis](docs/adr/README.md)
- [Entrega inicial, versão 0.1](RELATORIO_EXECUCAO.md)

Os anexos e resultados anteriores estão preservados. Nenhum ADR de pesquisa foi
aceito automaticamente. Fine-tuning, inferência de traços pessoais, ChromaDB,
execução de código e comparação científica conclusiva continuam fora desta versão.
