# Diagnóstico de partida e retomada — 12/09/2026

## 1. Mapa do estado atual

A rodada solicitada em CAIN_DIAGNOSTICO_PARTIDA_EXECUTAR.md foi encerrada com diagnóstico e escolha do primeiro trabalho. Não houve implementação, nova inferência, experimento científico, implantação ou consulta nova pela interface. O pedido posterior autorizou pull, atualização documental, commit e push para preservar a retomada antes de apagar o chat. Essa publicação documental não executa o caso escolhido.

### Referência de partida

- Checkout de entrega: C:/CAIN/work/supply-publish-20260912, branch validation/cain-supply-completion-20260912. HEAD inicial 895613dc8aaebe3c9f78764bec0e09e059f01e42, limpo e igual ao remoto. Pull --ff-only confirmou Already up to date antes da edição. O SHA final fica no Git e no recibo local desta entrega, evitando autorreferência no commit.
- Candidato Supply: d00bbc6fb910b3c51be6720d21012f4655258468adb7d7335451974929c58752. Código instalado: 7da108d0172b7ccc2675404b7dbf0b8a21ad248ee814ea14f199225003d23861. Ambiente C:/CAIN/work/supply-final-20260912/venv, Windows/Python 3.12. O hash agregado instalado e os seis arquivos de dependências declarados coincidiram com CANDIDATE_MANIFEST.json. Os 16 changed_files, a política Bundle, o runner e o protocolo também coincidiram.
- Instalação principal: C:/CAIN/.venv, recibo de commit 86c38f8a333f278084adac3abc2ebe40c48b616c. Cinquenta arquivos corresponderam ao commit com normalização LF; isso não foi comparação byte a byte do wheel. Não é a instalação Supply. Não havia listener observado nas portas 8877, 8889 e 11439; não se inferiu funcionamento atual pela interface.
- A falha Linux do candidato anterior 74da061d... pertence à referência research-bundle-v1. No Supply posterior, os XML linux-final-3.11 a linux-final-3.14 confirmaram 574 passes, dois skips, zero erros/falhas por versão. São execuções anteriores documentadas, não reexecuções deste diagnóstico. O recibo de publicação anterior liga a validação ao runtime f1f1f5632fe5b6856c31abf6d96c4f0af5780004; commits documentais não constituem novo runtime testado.

Bases dos fornecedores conferidas limpas e iguais às branches remotas: Cripto 97d60222d14ff211bfd415fff374d0751d5ac235; Stocks a3d570fd33749ad62bdb4735bbc24b1ecd421e38; Brasileirão 5efb4716d4805e37e0aa09b09dcdc52022cae039; Core bff0a548998d7db1dbaad346465771553b0cf4c9; Ops 4392782b231364a9394dae04a57cad2c0bf73ef1; Ecosystem a9f6594c840482419d6c310f373813e0e71f17d0. A inspeção não cobriu todos os worktrees históricos e não autoriza limpar alterações deles.

### Capacidades e fontes

| Capacidade | Planejada | Implementada | Testada | Disponibilidade |
|---|---|---|---|---|
| Receber e preservar Snapshot/Bundle | sim | sim, inspecionada | sim, documentada | parcial, staging preparado |
| Consultar registros/evidências/relações | sim | sim | sim, CLI/API e web Snapshot documentadas | parcial, acervos diferentes |
| Proveniência e restore offline | sim | sim | sim, recibos e publicação conferida no backup | operação atual não verificada |
| Explicação com citação literal | sim | sim | parcial, inferência anterior | provider temporário encerrado |
| Fidelidade semântica do caso H4 | sim | parcial, gerador existente | não verificado para H4 | não verificado |
| Conteúdo de objetos Bundle na explicação web | parcial | parcial, contexto factual não abre objetos | não verificado ponta a ponta | desnecessário ao caso Snapshot |

Os seis bundles exatos de POPULATION_PLAN.json foram lidos e suas identidades coincidiram com o plano. Não confundir pastas antigas chamadas final-e2e com esses bundles.

| Fonte | Conteúdo e recebimento | Uso e limites |
|---|---|---|
| Cripto | Bundle: charter, trials, atestados; 20 entidades e 12 artefatos. Snapshot separado: charter e registro documental | Bundle nega geração; Snapshot tem autorização específica de geração local. Datasets exatos não admitidos |
| Stocks | Três entidades de catálogo/seleção e três referências, zero objetos; relatório em Snapshot separado | Referência não é preço recebido; seleção desta exportação não prova input histórico |
| Brasileirão | 14 entidades, dois objetos, três referências; registro de alegações e replay | Retrospectivo; não comprova previsão prospectiva, PIT ou settlement |
| Core | 16 documentos recebidos | Metodologia e compatibilidade; documentação não certifica trial |
| Ops | 11 documentos recebidos | Contratos operacionais, não recibos reais de jobs; não precisa executar Ops neste caso |
| Ecosystem | Seis documentos recebidos, incluindo Snapshot/Bundle | Contrato de transporte; external não concede acesso nem fetch |

Os seis bundles originais negam geração/divulgação. A autorização Snapshot é separada. Não ampliar grants para obter um teste aprovado. A rodada suplementar 3f3b34cf... já documentou 47 chamadas sobre 33 documentos Core/Ops/Ecosystem: comparação estrutural neutra, sem demonstração de benefício semântico.

Evidências locais principais em C:/CAIN/work/supply-final-20260912: CANDIDATE_MANIFEST.json, POPULATION_PLAN.json, WEB_REHEARSAL.json, MODEL_VERIFICATION.json, model-final-backup.db, linux-final-*/full.xml e closure-real-20260912/RESULTS.json. Síntese Stocks anterior incluiu interpretação não sustentada pela fonte; não a usar como conclusão. O código relevante está em src/cain/research/{historian,service}.py e src/cain/web/app.js.

## 2. Bloqueios identificados

| Etapa/condição | Natureza e impacto | Menor verificação |
|---|---|---|
| Filtro H4 recupera charter; motivo consta em CLAIM-CR-LLM | Limitação de recuperação: pode impedir explicação apesar de conteúdo já recebido | Selecionar CLAIM-CR-LLM; verificar evidência fornecida ao gerador |
| Pergunta H4 pela web ainda não executada | Capacidade ainda não demonstrada; impede aceite do caso | Fazer pergunta exata em sessão isolada e comparar com gabarito |
| Provider local do preview encerrado | Dependência operacional, não defeito de modelo | Sessão temporária isolada com modelo existente, identidade registrada |
| Síntese Stocks anterior sem apoio integral | Defeito semântico documentado; causa não determinada, não prova falha H4 | Confrontar cada afirmação de H4; só propor correção se falhar |
| Clocks nulos e dados brutos fora do recorte | Limitação legítima; limita resposta, não impede motivo documental | Preservar UNKNOWN, sem inventar data ou recálculo |
| Antiga falha Linux e homologação/implantação geral | Fora do caminho do caso Windows | Não transformar em dependência artificial |

O diagnóstico usou arquivos e backup SQLite somente leitura, sem importar o serviço. preview.py grava USER_OBSERVATIONS.jsonl e o serviço inicializa estruturas SQLite: não repetir os scripts antigos diretamente sobre seus recibos. Não atribuir ao modelo ausência causada pelo filtro, exportação ou autorização.

## 3. Primeiro caso e ações prioritárias

Caso escolhido: explicar o encerramento de H4 sem confundir insuficiência amostral com refutação nem misturar H5. O recorte tem motivo explícito e autorização existente; evita ampliar admissões ou reconstruir ingestão. Não repete a geração Cripto anterior, que tratou de custos, nem a comparação de contagens dos 33 documentos.

Pergunta exata: “Segundo CLAIM-CR-LLM, por que H4 foi encerrada, qual amostra foi registrada e por que isso não constitui refutação estatística? Distinga H4 de H5 e cite os trechos que sustentam a resposta.”

Use Supply d00bbc6f... / instalação 7da108d0..., Windows staging, Snapshot legado crypto, usuário leo/projeto vazio. Fontes originais autorizadas: charters/scientific_state.json e docs/EVIDENCE_REGISTRY.md. A fonte HYPOTHESES.md foi consultada como corroboração; não é necessário admitir seu texto integral, que também contém passagens históricas agrupadas e ambíguas.

O gabarito factual e os identificadores completos do acervo ficam em GABARITO_LOCAL.md na entrega local C:/CAIN/entregas/diagnostico-partida-20260912-133135. Não publicar bancos, payloads recebidos ou respostas privadas. A política de origem preserva disclose=false. O resumo público informa o critério, sem republicar esses payloads.

Percurso: fonte original → Snapshot existente → recebimento → consulta CLAIM-CR-LLM na web → explicação → comparação com origem. Fonte/trecho exportado foram comparados por offsets e SHA; publicação no backup foi byte-idêntica à original. A web já demonstrou consulta/evidência/reinício em outro recorte; a explicação específica continua NÃO VERIFICADA. A simples localização de H4 ou uma citação válida não basta para passar.

| Ação | Onde | Dependência | Aceite |
|---|---|---|---|
| 1. Preparar sessão isolada com os mecanismos existentes de restore/preview | Nova área em C:/CAIN/work | Backup, ambiente/modelo existentes e política sem ampliação | Identidades, hash de publicação/trecho e isolamento de escrita conferidos |
| 2. Consultar CLAIM-CR-LLM e fazer a pergunta pela web | Pesquisa L0 Historian, crypto | Sessão e provider temporário | Registrar pergunta, evidências recuperadas, modelo e resposta |
| 3. Comparar com gabarito preparado antes | Novos recibos do caso | Resposta da ação 2 | Motivo explícito, amostra correta, ausência de refutação, distinção H4/H5 e referências que sustentem as afirmações |

Uma falha exige localizar seleção/recuperação/interpretação antes de propor implementação. Não trocar modelo por inferência. Não iniciar campanhas, scheduler, capital, merge, release ou implantação. Sucesso deste caso não homologa o produto inteiro.

Decisão: para Supply d00bbc6f... em Windows staging e no Snapshot Cripto, explicar H4 depende do charter e CLAIM-CR-LLM. Fonte → exportação → preservação está demonstrado por hashes e bytes no backup; explicação pela web não foi verificada. O próximo trabalho é verificar o uso no L0 Historian isolado com aceite factual e citações sustentadas. O ganho é demonstrar compreensão fiel da decisão, além de estados e contagens.

### Retomada sem chat

O diagnóstico está encerrado. O teste H4 não foi executado e não está rodando em background. Ao receber autorização para a próxima rodada: leia este documento, o mandato preservado e o gabarito local; confirme HEAD/branch/status e identidades atuais; execute somente as três ações acima. Não reinicie sete auditorias nem continue automaticamente o prompt histórico de remediação Linux. Preserve C:/CAIN/dados, modelos, ambientes, entregas e work/supply-final-20260912, além das fontes nas raízes próprias dos produtores. Git não é backup desses dados. Apagar o chat não autoriza apagar pastas.
