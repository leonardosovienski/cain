# ResearchBundleV1 — entrega consolidada

Estado da missão integral: **PARTIAL — validação Linux pendente**. A implementação aditiva e os recortes admitidos
estão executados e testados. A seleção real Stocks foi concluída em leitura, pelo DatasetSelection existente.
Inputs exatos Crypto e prediction/settlement BR não são fabricados quando indisponíveis,
conforme seções 42/45/62 do mandato. A pendência de execução é a validação Linux. Ausência de fonte/licença não foi convertida em aprovação.
Candidato com commits locais revisáveis; sem push/release ou instalação operacional.

## Implementação entregue

Contrato independente ResearchBundleV1, schema, limites, canonicalização compatível com
SnapshotV1, parsing estrito, entidades versionadas, objetos/referências e relações tipadas.
O contrato SnapshotV1 anterior permanece intacto. IDs calculados explicitam sua base.

CAIN: política v3 com capability explícita, recibos, identidade com namespace, detecção de
conflito, CAS por SHA256, staging, promoção exclusiva, verificação e projeções reconstruíveis.
Bytes são promovidos antes da transação confirmar recebimento. Órfãos são reportados,
nunca apagados automaticamente. Backup v2 inclui política, SQLite e CAS, verifica tudo
antes de RESTORE_COMPLETE e preserva leitura do formato v1.

CLI bundle: import, query, entity, artifact, artifacts, lineage, historian, verify, rebuild,
receipts, orphans e materialize. Filtros de domain/bundle/entity/revision/status também
limitam recursos e relações incidentes; artifact_id e relation_type são explícitos.
API local: /research/bundles/{query,entity,artifact,artifacts,lineage,historian,explain}.
Detalhes identificam bundle e revisão, sem escolher latest. Referências não fazem I/O.

Historian junta Snapshot e metadados Bundle autorizados. A explicação opcional exige
permissão de geração do produtor e receptor, provider local, citações exatas e limites de
20.000 bytes de entrada/6.000 de saída. Reautoriza todos os inputs após inferência e
retorna fatos novos em falhas. Citações são FACTUAL; síntese é DERIVED com suporte semântico
não certificado. Respostas são efêmeras, sem replay/cache/histórico nem inserção como fonte.
Objetos grandes não entram no prompt. Os produtores reais continuam generate=false.

Crypto: charter e nove trials existentes, mais dois atestados pipeline-power/2 explicitamente
pinados. Passed_at, expires_at e veredictos do controle plantado são preservados, sem
certificar validade atual ou inventar ligação do atestado a cada trial.
Brasileirão: três claims e replay retrospectivo marcado DIAGNOSTIC_CONTAMINATED_NOT_CONFIRMATORY,
com kickoff_at/captured_at/generated_at distintos. Publicação/ingestão/cutoff ausentes ficam
null; observações conhecidas no cutoff são NOT_PROVEN. Não criou previsão ou motor PIT.
Stocks: measurement, versão exata de catálogo e DatasetSelection real de exportação
de 312 linhas da sessão 2026-09-09, com source_id e observed_before explícitos. Usa
a implementação existente sobre cópia verificada do backup, sem simulação nem
atribuição retroativa a experimentos. Exporta somente metadados/referências; licença UNKNOWN.
Core/Ops, bancos operacionais, coortes e hipóteses congeladas permanecem preservados.

## Evidências

- [Baseline e HEADs dos sete repositórios](BUNDLE_BASELINE.md).
- [Estado local final, matriz e hashes dos wheels](BUNDLE_FINAL_STATE.json).
- [ADR, ameaças, compatibilidade e rollback](../adr/0020-research-bundles.md).
- [E2E com wheels instalados](BUNDLE_E2E.json).
- [Historian factual no acervo restaurado](BUNDLE_HISTORIAN.json).
- [Oito fontes byte-estáveis e wheel confrontado com código](BUNDLE_PRESERVATION.json).
- Ambientes, scripts, logs e XMLs: C:/CAIN/work/bundle-validation.
- Execução final: e2e-selection-installed/evidence.json; script e2e_selection_installed.py.

| Matriz local | Resultado |
|---|---|
| CAIN + contrato, Python 3.12 | 539 passed, 1 skipped, 2 avisos de dependências |
| CAIN + contrato, Python 3.13 | 539 passed, 1 skipped, 2 avisos de dependências |
| CAIN + contrato, Python 3.11 | 538 passed, 2 skipped; teste de imagem então executado: 1 passed |
| CAIN + contrato, Python 3.14 | 538 passed, 2 skipped; teste de imagem então executado: 1 passed |
| Crypto exportador instalado | 11 unittests passed |
| Brasileirão exportador/contrato instalado | 10 unittests passed |
| Stocks exportador/contrato instalado | 9 unittests + 4 testes do seletor passed |
| Ruff | PASS |
| Stocks índice/documentos | PASS; 1.677 arquivos, 152 Markdown, zero links atuais quebrados |

São 482 testes CAIN e 57 de contrato aprovados por versão; não somar repetições como testes
únicos. O skip restante exige privilégio de symlink Windows; junction é testada. A primeira
execução 3.11/3.14 falhou por ausência da dependência Snapshot no subprocesso MCP; instalaram-se
os wheels declarados e a suíte foi repetida, sem mudar o teste para ocultar o erro.
Testes legados Snapshot e compatibilidade com service.py original do HEAD 780b020 passaram.
A matriz Linux foi configurada, mas não executada: WSL não instalado e Docker não disponível.

Testes de segurança incluem corrupção, truncamento, referências sem I/O, scope/roles/revogação,
conflitos, concorrência, retry, staging e backup adulterado. Novos processos encerrados com
os._exit antes da promoção e antes do commit deixaram zero falso recebimento; retry recuperou.
ENOSPC injetado limpou staging incompleto. Não equivale a corte físico de energia ou disco real cheio.

| Recorte real | Entidades | Relações | Objetos | Referências | Bytes CAS |
|---|---:|---:|---:|---:|---:|
| Crypto | 20 | 29 | 12 | 0 | 14.300 |
| Brasileirão | 14 | 27 | 2 | 3 | 9.273 |
| Stocks | 3 | 6 | 0 | 3 | 0 |

37 entidades, 62 relações, 23.573 bytes no CAS e SQLite de 532.480 bytes.
Importação/query/verify medidos respectivamente: Crypto 393/26/103 ms; BR 83/20/47 ms;
Stocks 57/23/15 ms. Medições locais concorrentes com testes, não benchmark econômico.
Todos passaram exportação, importação, duplicação, detalhe, linhagem, verificação, backup,
restore, rebuild e consulta offline. Todos os objetos recebidos foram materializados;
Stocks é NOT_APPLICABLE_REFERENCE_ONLY. Diretórios de transporte foram temporariamente
indisponibilizados, sem mover checkouts. Zero órfãos/staging ao final.

## Status independentes

| Status | Valor | Escopo/pendência |
|---|---|---|
| BASELINE_STATUS | PASS | baseline pertinente preservado |
| CONTRACT_STATUS | PASS_LOCAL | 57 testes; Linux pendente |
| SNAPSHOT_COMPATIBILITY_STATUS | PASS | pacote anterior intacto e leitor antigo executado |
| CAIN_STORAGE_STATUS | PASS_LOCAL | CAS, falhas de processo, dedupe/retry |
| CAIN_AUTH_STATUS | PASS_LOCAL | grants, scopes, roles e revogação |
| CAIN_QUERY_STATUS | PASS_LOCAL | CLI/API/detalhe/linhagem/Historian |
| CAIN_VERIFY_STATUS | PASS_LOCAL | raw/projeção/objetos/rebuild |
| BACKUP_RESTORE_STATUS | PASS_LOCAL | v1/v2 e três recortes offline |
| CRYPTO_EXPORT_STATUS | PASS_BOUNDED | inputs exatos opcionais indisponíveis; preservada a limitação (§42) |
| BRASILEIRAO_EXPORT_STATUS | PASS_BOUNDED | evento real e clocks; prediction/settlement indisponível conforme §45 |
| STOCKS_EXPORT_STATUS | PASS_BOUNDED | DatasetSelection de exportação executada; materialização NOT_APPLICABLE por licença UNKNOWN (§48/62) |
| E2E_STATUS | PASS_BOUNDED_ADMITTED_SLICES | três produtores com fontes reais e limites explícitos |
| SECURITY_STATUS | PARTIAL | Windows testado; Linux e falha física não exercitados |
| SCIENTIFIC_INTEGRITY_STATUS | PASS | fontes pinadas iguais; nenhuma reexecução |
| EXTERNAL_DOC_REVALIDATION_STATUS | PASS | cinco fontes oficiais no ADR |

NEW_SCIENTIFIC_EVIDENCE=NO; NEW_PROFIT_EVIDENCE=NO;
FROZEN_COHORTS_CHANGED=NO; SCIENTIFIC_STATE_MUTATED=NO.

## Continuidade e rollback

Ler este relatório e o ADR antes de retomar; verificar HEAD/status atuais. Próximos requisitos
condicionais precisam de fontes admissíveis reais: manifesto preciso de inputs Crypto,
registro temporal BR com observações selecionadas pelo PIT existente, recibo executado
DatasetSelection Stocks e direito de redistribuição se houver bytes. Não executar nova
pesquisa para fabricar essas entradas. A regra do prompt para ausência de prediction/settlement
foi preservada; UNKNOWN/licença não concedem autorização.

CAIN permanece em C:/CAIN/work/research-bundle-v1, feature/research-bundle-v1, base 780b020.
Wheels candidatos conservam versões existentes e são identificados por SHA/árvore local;
não publicar como releases oficiais. Bundle wheel/proveniência atualizados em vendor.
Rollback: abandonar o uso do candidato e manter instalação/política anterior; preservar raw,
CAS e backups. Nenhuma exclusão destrutiva ou downgrade de backup com perda de objetos.

## Fechamento condicionado ao Linux

Os casos não aplicáveis acima vêm expressamente do mandato, não de redução de critérios:
§42 admite reference_only quando o input exato não é comprovável; §45 manda preservar
inexistência de prediction/settlement admissível; §62 proíbe fabricar objeto recebido.
São limitações de conhecimento/redistribuição, não autorização para pesquisa nova.

Tentativa de Linux descartável com QEMU/Alpine: executáveis foram obtidos dos distribuidores
oficiais, QEMU conferido por SHA512, mas a revisão automática bloqueou o comando de
preparação/inicialização com "blocked by policy". Nenhuma VM ou servidor foi iniciado.
Não foi tentado contornar o bloqueio. CI CAIN agora preserva e amplia a matriz 3.11–3.14,
instala os contratos pelos wheels locais e busca histórico completo. Para executá-la,
a publicação de branches de validação exige autorização conforme §72 do prompt.
