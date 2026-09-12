# Remediação CAIN Supply — 12/09/2026

Estado: **remediação local F01–F10 implementada e validada no escopo abaixo**.
E2E e mini-auditoria concluídos. **Não estabilizado: Linux corrente não executado.**
Sem push, release, commit novo ou ativação operacional; mudanças permanecem nos
checkouts para revisão. Os HEADs anteriores não representam estas alterações.

Ordem: desenhos F03, F02/F04 e F01, implementação P1, reataque adversarial,
F07, F05, F06, F08/F10 e documentação F09. O
[desenho](BUNDLE_REMEDIATION_DESIGN.md) e a [ADR](../adr/0020-research-bundles.md)
definem as mudanças de contrato e autorização.

Evidências desta rodada: `C:/CAIN/work/bundle-remediation-20260912`.
Auditoria retrospectiva preservada: `C:/CAIN/work/bundle-audit-20260912/REPORT.md`.
O BUNDLE_REPORT.md anterior é histórico; sua classificação PASS não certifica
os achados de segurança descobertos posteriormente.

## Achados e resultado

| Achado | Correção | Evidência |
|---|---|---|
| F03 P1 | Aprovação administrativa separada de importação scoped; reserva global atômica e hash exato aprovado | Tentativas sem aprovação não consultam entidades/reservas globais; presença/ausência oculta produz a mesma rejeição; concorrência admite uma assinatura |
| F02 P1 | external não dispensa autorização do descritor | Revogação remove relações em serviço, CLI, HTTP e Historian, nos dois perfis |
| F04 P2 | Perfil 2 usa SHA do descritor completo em endpoint externo; perfil 1 preservado | Descritores distintos têm revisões distintas; endpoint não resolvido é omitido |
| F01 P1 | verify/rebuild negam escopo incompleto antes de I/O de objetos | Revogação de role, bundle ou referência produz zero leituras protegidas |
| F07 P2 | Sincronização dos pais da cadeia e de entradas já existentes | Ordem de chamadas e falha injetada impedem commit; não equivale a perda física de energia |
| F05 P2 | Primeiro raw intacto, até sete variantes adicionais por bundle, quota compartilhada | Duplicate preserva bytes; ausência/corrupção falha; backup/restauração conserva variante |
| F06 P2 | evidence paginada, detalhe bundle/id, CLI/HTTP/Historian | Fato somente em evidence recuperável; revogação remove acesso; geração cita evidence |
| F08 P3 | Origem/restrições definidas nos produtores | Helper aceita origem não relacionada aos três projetos, sem defaults de domínio |
| F10 P2 | Manifesto de proveniência recuperável e fingerprint de código/dependências efetivos | Alteração de helper muda fingerprint; wheels, fontes e instalações conferidos byte a byte |
| F09 P2 | ADR e documentos correntes consolidados; relatórios anteriores identificados como históricos | Stocks distingue seleção opcional de experimento histórico; BR corrige contagem; CI antiga não atribuída a código novo |

## Validação executada

- Regressão CAIN + contrato: **562 aprovados, 1 skip**, sem falhas.
- Mini-auditoria: **21 aprovados**, incluindo três casos adicionais aos da regressão.
  Os demais se sobrepõem à regressão; não somar como casos distintos.
- Ecosystem principal: **60 aprovados**.
- Produtores: **23 Crypto, 11 Brasileirão, 15 Stocks**, incluindo Snapshot legado.
- Ruff, diff checks, checker documental Stocks e wheel instalado offline: PASS.
- Snapshot: fontes sem mudanças, três vetores confrontados com serializador histórico,
  sem regeneração de fixture. Core/Ops limpos e sem mudanças.
- **23 arquivos da auditoria anterior conferidos por SHA256 e preservados.**

A mini-auditoria foi feita pelo mesmo executor, não por revisor independente.
Não surgiram novos achados materiais nos casos dirigidos; isso não é prova universal
de ausência de defeitos. O skip é `test_symlink_import_escape`, por ausência de
privilégio Windows para symlink; o teste próprio de junction/reparse do Bundle passou.
As deprecações de Starlette/httpx/anyio estão registradas nos XML/logs.

## E2E real com instalações novas

Dois exports por produtor foram iguais entre si, com as **oito fontes pinadas
inalteradas** e zero chamadas científicas proibidas detectadas pelo guard Python.
O guard observa audit/profile events e hashes; não é rastreamento de kernel.

| Produtor | Entidades | Relações | Objetos | Referências |
|---|---:|---:|---:|---:|
| Crypto | 20 | 29 | 12 | 0 |
| Brasileirão | 14 | 27 | 2 | 3 |
| Stocks | 3 | 6 | 0 | 3 |
| Total | 37 | 62 | 14 | 6 |

Foram exercitados aprovação administrativa, importação/reimportação, consultas,
detalhes de todas as entidades/artefatos/evidências, verificação da proveniência,
materialização de todos os objetos recebidos, backup, restauração em destino novo,
rebuild e materialização sem acesso aos diretórios de transporte dos produtores.
CAS: **23.573 bytes**, zero órfãos/staging ao término. SQLite: **667.648 bytes**.
Evidência integral: `C:/CAIN/work/bundle-remediation-20260912/e2e/evidence.json`.

Bundles testados:

- Crypto: `790a9f3eed755010eb7a1d50fe128531b0b9f6e34e19be64e9e6a73f77cca8ce`
- Brasileirão: `034b293e68854ed238ee2114038f0c10f237da912a913b5cbf82f6263c1d6667`
- Stocks: `d385fbe3d7de5f780619083872f42bcabeaede41f845874ab2beca9909d5809d`

Saídas ficam nas respectivas raízes:
`C:/CRIPTO/operacao/relatorios/bundle-remediation-20260912-real`,
`C:/BRASILEIRAO/work/bundle-remediation-20260912-real`,
`C:/STOCKS/work/bundle-remediation-20260912-real`.

## Artefatos executados e rastreabilidade

Wheels em `C:/CAIN/work/bundle-remediation-20260912/wheels`:

- cain_research 0.4.7: `62bf08010e17a471fd9431ee725806710655c0735fab8f7a5c3d8602a4ad3171`
- predictor_research_bundle 1.0.0: `79fe4d595de0c0f4540c41404406c4974f2d7e656d466b1905ad5614b8138ad5`

São candidatos locais identificados por hash; os números nominais não constituem
uma release nova. `integrity.json` registra bases Git, arquivos alterados e hashes
efetivos. `vendor/bundle-provenance.json` declara explicitamente a origem de working
tree, sem afirmar que o HEAD anterior contém o patch. Proveniência dos produtores
separa code_revision do fingerprint dos arquivos efetivamente usados.

Para revisar/repetir: `regression.xml`, `p1-reattack.xml`, `f07.xml`, `f05.xml`,
`f06.xml`, `f08-f10.xml`, `mini-audit.xml`, `ecosystem.xml`, `wheel-check.log`,
`compatibility.json`, `integrity.json`, `e2e.py` e `export_audit.py` estão na raiz
de evidências desta rodada. Repetições de E2E exigem novos diretórios de saída.

## Mudanças de uso e limites restantes

O administrador deve executar `bundle approve` antes de `bundle import` para cada
hash/escopo. Não distribuir acesso ao CLI administrativo, SQLite ou política a
consumidores não confiáveis. O app local não implementa autenticação remota entre
usuários de sistema operacional. Relações externas ambíguas antigas são preservadas
em raw, porém omitidas da consulta; novos produtores usam perfil 2. Verify/rebuild
agora falham integralmente se qualquer permissão do escopo for revogada.

**CI Linux histórica não cobre estas alterações.** A sequência local pedida foi
concluída até a mini-auditoria; não se declara estabilização ou prontidão operacional.
Não houve ensaio físico de queda de energia. Permanecem os limites admissíveis do
mandato original: não inventar inputs experimentais Crypto, prediction/settlement/PIT
BR ou licença para preços Stocks. UNKNOWN e protocolos/coortes continuam preservados.
Testes de engenharia não demonstram validade científica ou lucro executável.
