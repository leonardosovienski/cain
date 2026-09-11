# Cain 0.4.5 — dossiê de pesquisa

Registro histórico. A instalação do Ollama e as capacidades então pendentes foram
tratadas na [entrega 0.4.6](DELIVERY_046.md); os limites abaixo descrevem 0.4.5.

## Uso

Na interface local, abra **Pesquisa · L0 Historian**, escolha `crypto`, `stocks`
ou `brasileirao` e use **Dossiê: relações, datas e lacunas**. A identidade da
fonte é opcional. O dossiê usa esses dois filtros; estado/texto pertencem à
consulta anterior e não filtram a inspeção.

Abra **Navegar pelas relações e fontes** para expandir cada revisão e seu conteúdo.
As seções adicionais mostram datas, lacunas, grafo explícito, cobertura e métricas.
Para comparar, informe identidade da fonte e ambas as revisões. Elas precisam
existir no mesmo namespace admitido. Escolher origem/destino não seleciona a
revisão cientificamente correta. Diferença de estado não prova contradição.

```powershell
C:\CAIN\CAIN_RESEARCH.cmd --collection crypto inspect --source-id H6
C:\CAIN\CAIN_RESEARCH.cmd --collection stocks inspect
C:\CAIN\CAIN_RESEARCH.cmd --collection brasileirao inspect
```

API: `POST /research/inspect`, com `user_id`, `project_id`, `collection`,
`source_id`, `domain`, `before`, `after`. Todos opcionais exceto as dependências
da comparação. Não aceita campos extras. Usuário/projeto continuam seleção de
escopo local; o serviço não deve ser exposto como autenticação remota.

## Alteração

Grafo de proveniência, linha do tempo, comparação de campos e suporte entre
revisões, achados estruturais e diagnóstico de consulta. Não há extração de
entidades, afirmações novas, rede, inferência ou novas dependências.
O limite é 2.000 revisões e 1 MB de resultado; excesso é erro explícito, sem corte.
Cada resultado usa uma transação de leitura e recusa mudança de política durante
a inspeção. Não grava o conteúdo do dossiê no histórico de consultas.

Novo módulo `src/cain/research/inspection.py`, adaptadores CLI/API e controles
na interface. O contrato ResearchSnapshotV1, a projeção e as fontes não mudaram.

## Validação desta rodada

- Suíte completa intermediária: 387 aprovados, um skip Windows; depois dois
  testes adicionais de limites aprovados (oito casos novos ao todo).
- Ruff aprovado; wheel instalado e verificado offline em ambiente vazio, fora
  do checkout; versão e assets conferidos; `pip check` aprovado.
- Instalação principal atualizada por wheel para 0.4.5, serviço reiniciado.
- Interface real: dossiês Crypto/Stocks/Brasileirão mostram 15/1/3 revisões.
- `tools/verify_research_inspection.py` executado com Python instalado e `-I`:
  cópia SQLite reaberta com todas as raízes dos produtores inexistentes;
  igualdade de IDs/estados com consulta anterior, hashes de todos os conteúdos
  e usuário sem permissão verificados. Não há mudança de ranking/modelo/memória.
- Grafos reais: 31/5/11 nós e 60/4/12 relações, respectivamente. Referências em
  publicações diferentes podem repetir conteúdo; contagens não são ensaios.
- Comparação adversarial de revisões, ciclos e fusos horários usa fixtures;
  os três acervos reais não fornecem um par de revisões da mesma identidade.

Recibo local em `C:\CAIN\entregas\0.4.5\installed-inspection\report.json`.
Backup anterior em `C:\CAIN\entregas\0.4.5\before-backup`. Mantém o procedimento
de restauração 0.4.4; não houve migração de schema nesta rodada.
Wheel final: `final\cain_research-0.4.5-py3-none-any.whl`, SHA-256
`71b47f0421037e25b284fa446f26e6b34c043a6d6c69a11733ba0ee69b17c18c`.
O wheel intermediário na raiz de `entregas\0.4.5` é histórico e foi substituído
pela revisão visual com quebra de identificadores longos.

Primeira CI publicada aprovada nas três versões Python:
[execução 34625953228](https://github.com/leonardosovienski/cain/actions/runs/34625953228).
CI final também aprovada em Python 3.11, 3.12 e 3.13:
[execução 34626131488](https://github.com/leonardosovienski/cain/actions/runs/34626131488).
Código instalado: `89da45975892d31b7e28750c1a0b4bc25ec160e3`; os 42 arquivos
do pacote foram comparados byte a byte com wheel final e checkout isolado.
Recibo: `C:\CAIN\entregas\0.4.5\installed-code-receipt.json`.
Após reinício, `/health` informou 0.4.5. A interface foi reaberta e o dossiê
novamente consultado; largura do resultado e do conteúdo ambas 437 pixels
no viewport de revisão, sem transbordamento horizontal.

## Continuidade e limites

Trabalho isolado em `C:\CAIN\work\research-capabilities-20260911`, branch
`feature/research-capabilities-20260911`, base `f6a7a7a`. O checkout principal
`C:\CAIN\projeto` contém mudanças concorrentes de arquitetura; não foram
incorporadas, revertidas ou validadas neste wheel. Os produtores não foram editados.
Usar esta branch para retomar este lote; integrar as mudanças concorrentes por
diff, sem trocar ou sobrescrever a árvore principal.

[Inventário ampliado](research/capability-inventory-20260911.md) distingue
implementação, lacunas reais, dependências e limites de autorização. Ainda
faltam recursos dos rivais: multimodal, streaming, MCP geral, workflows amplos,
extração semântica e debates, entre outros. Este lote não conclui paridade total.
O executável Ollama configurado não existe. Nenhuma inferência real, previsão,
aposta ou avaliação econômica foi executada. Aceite em [ADR 0014](adr/0014-research-inspection.md).
