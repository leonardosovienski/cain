# Cain 0.4.4 — integração de três produtores

Execução em 11/09/2026, Windows, Python 3.12.14. O mandato foi a execução integral
do texto recebido, partindo do piloto preservado em C:\CAIN\historico\PROMPT_ORIGINAL.txt.
Este documento substitui as contagens e limitações operacionais da continuidade 0.4.3.

## Percurso entregue

Exportador de relatório permitido → ResearchSnapshotV1 → raiz do respectivo produtor
→ validação e arquivo local Cain → CLI/API/interface → consulta após reinício/restauração.
O Cain 0.4.4 está instalado por wheel não editável em C:\CAIN\.venv, porta 8877.

| Acervo | Fonte permitida | Registros / objetos de evidência | Limite |
|---|---|---|---|
| crypto | charters/scientific_state.json; docs/EVIDENCE_REGISTRY.md | 15 / 7 | Relatos congelados do clone local/l0-exporter, não o estado completo da pesquisa posterior |
| stocks | STOCKS_CURRENT_STATE.md | 1 / 1 | Linha de prontidão econômica, não toda a pesquisa B3 |
| brasileirao | docs/EVIDENCE_REGISTRY.md | 3 / 3 | Alegações documentadas de incrementabilidade por horizonte, sem nova avaliação |

O acervo heterogeneous anterior permanece preservado. As novas integrações têm
publicadores próprios e acervos separados. IDs iguais entre domínios não se fundem.
Os bancos científicos, protocolos, holdouts e ambientes dos produtores não foram abertos
ou modificados pelas rotas entregues. Relatos não são trials reproduzidos.

## Alterações verificadas

- Política v2: imports associa user/project/collection a uma raiz absoluta. Binding
  duplicado, raiz relativa e escopo sem raiz são recusados. Grants continuam controlando
  origem/fontes/geração. Leitura da política v1 e consultas offline permanecem.
- Exportadores stdlib em tools/export_cain_status.py dos dois novos produtores:
  entrada fixa, SHA explícito, fonte commitada, releitura consistente, estado literal,
  recusa de duplicatas/alterações/sobrescrita. Não instalam runtime científico.
- Comando archive: backup do workspace, knowledge, research e política; restore em
  destino novo com hashes e integridade SQLite. Snapshots dos bancos são consistentes
  individualmente, sem alegação de transação global ou proteção contra falha física.
- [Comparação de mercado](research/market-comparison-20260911.md), [ADR](adr/0013-three-producers-and-complete-backup.md)
  e protocolos PT/EN. Sem framework, modelo, rede de agentes ou dependência nova.

## Usar

Abra C:\CAIN\ABRIR_CAIN.cmd. Selecione usuário leo, projeto Geral, expanda
Pesquisa · L0 Historian, escreva crypto, stocks ou brasileirao em Acervo.
Limpe Identidade da fonte ao trocar de domínio; H6 é um filtro Crypto.
Consultar acervo mostra registros; expanda a fonte e a cobertura e inspecione evidência.
Histórico de pesquisa desta conversa permite recuperar consultas.

```text
C:\CAIN\CAIN_RESEARCH.cmd --collection crypto query --source-id H6
C:\CAIN\CAIN_RESEARCH.cmd --collection stocks query
C:\CAIN\CAIN_RESEARCH.cmd --collection brasileirao query --source-id CLAIM-BR-MARKET-001
C:\CAIN\CAIN_RESEARCH.cmd --collection stocks import status-20260911.json
C:\CAIN\CAIN_RESEARCH.cmd --collection brasileirao verify
```

Importações são explícitas; não há sincronização ou monitoramento automático.
As raízes estão na política local: C:\Cripto\cain-l0\publications,
C:\STOCKS\work\cain-l0\publications e C:\BRASILEIRAO\work\cain-l0\publications.
Exportação: seguir README/HANDOFF e tools/export_cain_status.py do produtor, conferindo
o SHA do relatório antes de admitir uma versão. Arquivo já existente não é sobrescrito.

Para instalar em outra máquina: instalar o wheel do contrato em vendor e o wheel Cain
com extras api, configurar bancos próprios e uma política com caminhos locais. Nenhum
producer precisa importar Cain. Fontes privadas e bancos não são distribuídos pelo Git.

```text
cain archive backup --workspace WORKSPACE.db --research RESEARCH.db --policy POLICY.json NOVA_PASTA_BACKUP
cain archive restore PASTA_BACKUP NOVA_PASTA_RESTAURADA
python tools/verify_research_delivery.py --db RESEARCH.db --policy POLICY_V2.json --output NOVA_PASTA_DE_VERIFICACAO
```

Backup inclui dados pessoais de todos os escopos: é operação administrativa local,
sem endpoint HTTP. Preserve permissões do filesystem. Diretório sem manifest.json não
é backup concluído; destino sem RESTORE_COMPLETE.json não é restore concluído.
Não substitui backup externo, bibliotecas/serviços, fontes configuradas fora de knowledge
ou instalação do modelo. Políticas restauradas precisam ser revistas antes da ativação.

## Evidência desta execução

Suíte completa: **381 aprovados, 1 skip**, incluindo sete casos novos. Lint completo
aprovado. O skip é a condição de privilégio Windows já existente, não uma rota omitida.
As primeiras tentativas de baseline encontraram pytest ausente e preparação incompleta
do ambiente auxiliar; depois 370 casos passaram e quatro subprocessos falharam por Cain
ainda não instalado nesse ambiente. Instalação editável de desenvolvimento resolveu essa
falha ambiental. Não classificar essas tentativas como bugs corrigidos do produto.

Wheel 0.4.4: instalação offline em venv limpo fora do checkout, assets e contrato,
workspace/documento, CLI e pip check aprovados. O wheel também foi instalado na
instância principal, que foi reiniciada pelo inicializador existente.

Três publicações reais exportadas, validadas, admitidas e reimportadas como duplicate.
Verificação instalada: 15/1/3 registros, 7/1/3 referências resolvidas, hash e rebuild;
backup/restauração e consultas com TODAS as raízes do produtor apontando para caminhos
inexistentes. Esse ensaio não desliga nem altera processos dos produtores: demonstra
que o consumidor não acessa suas fontes para responder.

Navegador real: H6, Stocks e três alegações Brasileirão consultados na instância 8877;
fontes, estados, hashes, offsets e cobertura inspecionados. Campo de ID Crypto foi
removido antes de enumerar Stocks. Nenhuma resposta de LLM foi usada nessa demonstração.

Backup dos bancos ativos e política anterior criado e restaurado em
C:\CAIN\work\before-044-backup e before-044-restored. O catálogo ativo não tinha
documentos enviados; preservação de knowledge foi exercitada com documentos sintéticos
nos testes novos. Evidências de instalação em C:\CAIN\entregas\0.4.4,
XML da suíte em C:\CAIN\work\full-044.xml. Nenhum dado desses bancos é enviado ao Git.

## Avaliação e limites

Protocolos evaluation/three_producers_{crypto,stocks,brasileirao}.json foram gravados
antes da execução. Quatro perguntas por acervo, PT/EN, estado conhecido e ID ausente.
Consulta estruturada: 12/12; recuperação documental com mesma curadoria e filtro de ID:
12/12. São seis grupos de casos, incluindo controles negativos, não 12 episódios
científicos independentes. Não foi avaliada compreensão livre de perguntas pelo roteador.
Zero chamadas a modelo; benefício semântico comparativo INCONCLUSIVE.

Ollama não estava escutando em 127.0.0.1:11434; provider real não exercitado.
Não baixamos pesos nem enviamos evidências a serviço remoto. Testes adversariais do
Historian continuam cobrindo falhas e revogação; mocks não certificam inferência real.
Nenhum novo lucro, poder preditivo ou validade científica/econômica foi demonstrado.

## Aceite e continuidade

IMPLEMENTATION_STATUS: COMPLETE para os lotes selecionados e contratos de consulta.
INTEGRATION_STATUS: REAL_VERIFIED nos três acervos públicos e limitados acima.
UI_STATUS: INTERACTIVE_VERIFIED.
PROVIDER_STATUS: UNAVAILABLE nesta configuração/execução.
UTILITY_STATUS: INCONCLUSIVE.

Não há falha crítica conhecida nos percursos exercitados. Ausência de inferência real,
avaliação humana/held-out e backup externo permanece pendência explícita, não requisito
silenciosamente removido. A melhoria funcional demonstrada é integração independente
e recuperação completa no escopo local; paridade universal não foi prometida.

Rollback: preservar o backup anterior e publicações; parar apenas o processo Cain,
reinstalar wheel 0.4.3 e restaurar a política v1 do backup. Bancos não tiveram migração
de schema nesta entrega; a versão antiga não interpreta política v2.
Para manter 0.4.4, retomar por CONTINUIDADE.md e esta entrega. Novos acervos exigem
fonte permitida e contrato explícito. Não reabrir hipóteses por causa desta integração.
