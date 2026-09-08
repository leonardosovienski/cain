# ADR-0012 — Preferências explícitas e memória na versão funcional

- Status: Provisório — implementado experimentalmente
- Data: 2026-09-07
- Faixa: B
- Relacionados: ADR-0006/0007/0008 (textos não fornecidos), ADR-0009/0010/0011

## Contexto

O usuário autorizou evoluir o esqueleto para respostas reais, adaptação do perfil,
memória e agentes funcionais. A primeira versão apenas armazenava interações.
A restrição sem ajuste de pesos e as decisões de escopo do núcleo são preservadas.

## Decisão provisória

Implementar atualização conservadora por declaração explícita em português para
formato, extensão e idioma. Manter personalidade estável separada do UserModel.
Registrar procedência, correção e remoção por revisão; a evidência atual prevalece.
Aplicar a preferência antes da primeira resposta que deve utilizá-la.

Entrada e perfil são persistidos em transação, com verificação da revisão esperada.
`IdentityStore.apply_signal` acrescenta essa operação à porta da implementação;
o contrato originalmente recebido em ADR-0009 não fornecia transação composta.
O índice permanece derivado e reconstruível.

Recuperar quantidade limitada de episódios do usuário, excluindo episódios de
preferências e a entrada da decisão atual. Remover uma preferência não elimina
o histórico bruto; tombstones e filtros impedem seu uso como preferência vigente.

## Justificativa e alternativas

Regras explícitas tornam cada mudança auditável e testável sem usar o mesmo LLM
como extrator e avaliador. Inferência livre por LLM e feedback implícito foram
adiados porque exigem critérios próprios de evidência, erro e correção. Ausência
de adaptação fica preservada no histórico como implementação inicial de controle.

O recorte se apoia nas alternativas discutidas em
`../research/posicionamento.md`; não estabelece novidade ou superioridade empírica.

## Consequências e validação

A versão aprende somente declarações reconhecidas; não compreende toda paráfrase.
Preferências antigas podem permanecer nos dados brutos de auditoria. A qualidade
da resposta depende do LLM e requer inspeção independente do estado persistido.

Testes cobrem primeira resposta, reabertura, conflitos, negação, citações,
isolamento, remoção, reconstrução e transação. A demonstração com modelo real
registra contexto, estado e resposta. Ela não aceita ADR-0010 nem substitui
validação de construto e comparação controlada.

## Extensão v0.3, ainda provisória

O usuário autorizou a implementação do recorte recomendado após pesquisa de
alternativas. A identidade agora admite overlays por projeto, sessão e turno,
com expiração e precedência explícita, preservando os dados globais anteriores.
A criação de perfil é atômica por `create_if_absent`; consultar uma identidade
não pode substituir uma atualização concorrente. As decisões científicas deste
ADR e dos anexos permanecem provisórias.

A busca híbrida e seu cache são derivados. A UI oferece inspeção, controle e
feedback categorizado sem atualizar preferências a partir da avaliação de uma
resposta. Documentos recuperados continuam sendo dados, não instruções para alterar
identidade. Ver [memória por escopo](../architecture/memoria-por-escopo-v03.md),
[busca híbrida](../architecture/busca-hibrida-v03.md) e [relatório v0.3](../../RELATORIO_V03.md).
