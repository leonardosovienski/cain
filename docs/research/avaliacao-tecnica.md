# Harness antecipado de avaliação

O instrumento implementa o desenho proposto em ADR-0010 e §6/§12.3 do documento mestre.
**ADR-0010 continua Proposto.** Não foi aceita nenhuma decisão metodológica e não foi realizada
coleta formal. A rubrica preliminar foi escrita antes da primeira execução técnica. Ela precisa
de revisão, validação e pré-registro em commit datado; hashes de arquivos não substituem isso.

## Executar o smoke

Na raiz do projeto, após `python -m pip install -e ".[dev]"`:

```powershell
python -m cain.evaluation --mode smoke --output evaluation/results --run-id smoke-local
```

O padrão é `FakeLLM`, um dublê determinístico sem inferência. A execução atravessa seis cenários,
três sessões por cenário e três braços. Cada sessão contém a tarefa, três sondas de estilo e
duas sondas de perfil: 324 registros ao todo, incluindo saídas do agente Busca não-LLM.
O corpus e as personas são sintéticos. Cada cenário tem usuário isolado; sessões compartilham
esse usuário. Não há dados pessoais de participantes.

- **A:** prompt de sistema estático, sem transcritos.
- **B:** mesmo prompt estático mais transcritos brutos de sessões anteriores do próprio braço.
  As respostas da sessão atual só entram no histórico ao terminar a sessão.
- **C:** runtime completo com roteamento, identidade estruturada, persistência e mediação.
  A adaptação continua um stub explícito.

O wrapper registra prompt, contexto e resposta de cada chamada real ao adaptador. No smoke,
limita C por caracteres Unicode, preservando o início do contexto estruturado, e limita B ao
orçamento observado de C, incluindo o prompt estático de B. Quando os transcritos são menores,
B recebe menos caracteres; isso fica visível nos logs. **Caracteres não são tokens.** O contador
é uma fronteira substituível (`ContextCounter`), e a equivalência exigida pelo ADR ainda não
está demonstrada. O orçamento inclui instruções específicas do agente em C, outro fator que
precisa de controle antes da coleta. Busca C não chama LLM: nesses casos o pareamento de
contexto é nulo, B fica apenas com prompt estático e nenhuma inferência B/C é válida.

## Artefatos de cada execução

O diretório recebe o `run_id`; repetir o mesmo ID falha, preservando os dados anteriores.

| Arquivo | Função |
|---|---|
| `config.json` | Provedor, modelo, temperatura, seed solicitada, orçamento, hashes e bloqueios. |
| `inputs/` | Cópia exata dos cenários, sondas e rubrica usados. |
| `raw.jsonl` | Todos os prompts, respostas, contextos, decisões e limitações por observação. |
| `decisions.jsonl` | Eventos de auditoria exportados, incluindo razões e fases mediated/completed/failed. |
| `cain.sqlite3` | Estado e trilha de decisões do runtime C. |
| `blind/paired.jsonl` | Respostas pareadas, com ordem randomizada por seed e identificadores opacos. |
| `private/unblinding.json` | Chave separada: relaciona amostras/condições aos braços. |
| `metrics.json` | Matriz 3×3 do roteador e métricas indisponíveis como nulas com motivo. |
| `report.md` | Interpretação limitada à execução preparatória. |
| `failure.json` | Se houver falha, preserva motivo e quantidade de registros anteriores à falha. |

O identificador cego da condição permanece estável dentro do cenário ao longo das sessões,
permitindo medir estabilidade sem abrir a chave. A posição muda em cada par. Compartilhe apenas
`blind/` e a rubrica com os avaliadores. Uma resposta pode sugerir o sistema que a gerou; o
protocolo deve registrar suspeitas de quebra do cegamento. A randomização implementada é da
apresentação, não da ordem de execução: C precisa preceder B no smoke para observar o orçamento.

## Métricas e limites atuais

O ground truth define dois cenários por agente antes da execução; metade usa intent explícito
e metade inferência. Acurácia e matriz 3×3 contabilizam apenas tarefas C, separando os dois
modos. Sondas não entram nessa matriz. A/B não roteiam, portanto não têm acurácia de delegação.
Mesmo uma matriz perfeita no smoke só verifica as regras provisórias com os exemplos escolhidos.

As sondas `style-*` medem `PersonalityState`, com fatos constantes em todas as sessões; as
`profile-*` se destinam a `UserModel`, com preferências conhecidas. O código verifica apenas
que os IDs são diferentes e que os rótulos de superfície correspondem ao conjunto; isso não
valida independência de construtos. Preferência por passos/parágrafo pode se sobrepor a estilo
de estrutura/verbosidade. O piloto precisa testar essa ameaça e estabelecer extração independente
do conteúdo da preferência declarada, sem premiar o formato da própria resposta. A biblioteca
implementa distância ao vetor-alvo e redução da
distância, distância de cosseno entre embeddings fornecidos e percentual de concordância humana.
Ela não gera embeddings artificiais nem preenche notas humanas. Sem vetores reais, extrator de
perfil validado ou avaliadores, as respectivas métricas permanecem nulas. O stub não produz
convergência de perfil mensurável. Não foram coletados dados de satisfação.

## Piloto real do instrumento, preparado

Com Ollama acessível e o modelo já disponível, execute:

```powershell
python -m cain.evaluation --mode pilot --provider ollama --model qwen2.5:3b --output evaluation/results
```

Esse comando solicita respostas de duas personas de estilo contrastante para as três sondas,
repetidas em três sessões independentes: 18 respostas. Ele exporta pares cegos para 2–3
avaliadores aplicarem a rubrica. Não usa orçamento em caracteres e não compara os braços A/B/C;
serve para validar o instrumento antes do experimento. Provedor fake é recusado no modo pilot.
A temperatura é fixada e a seed é solicitada ao Ollama; isso não garante determinismo do backend.
Nenhum pacote/modelo é baixado automaticamente e não há fallback silencioso para FakeLLM.

**Validade de construto NÃO demonstrada por fake.** Até avaliação humana do piloto real, não se
afirma que as sondas discriminam personas. Rodar o LLM, por si só, também não fecha esse critério.

## Bloqueios antes de coleta formal

`--mode formal` recusa a execução e lista as pendências. Não existe flag para aceitar ADRs.
É necessário fechar identidade/adaptação, revisar e pré-registrar rubrica/ground truth, obter
decisões institucionais pertinentes, demonstrar validade de construto e implementar equivalência
de tokens com o tokenizador real do modelo, incluindo controles de contexto e diferenças entre
agentes. Não descarte resultados após observá-los. Preserve falhas e invalidações justificadas.

Há ainda um confundidor de exposição: C persiste cada interação e pode recuperá-la em sondas
posteriores da mesma sessão, enquanto B só injeta sessões anteriores. Antes do experimento,
congele snapshots por sessão/sonda ou iguale a informação disponível entre os braços. O smoke
atual não permite atribuir qualquer diferença B/C à estrutura da identidade.

Satisfação é secundária e descritiva; o plano substituto do ADR é avaliação qualitativa por
2–3 avaliadores cegos. Não aplicar significância com n < 20. O scaffold não autoriza recrutamento,
contato com terceiros, aceite de ADR ou qualquer publicação externa.
