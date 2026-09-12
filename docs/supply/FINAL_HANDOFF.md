# CAIN Supply — entrega final para revisão

<!-- supplemental-real-closure -->
**Atualização de fechamento:** houve uma rodada adicional com 33 documentos reais de Core/Ops/Ecosystem, 47 chamadas públicas e comparação estrutural neutra. Persistência, restore offline e revogação passaram. São novas publicações autorizadas em acervo separado, identidade `3f3b34cf116201aea601459668b70480570fa9583575e727228e75fd0c2a8063`; a identidade/CI do candidato base abaixo foi preservada. Consulte `FECHAMENTO_DO_PROMPT.md` e `closure-real-20260912/RESULTS.json`. As menções abaixo aos seis bundles que negam geração referem-se ao acervo original.

Leo pode abrir a **CLI Bundle dos seis acervos** e a **web legada de Crypto/Stocks/Brasileirão**, usando o candidato isolado em `C:/CAIN/work/supply-final-20260912`. Leia `USER_ACCEPTANCE.md`. **USER_PREVIEW_STATUS=LIMITED_IN_STAGING**; **READY_FOR_FREEZE_REVIEW=PASS no escopo de engenharia delimitado abaixo**. Nenhum congelamento administrativo, release ou implantação foi realizado.

- Candidato: `d00bbc6fb910b3c51be6720d21012f4655258468adb7d7335451974929c58752`; wheel CAIN 0.4.7 SHA256 `4fc950531cca6930055636e78485967c647cc5aee2dd326039719ec0af277006`. Identidade instalada: `7da108d0172b7ccc2675404b7dbf0b8a21ad248ee814ea14f199225003d23861`.
- Abrir CLI: `& 'C:/CAIN/work/supply-final-20260912/venv/Scripts/python.exe' 'C:/CAIN/work/supply-final-20260912/preview.py' --collection crypto query --entity-type hypothesis --limit 50`. Encerra sozinho.
- Abrir web: `& 'C:/CAIN/work/supply-final-20260912/venv/Scripts/python.exe' 'C:/CAIN/work/supply-final-20260912/web_preview.py' --legacy`, endereço `http://127.0.0.1:8889`. Encerrar: Ctrl+C somente nesse terminal. Portas 8889/11439 liberadas ao final.
- Perguntas: descoberta, estados literais, evidências, relações e ausências dos seis scopes; 12 comandos específicos e 18 casos do runner exercitados. UI confirmou Crypto 15, Stocks 1, BR 3 revisões, evidência e proveniência, ausência e reinício. Não é 89 experimentos: Bundle e Snapshot usam unidades diferentes.
- Runner: executado e retomado,2→18, sem duplicação. Regras, interpretação por modelo e texto de engenharia estão identificados separadamente.
- Modelo: 3 gerações locais reais com qwen3.5:0.8b, 1 timeout preservado e retry serial de 180 s. História recuperável após backup/restart; revogação redigiu o conteúdo. Citação literal passou; síntese Stocks não está totalmente apoiada. Utilidade semântica permanece inconclusiva.
- Memória derivada: comparação sintética neutra, persistência/offline restore/contradição/revogação passaram. Nenhum ganho/generalização real demonstrado; seis bundles reais continuam negando geração. Uso desabilitado por padrão.

## Código publicado e identidade exata

Branch **`validation/cain-supply-completion-20260912`**, HEAD de publicação local e remoto **`1ab431f4e368b06c7071fa1b3fd44d775d743c8c`**. O último commit altera somente o README, com CI dispensado. Runtime validado no commit **`f0cfb92b20a41e615d28f41e93bae589d680cf84`**, sem alteração posterior de código ou manifesto. CI exata desse runtime: https://github.com/leonardosovienski/cain/actions/runs/34702803998; CI de transporte: https://github.com/leonardosovienski/cain/actions/runs/34702803984. SHA conferido com `git rev-parse HEAD` e `git ls-remote origin refs/heads/validation/cain-supply-completion-20260912`.

A raiz dessa branch contém o baseline e o kit de validação. **O runtime corrigido está no overlay verificável**, `.ci/completion/cain-overlay.zip`, associado ao PREVIEW_MANIFEST e ao manifesto de transporte `ef7db4251dfaaf91bf6cbc0e2d3bfad8c8ad19a100d690574da351b9fc51958a`. Não confundir checkout raiz/main com instalação do candidato. A CI reconstruiu bases pinadas e overlays antes de testar. Não houve merge, tag, pacote publicado, ativação permanente ou mudança global da máquina.

## Validação

| Ambiente e escopo | Resultado |
|---|---|
| Windows/Python 3.12, wheel não editável, CAIN+Bundle |575 aprovados, 1 skip de privilégio symlink|
| Linux/Python 3.11,3.12,3.13,3.14, candidato reconstruído |574 aprovados e 2 skips exclusivos de launcher Windows por versão|
| Linux segurança/POSIX direcionado |187 aprovados,zero skips,por versão; symlink obrigatório executado|
| Linux mini-auditoria |45 aprovados por versão,com sobreposição à suíte|
| Linux produtores 3.13/3.14 |Crypto23,BR11,Stocks 15 testes; ambientes/pins separados|
| Linux exportação real Snapshot |Crypto 15,Stocks 1,BR 3 revisões; ingestão/evidência/restore offline|
| Linux exportação real Bundle |Crypto 20 entidades/12 objetos,BR 14/2,Stocks 2/0; lineage e materialização offline|
| Windows acervo populado |6 scopes;47 objetos materializados/verificados; backup SQLite/CAS,restore e revogação|
| Revisão independente |Falhas corrigidas,reprobes e vínculo manifesto/overlay/wheel/fonte/instalação aprovados|

Dois skips Linux são os launchers testados no Windows; não se omitiu gate Linux obrigatório. Contagens sobrepostas não devem ser somadas. A matriz cobre consumidor/contratos/exportadores, **não** uma revalidação dos runtimes científicos completos nem todo cruzamento possível OS×Python. Stocks Linux usa o catálogo sem a seleção opcional sobre backup local; por isso 2 entidades versus 3 no bundle Windows já preservado. Não foi enviado banco científico ao CI.

`F01_F10_MATRIX.json` liga cada achado original a evidências. Proteções de paths, autorização, conflitos, variantes raw, durabilidade, quota, evidências e dependências foram exercitadas; isso não é prova universal de segurança ou tolerância a toda falha física.

## População e cobertura

O recorte preserva 70 entidades Bundle,47 descritores recebidos, 6 referências e 231658 bytes lógicos. Crypto inclui estados/trials/attestations existentes; BR inclui claims e relato retrospectivo; Stocks conserva catálogo/seleção metadata e referências; Core 16, Ops 11, Ecosystem 6 documentos/contratos. O acervo legado acrescenta 9 publicações e 19 revisões documentais, com permissões previamente existentes.

Inventário de paths dos seis repositórios e publicações admitidas está preservado; denominador científico completo UNKNOWN. Não houve varredura indiscriminada de discos, nova previsão, liquidação, backtest, treino, trade, aposta ou promoção de métrica. Novas admissões estão registradas em ADMISSION_REQUESTS; geraçãofalse dos documentos exportados conservadoramente não é uma proibição universal inferida de licença.

## Preservação e autoria

Os sete checkouts originais mantiveram HEAD/status e hashes selecionados (`SOURCE_PRESERVATION.json`). Mudanças CAIN ocorreram em cópia isolada. Stocks recebeu somente uma fixture de portabilidade em overlay na raiz própria; Core/Ops runtime não mudaram. Preservação se baseia nos comandos,Git e hashes observados, não em auditoria de kernel. A tentativa inicial antiga de hash amplo foi interrompida sem log por read; não há alegação de zero acesso a toda classe restrita.

O CAIN produziu consultas/regras e gerações registradas; o Codex produziu código,harness,oráculos e este relatório. Persistência de resultados não é aprendizado. Modelos não decidem validade científica nem autorizam operações. A interpretação não apoiada e os resultados negativos foram conservados.

## Reconstrução e retomada sem chat

Bases dos sete projetos,arquivos alterados,patch,overlay,wheel,dependências,corpus,policy e runner estão em CANDIDATE_MANIFEST.json. `overlay.zip` preserva bytes inclusive CRLF; cenários/rubricas originais são byte-idênticos. Reconstrução CAIN foi ensaiada em `reconstruction-check`:

```powershell
& 'C:/CAIN/work/supply-final-20260912/venv/Scripts/python.exe' 'C:/CAIN/work/supply-final-20260912/restore_working_tree.py' --destination 'C:/CAIN/work/NOVO_DESTINO'
```

O destino deve ser novo. O script reconstrói CAIN; a fixture Stocks está separada em `C:/STOCKS/work/supply-portability-20260912/tools/test_cain_bundle_selection.py` e `ci-kit/stocks-overlay.zip`. `ci-kit/prepare_ci.py` e `restore_candidate.py` reconstroem os checkouts para Linux a partir das bases/overlays declarados. Não usar reset/clean sobre fontes originais.

Runner: `& 'C:/CAIN/work/supply-final-20260912/venv/Scripts/python.exe' 'C:/CAIN/work/supply-final-20260912/runner.py' --config 'C:/CAIN/work/supply-final-20260912/UTILITY_PROTOCOL.json' --state 'C:/CAIN/work/supply-final-20260912/utility-release'`. A execução já terminou; retomada valida os 18 resultados. Config/código/policy diferentes exigem pasta nova e revalidação. Nenhum trabalho continua em background após esta entrega.

Artefatos principais: BASELINE/SESSION_BASELINE; SOURCE_INVENTORY e LEGACY_SOURCE_INVENTORY; POPULATION_PLAN/LEDGER; KNOWLEDGE_COVERAGE; UTILITY_PROTOCOL/RESULTS; DERIVED_VALIDATION; FINDINGS_AND_REMEDIATION; GATES; CHECKPOINT; USER_ACCEPTANCE. Evidências novas: FINAL_VERIFICATION,REMOTE_FINAL_VERIFICATION,MODEL_VERIFICATION,WEB_REHEARSAL,MANUAL_GUIDE_REHEARSAL,diagnostic-restore,derived-evaluation-r2,linux-final-*. Revisão independente original em `C:/CAIN/work/supply-review-20260912/DELIVERY_REVIEW.md`.

Não resta defeito reproduzível aberto no escopo revisado. Uma revisão humana pode agora decidir o congelamento **da Supply delimitada**, conservando as limitações de conteúdo/modelo e a derivação experimental desligada. A entrega não autoriza freeze administrativo nem implantação. Para ampliar o produto, decidir admissões específicas e avaliar benefício semântico em protocolo próprio, sem tratar esta fundação como lucro ou aprendizado validado.

## Gates separados

```json
{
  "CANDIDATE_IDENTITY_STATUS": "PASS",
  "LEGACY_COMPATIBILITY_STATUS": "PASS",
  "CONTRACT_AND_PROFILE_STATUS": "PASS",
  "WINDOWS_STATUS": "PASS",
  "LINUX_STATUS": "PASS",
  "PYTHON_MATRIX_STATUS": "PASS",
  "F01_F10_STATUS_BY_PLATFORM": {
    "Windows": "PASS within executed regression cases; symlink privilege case not executed here",
    "Linux": "PASS within executed remediations and POSIX probes; required symlink executed; F09 documentation review is platform-neutral"
  },
  "INVENTORY_STATUS": "PARTIAL_JUSTIFIED",
  "POPULATION_STATUS_BY_SOURCE_AND_CLASS": {
    "brasileirao": "PARTIAL_JUSTIFIED",
    "core": "PARTIAL_JUSTIFIED",
    "crypto": "PARTIAL_JUSTIFIED",
    "ecosystem": "PARTIAL_JUSTIFIED",
    "ops": "PARTIAL_JUSTIFIED",
    "stocks": "PARTIAL_JUSTIFIED"
  },
  "COVERAGE_STATUS": "PARTIAL_JUSTIFIED",
  "DETERMINISTIC_QUERY_STATUS": "PASS",
  "TEMPORAL_AND_LINEAGE_STATUS": "PASS",
  "MODEL_UTILITY_STATUS": "INCONCLUSIVE",
  "DERIVED_PIPELINE_STATUS": "PASS",
  "DERIVED_BENEFIT_STATUS": "INCONCLUSIVE",
  "SECURITY_AND_REVOCATION_STATUS": "PASS",
  "BACKUP_RESTORE_OFFLINE_STATUS": "PASS",
  "WHEEL_INSTALL_STATUS": "PASS",
  "REMOTE_CI_STATUS": "PASS",
  "INDEPENDENT_REVIEW_STATUS": "PASS",
  "SCIENTIFIC_INTEGRITY_STATUS": "PASS",
  "READY_FOR_FREEZE_REVIEW": "PASS",
  "USER_PREVIEW_STATUS": "LIMITED_IN_STAGING"
}
```

Os limites de interpretação de cada gate constam de GATES.json. PASS de pipeline derivado refere-se ao mecanismo testado, não à geração negada nos seis bundles reais; PASS de integridade científica refere-se à evidência observável declarada acima.


## Atualização Git e pastas

O código final foi materializado no checkout `C:/CAIN/work/supply-publish-20260912`, branch `validation/cain-supply-completion-20260912`. As descrições de raiz baseline acima registram a etapa anterior. Leia `C:/CAIN/entregas/supply-20260912/LEIA_PRIMEIRO.md`; `GIT_DELIVERY.json` nessa pasta registra o commit e a conferência remota. Os dados e evidências locais permanecem em `C:/CAIN/work/supply-final-20260912`. Nenhuma instância ativa foi modificada.
