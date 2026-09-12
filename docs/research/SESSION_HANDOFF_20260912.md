# Continuidade integral da sessão CAIN Supply — 12/09/2026

## Resposta de encerramento

O chat pode ser apagado depois de preservar este documento e os diretórios de evidência indicados abaixo. Este é um registro estruturado do contexto disponível e dos artefatos, não uma transcrição literal de toda a conversa. O GitHub contém código e documentação publicada; não contém todos os bancos, fontes privadas ou evidências locais. Apagar o chat não autoriza apagar esses diretórios.

**Não está tudo perfeito ou integralmente validado.** Os sete checkouts ativos foram sincronizados e a documentação de entrada foi atualizada. O inventário de 742 Markdown da conferência anterior verificou arquivos, hashes e UTF-8; não revisou semanticamente todas as afirmações de todos os documentos. Relatórios antigos conservam afirmações válidas apenas para suas datas. O gate Linux continua reprovado e a estabilização não foi aprovada.

Este documento é a entrada mais recente para esta sessão. O [registro de publicação](BUNDLE_PUBLICATION.md), o [relatório de remediação](BUNDLE_REMEDIATION.md), o [desenho](BUNDLE_REMEDIATION_DESIGN.md) e a [ADR 0020](../adr/0020-research-bundles.md) detalham suas respectivas etapas. O relatório de remediação foi escrito antes do commit/push e do Linux; suas afirmações de “sem push” e “Linux não executado” são históricas, não o estado presente.

## Pedido, decisões e autorizações

O dono pediu implementação integral do primeiro mandato, auditoria retrospectiva, remediação ordenada, validação Linux e gate final de estabilização. A sequência explicitamente determinada foi:

1. Desenho F03; desenho F02/F04; semântica F01.
2. Implementar P1 e realizar reataque adversarial.
3. F07, F05, F06, F08/F10 e F09.
4. E2E completo, mini-auditoria e somente então discutir estabilização.

Houve autorização explícita para publicação e GitHub Actions, seguida de novo mandato que restringia publicação. A instrução posterior “já pode comitar tudo e fazer o push” autorizou novamente commits e push nas branches existentes. Também foram solicitadas atualização documental de todos os projetos e preservação deste encerramento. Não confundir essa autorização com merge, tag, release, instalação operacional, ativação de modelos/coletas ou operação financeira.

Trabalho solo. Não misturar dados de domínio entre produtores. Não executar campanhas científicas nem tocar coortes protegidas para conseguir CI verde. Preservar hipóteses, trials, ledgers, fontes, UNKNOWN e recibos. A mini-auditoria foi realizada pelo mesmo executor; não é auditoria independente.

## O que foi implementado e por quê

| Achado | Mudança implementada | Limite a conservar |
|---|---|---|
| F03 | Aprovação administrativa do hash exato e reserva global transacional antes do import por escopo | Erros globais ficam na operação administrativa; não esconder conflito global apenas filtrando por escopo |
| F02/F04 | Perfil 2 identifica artefato externo pelo SHA do descritor completo; consulta exige descritor autorizado | External nunca concede acesso; perfil 1 permanece legível; ambiguidade é omitida da consulta, sem reescrever raw |
| F01 | Verify/rebuild exigem autorização integral antes de ler CAS | Negação deve produzir zero I/O protegido; não apresentar verificação parcial como completa |
| F07 | Fsync de arquivo, diretórios e pais antes do commit de metadados | Ordem de syscalls e falha injetada não são prova de resistência a perda física de energia |
| F05 | Primeiro raw preservado; até sete variantes extras por bundle, quotas e recibos verificáveis | Backup/restore/rebuild precisam detectar variante ausente ou corrompida |
| F06 | Evidence paginada e detalhada em serviço, CLI, HTTP e Historian | Fato somente em evidence é recuperável e revogável; não precisa virar objeto CAS |
| F08/F10 | Origem/restrições explícitas nos produtores; manifesto exporter-provenance/1 com arquivos efetivos e dependências | Versão nominal/HEAD sozinho não identifica bytes de working tree ou helper |
| F09 | ADR, relatório e documentos de continuidade | Não usar CI antiga como validação do código corrigido nem sobrescrever evidência antiga |

SnapshotV1 foi preservado. Core e Ops não receberam mudanças de código nesta remediação; somente documentação na conferência posterior. A aprovação local exige acesso administrativo confiável; não existe autenticação remota que transforme acesso direto ao SQLite/Python em consumidor não confiável.

## Evidência local anterior ao Linux

O relatório de remediação registra CAIN + contrato com 562 passes e 1 skip Windows; mini-auditoria com 21 passes parcialmente sobrepostos; Ecosystem principal com 60; exportadores Crypto 23, Brasileirão 11 e Stocks 15, incluindo Snapshot legado. Ruff, conferência de diferenças, checker Stocks, instalação offline e vetores de compatibilidade passaram naquele escopo.

O skip Windows era test_symlink_import_escape. Não foi contado como passe Windows. O gate Linux posterior executou o teste obrigatório. Vinte e três arquivos da auditoria anterior tiveram hashes preservados.

O E2E Windows com fontes reais registrou dois exports determinísticos por produtor, oito fontes pinadas inalteradas, aprovação/import/duplicata/consulta/evidence/proveniência/materialização/backup/restore offline/rebuild. Totais: 37 entidades, 62 relações, 14 objetos, 6 referências; CAS 23.573 bytes, zero órfãos/staging ao final. Esses resultados não substituem E2E Linux instalado.

| Produtor | Bundle real da remediação |
|---|---|
| Crypto | `790a9f3eed755010eb7a1d50fe128531b0b9f6e34e19be64e9e6a73f77cca8ce` |
| Brasileirão | `034b293e68854ed238ee2114038f0c10f237da912a913b5cbf82f6263c1d6667` |
| Stocks | `d385fbe3d7de5f780619083872f42bcabeaede41f845874ab2beca9909d5809d` |

Não foram inventados inputs exatos de experimentos Crypto, prediction/settlement/PIT Brasileirão ou licença para preços Stocks. O recorte BR é retrospectivo/contaminado quando assim indicado. A seleção Stocks é uma seleção desta exportação; não prova input de experimento histórico. Nenhum teste de engenharia demonstra lucro ou validação científica.

## Candidato congelado e Linux real

Candidato: `74da061d1be17326d07d333b7923a717c6ce21c41d6f65f00c5d3947b6d2f248`.
O manifesto e overlays identificam bases Git e bytes alterados, não apenas um HEAD. Os overlays foram preservados em `.ci/cain-supply/overlay.zip` em cada um dos cinco repositórios. O kit central está em `.ci/cain-supply/` e o workflow em `.github/workflows/cain-supply-linux.yml`.

A CI reconstrói as bases anteriores e aplica os overlays exatos em clones novos. Não trocar o manifesto ou overlay antigo para fazê-lo aceitar uma correção posterior. Criar nova identidade e novas evidências quando houver mudança no produto. Os commits documentais posteriores não foram executados como novo candidato de produto.

WSL/Docker/Podman não estavam disponíveis localmente. Uma tentativa de ambiente virtualizado local recebeu bloqueio automático de política; não contornar esse bloqueio. A autorização posterior de push tornou GitHub Actions a via usada.

- [CI geral](https://github.com/leonardosovienski/cain/actions/runs/34674661122): sucesso no código `7e6105e250221d268a20dbbb712bc72b464ccb1f`.
- [CAIN Supply Linux gate](https://github.com/leonardosovienski/cain/actions/runs/34674661161): falha em Python 3.13 e 3.14 na etapa full.
- Artefato 3.13: Ubuntu 24.04.5, kernel 6.17.0-1022-azure, x86_64, uid 1001, umask 022, Python 3.13.15; stat reportou filesystem ext2/ext3. SOURCE_EQUIVALENCE=PASS.
- Direcionados: 187 passes, nenhum skip, incluindo symlink e testes POSIX. Suíte completa: 547 passes, 13 falhas, 4 erros e 2 skips.
- Os dois skips 3.13 foram conferidos no XML durante este encerramento: test_api_launcher_does_not_prepare_ollama e test_windows_launcher_refuses_other_service_without_stopping_it, ambos com motivo “Windows launcher only”. São exclusões de plataforma, não os testes obrigatórios de symlink.
- Os detalhes completos do artefato 3.14 ainda devem ser baixados/analisados; sua falha na mesma etapa foi observada nos jobs/logs, sem atribuir-lhe automaticamente as contagens 3.13.

O fail-fast impediu E2E instalado, restore offline, testes dos produtores e mini-auditoria Linux nessa execução. Real producer export Linux: NOT_EXECUTED. Matriz integrada dedicada: incompleta; não extrapolar para toda a faixa Python >=3.11.

## O que deu errado e o que aprendemos

1. A instalação isolada do wheel encontrou FileNotFoundError para evaluation/scenarios/scenarios.json e quality-v03.json. Inspeção atual: quality.load_dataset e harness._data_root usam Path(__file__).resolve().parents[3], presumindo layout de checkout; package-data declara apenas web/*.html/css/js. Classificação fundamentada: empacotamento/localização de recursos. Não foi corrigido nesta sessão de encerramento.
2. CI geral verde e testes no checkout não bastaram para descobrir esse defeito. O teste da distribuição instalada foi necessário. Não adicionar PYTHONPATH, copiar cenário manualmente para site-packages nem suprimir testes para obter verde.
3. A execução terminou após registrar/publicar a falha, sem cumprir todos os gates da missão Linux. Portanto não se deve declarar a missão técnica concluída, “100%”, READY_FOR_STABILIZATION_REVIEW ou release-ready.
4. Documentos de entrada ainda diziam “sem push” após publicação. Foram acrescentados avisos de precedência e estados atuais. Essa correção contextual não equivale a remover toda ambiguidade de centenas de relatórios históricos. Possível melhoria: separar mais claramente documentos normativos atuais e recibos datados, sem modificar originais congelados.
5. O rastreamento remoto Stocks buscava só main. Foi acrescentado o refspec da branch validation/retest-six-20260911 e restabelecido seu upstream; não houve force-push/reset.
6. Na automação auxiliar da conferência houve uma tentativa inicial de configurar upstream antes do refspec correto e um aviso de escape de caminho no gerador do relatório. Foram corrigidos e a geração/verificação final repetida. Não foram alterações de produto.
7. Contagens de testes sobrepostos não devem ser somadas como cobertura independente. Hashes de arquivos provam identidade, não correção semântica. A revisão pelo próprio executor não é independente.

## Publicação e diretórios de trabalho

Os SHAs abaixo são os verificados ao terminar a conferência documental anterior. Este encerramento acrescenta commits documentais; para HEAD final consultar Git e o recibo local de publicação desta sessão, evitando autorreferência de hash no próprio commit.

| Projeto | Checkout | Branch | SHA anterior ao encerramento |
|---|---|---|---|
| CAIN | C:/CAIN/work/research-bundle-v1 | feature/research-bundle-v1 | d83af66591c738e1e716ebe6ba44a4d5d8f216a2 |
| Ecosystem | C:/CAIN/contrato | feature/research-bundle-v1 | 0ef9f4faaf5ecd1a2732442a34f6dbc0c4c11a00 |
| Crypto | C:/CRIPTO/pesquisa-20260909 | validation/retest-six-20260911 | 84850885391b3c87585f2b2576b76ee6f33613b1 |
| Stocks | C:/STOCKS/stocks-predictor | validation/retest-six-20260911 | 77c71938e2ce6e3d7ce5ce96c219b86643e5a1ec |
| Brasileirão | C:/BRASILEIRAO/brasileirao-predictor | publication-validation-architecture-20260911 | 0e019086d3927c59beea6da8ad548f71a69a65ad |
| Core | C:/PREDICTORS/core-predictor | validation/retest-six-20260911 | 2da7c6d75915c54c554484fc3ef57374163ff49f |
| Ops | C:/PREDICTORS/predictor-ops | validation/retest-six-20260911 | f77a807f775519039e94b57441fa7c89175d0f76 |

Foram inspecionados 19 worktrees. Os sete ativos estavam limpos e com HEAD igual à branch remota. Dois históricos Crypto são exceções: publicacao-chat-20260909 conserva alterações e conflitos em README.md, tests/test_review_failure_boundaries.py e tests/test_store_history.py; restaurado-20260908/projeto contém fred_test.csv não versionado. Não resolver/descartar esses trabalhos como limpeza documental. Outros worktrees conservam suas próprias branches; “atualizar pastas” não significa substituir tudo pelo mesmo checkout.

## O que preservar fora do chat

| Diretório | Conteúdo |
|---|---|
| C:/CAIN/work/bundle-audit-20260912 | Auditoria retrospectiva original, imutável |
| C:/CAIN/work/bundle-remediation-20260912 | Testes Windows, hashes, E2E e wheels da remediação |
| C:/CAIN/work/bundle-linux-validation-20260912 | Candidato original, patches, overlays e preparação anterior à CI |
| C:/CAIN/work/bundle-linux-ci-20260912 | ZIP 3.13 baixado, XML, logs, ambiente, equivalência e hashes Linux |
| C:/CAIN/work/documentation-sync-20260912 | Inventários antes/depois, worktrees e recibos da conferência documental |
| C:/CAIN/work/session-handoff-20260912 | Cópias locais dos três mandatos anexados, hashes e recibo final deste encerramento |
| C:/CRIPTO/operacao/relatorios | Evidências e bundles Crypto, mantidos na raiz própria |
| C:/BRASILEIRAO/work | Evidências e bundles Brasileirão, mantidos na raiz própria |
| C:/STOCKS/work | Evidências e bundles Stocks, mantidos na raiz própria |

Não remover bancos, fontes, arquivos ignorados, diretórios de runtime ou snapshots junto com o chat. Este registro e os commits não substituem backup desses acervos. O ZIP de artefato CI já baixado evita depender apenas da retenção temporária do GitHub.

## Próxima execução: prioridades e critérios de aceite

1. Ler este documento, os três mandatos preservados, AGENTS/regras locais, desenho e ADR. Conferir branches/HEAD/status/CI; não presumir que o estado continuou igual depois desta data.
2. Preservar a falha original. Baixar/analisar artefato 3.14 e confirmar seus skips/falhas. Examinar também probes, rubrics e chamadas de source_metadata: corrigir só os dois nomes observados pode deixar recursos irmãos ausentes.
3. Definir e implementar a menor correção de recursos instalados. Candidato de desenho: incluir recursos próprios no pacote e usar importlib.resources, mantendo caminhos explícitos aceitos e hashes das fixtures. É proposta, não implementação concluída. Não transformar dado externo/científico em recurso redistribuível sem verificar seu escopo.
4. Criar teste de regressão que execute a distribuição realmente instalada fora do checkout, sem PYTHONPATH; verificar os recursos e preservação da proveniência. Repetir o conjunto Windows afetado e criar novo manifesto/overlays com identidade explícita.
5. Rodar Linux dedicado em 3.13/3.14: equivalência antes de testes; segurança/POSIX; suíte completa; pip check, wheel/CLI/recursos; E2E instalado; restore sem transporte original; exportadores permitidos; reataque e mini-auditoria. Registrar cada skip. Não executar suites científicas protegidas para ampliar contagens.
6. Confrontar cobertura exigida F01–F10 com evidência concreta, incluindo todos os observáveis públicos de F03, concorrência, perfis antigos/novos, quotas/recibos, evidência isolada e alteração controlada de proveniência. Teste existente não dispensa verificar a cobertura real do mandato.
7. Completar comparação clean-sheet e avaliação do contrato durável; emitir recomendação explícita e seus limites. Só considerar READY_FOR_STABILIZATION_REVIEW depois de todos os gates exigidos; isso ainda não autoriza release ou validação científica.
8. Melhorias documentais opcionais: índice automático de documentos atuais/históricos; links de sucessão nos documentos mutáveis; recibos com SHA testado separados do HEAD documental; checker de links por projeto; job precoce de wheel instalado. Não reescrever recibos imutáveis para mudar status antigo.

## Prompt de retomada

Continue a missão CAIN Supply a partir de docs/research/SESSION_HANDOFF_20260912.md no checkout C:/CAIN/work/research-bundle-v1. Trabalhe sozinho. Código e documentos foram publicados nas branches indicadas; estabilização NÃO aprovada. O gate Linux 34674661161 falhou na distribuição instalada porque os loaders de avaliação presumem layout de checkout. Preserve os artefatos anteriores, diagnostique e corrija a menor causa, gere novo candidato identificável e conclua Linux/E2E/restore/mini-auditoria antes de discutir estabilização. Respeite as raízes e regras de cada projeto, dados/coortes protegidos, UNKNOWN e limites científicos. Commits/push já foram autorizados; não fazer merge, tag, release, instalação operacional ou campanha científica por inferência. Registre novas evidências e decisões sem depender deste chat.
