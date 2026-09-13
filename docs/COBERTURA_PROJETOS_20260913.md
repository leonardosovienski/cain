# Cobertura dos projetos conectados — 13/09/2026

**Conclusão: o CAIN não recebe os projetos inteiros.** A recuperação do conteúdo conectado passou; as conexões entregam recortes Snapshot e metadados/artefatos Bundle específicos. A versão 0.4.12 acrescenta um diagnóstico conjunto à API, CLI e interface, para não confundir esses conceitos.

## Acervo principal observado

| Projeto | Snapshot principal | Bundle no CAIN principal | Inventário do checkout atual |
|---|---|---|---|
| Crypto | 15 revisões de registros, oriundas de dois arquivos | Nenhum | 3.247 arquivos versionados |
| Stocks | Uma revisão de status de um arquivo; outro acervo preserva uma publicação adicional | Um pacote, duas entidades, dois artefatos somente referenciados | 1.680 arquivos versionados |
| Brasileirão | Três revisões de registros de um arquivo | Nenhum | 2.537 arquivos versionados |

O acervo `heterogeneous` repete quatro registros selecionados de Stocks/Brasileirão. Não somar esses registros como pesquisas independentes. As quantidades de arquivos vêm de `git ls-files`; não incluem todos os dados não versionados e não medem compreensão do modelo. Mesmo os arquivos declarados podem estar representados apenas por trechos.

Arquivos declarados no conteúdo recebido: Crypto — `charters/scientific_state.json` e `docs/EVIDENCE_REGISTRY.md`; Stocks — `STOCKS_CURRENT_STATE.md` e `docs/engineering/2026-09-11-architecture/evidence/real-v020.json`; Brasileirão — `docs/EVIDENCE_REGISTRY.md`. Todo o restante fica fora dessa declaração. A auditoria encontrou uma versão histórica de `STOCKS_CURRENT_STATE.md` diferente do arquivo atual, além de uma versão coincidente; isso não autoriza substituir ou apagar a anterior.

**Retificação do relatório 0.4.11:** a expressão “dois Bundles” confundia duas entidades com pacotes. O acervo `stocks-main-bundle` contém um pacote e duas entidades na auditoria atual.

## O que foi testado

A ferramenta `tools/verify_project_coverage.py` percorreu os seis acervos configurados, paginou todos os 24 registros disponíveis entre eles (há sobreposição), recuperou cada identidade exata por consulta e busca, e resolveu suas referências. Para Bundle, conferiu as duas entidades, dois artefatos, três evidências e três relações. Um usuário sem concessão recebeu acervos vazios. Nenhuma inferência foi usada para aprovar contagens ou hashes.

A auditoria foi executada sobre cópias dos bancos, com a política preservada. Uma primeira tentativa concorrente com o workflow encontrou bloqueio de SQLite; o auditor foi separado em outra cópia e passou. Isso é uma correção do ensaio, não evidência de recuperação completa na tentativa que falhou.

Também foram validados e importados os três pacotes `bundle-v1-completion-e2e/bundle.json`, em banco e política exclusivos de QA:

| Exportação | Entidades recuperadas | Artefatos | Conteúdo materializado e hash conferido | Somente referência |
|---|---:|---:|---:|---:|
| Crypto | 20 | 12 | 12 | 0 |
| Stocks | 2 | 2 | 0 | 2 |
| Brasileirão | 14 | 5 | 2 | 3 |

A consulta de cada entidade e artefato passou. As 14 materializações coincidiram com seus hashes; os cinco artefatos somente referenciados recusaram materialização. A geração permaneceu desautorizada nos três pacotes, conforme as restrições originais. O isolamento entre usuários passou.

Esses pacotes não estão conectados à instalação principal. O teste isolado demonstra que o consumidor consegue recebê-los; não amplia a política principal nem habilita acesso aos repositórios, bancos protegidos ou conteúdos que os produtores excluíram. Todos os três manifestos declaram `completeness=partial`.

## Workflows e síntese livre

Foram executados três workflows completos de seis etapas, um por produtor: Crypto/H4, Stocks/prontidão operacional e Brasileirão/CLAIM-BR-MARKET-001. Os 18 checkpoints concluíram e foram reabertos depois pela API instalada 0.4.12. Houve nove inferências reais de redação (support/challenge/synthesis); inspect/search/extração estruturada não fizeram chamadas ao modelo. Mais três chamadas em `/research/explain` produziram seleção de trechos (`source_excerpts`), não síntese livre irrestrita.

A geração rodou com o pacote 0.4.11, Ollama 0.34.0 e qwen3.5:4b nos parâmetros existentes. Os módulos de workflow, análise, Historian, evidências e pontes foram comparados byte a byte e permanecem iguais na 0.4.12. A mudança desta entrega é o diagnóstico de cobertura; a leitura dos checkpoints foi retestada pela API 0.4.12.

**Conclusão técnica não é aprovação semântica.** A revisão das redações identificou:

- Crypto: estado e trial preservados, mas a expressão “status atual” pode ultrapassar o que um snapshot congelado atesta. Resultado parcial.
- Stocks: a etapa support diz que a conclusão decorre “exclusivamente” da ausência de dados; essa atribuição é mais forte que o trecho disponível. Resultado parcial.
- Brasileirão: support/challenge/synthesis tratam a descrição de uma hipótese (“Model has incremental information…”) como informação estabelecida, mesmo com estado bloqueado e nenhuma comparação executada. **Falha semântica**. Citações válidas não corrigem essa interpretação.

Esses resultados estão em `semantic-review.json`. Não houve alteração dos produtores, das hipóteses ou das restrições de geração para fazer o teste passar.

## Correção do diagnóstico

O comando `cain research ... coverage` preserva os campos anteriores de Snapshot e acrescenta contagens separadas para Bundle, arquivos declarados, permissões de geração e disponibilidade dos artefatos. A API oferece `POST /research/coverage`, e a interface inclui **Cobertura do acervo** no painel Pesquisa.

O diagnóstico não declara cobertura integral do repositório. Também informa que os workflows de seis etapas usam Snapshot; a consulta de metadados Bundle é separada. Permissões e integridade continuam verificadas, com escopo consistente e limite explícito de tamanho da resposta. As regressões cobrem acervos somente Bundle, mistura das duas pontes, duplicação, revogação, isolamento, corrupção, API e CLI.

## Reprodução e entrega

Recibos: `C:/CAIN/work/coverage-projects-20260913`. `coverage-audit.json` contém inventários e recuperação completa do acervo configurado; `bundle-candidates/report.json` contém as três importações isoladas; `full-workflows.json` preserva cada etapa e explicação, incluindo falhas se houver. Os diretórios `baseline`, `isolated`, `audit` e `bundle-candidates` mantêm os ensaios separados.

Para repetir o auditor, fornecer uma cópia consistente do banco com seu diretório `research-objects` e um JSON com `projects` (domain/checkout) e `bundles` (manifestos explicitamente selecionados):

```text
python tools/verify_project_coverage.py --db COPIA/research.db --policy POLICY.json --inventory producer-inventory.json --output coverage-audit.json
```

Versão instalada **0.4.12**, código `5364c3b1de5d01c1cf6747b9eed52e562e1a63cd`; wheel SHA256 `20bf092380eb9f2a62fee9cf19975dd3586766309b9c99d0c00f60b0edea73f9`. Suíte completa: **680 aprovados, 1 skip Windows e 2 avisos**. Ruff, sintaxe JavaScript, instalação offline, pip check e comparação dos **62 arquivos** aprovados. API principal nos seis acervos, CLI e botão **Cobertura do acervo** verificados. A tela mostrou corretamente Crypto com 2 publicações/15 revisões e Stocks Bundle com 1 pacote/2 entidades/2 referências sem conteúdo recebido.

Os bancos principais estão íntegros, com todas as linhas preexistentes preservadas. Configurações, política, atalhos e dependências de terceiros não mudaram. Os HEADs e estados Git dos três produtores permaneceram iguais. Backup da 0.4.11 e dos bancos em `baseline`; ver `preservation.json`. Publicação local/remota em `git-publication.json`; resultado da CI da referência final em `ci-final.json`, separado do pacote e da avaliação semântica.

A cobertura de importação/recuperação e a validade de citações não comprovam aprendizado, compreensão integral, correção científica, lucro ou prontidão operacional dos produtores.
