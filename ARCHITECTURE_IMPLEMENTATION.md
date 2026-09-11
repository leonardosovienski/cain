# Implementação arquitetural — 2026-09-11

Esta alteração complementa a entrega 0.4.4 existente, preservando os três produtores, backup e configuração de import roots implementados em outra tarefa.

As factories de provedores estão em `cain.providers`. API e CLI de pesquisa não importam a CLI principal; nomes antigos continuam reexportados para compatibilidade. A configuração fake continua independente de modelo instalado.

A importação exige um grant para o escopo antes de abrir o arquivo de publicação. Histórico de consultas registra publicações de origem; a listagem reavalia permissões e oculta filtros/perguntas derivados quando as fontes foram revogadas. Reabrir uma consulta remove metadados internos antes de executar novamente os filtros. Entradas antigas sem vínculo suficiente são tratadas conservadoramente na listagem. Não há migração destrutiva nem escrita nos produtores.

Validação delimitada: 82 testes aprovados e um skip já previsto pela plataforma, abrangendo transporte, raízes, backup, história, revogação e factories. Dois avisos de depreciação vêm do ambiente de teste FastAPI/Starlette. Ruff aprovado. Testes usam bases e modelos sintéticos; nenhum modelo local real foi iniciado ou substituído.

Rollback de código não remove o histórico; preservar o banco e o contrato V1. A revogação de acesso continua independente de permissões declaradas pelo pacote recebido.

A matriz Python 3.11/3.12/3.13 e a instalação offline do wheel 0.4.5 passaram. O intercâmbio final usou exportador 1.0.1/contrato 1.0.1 em outro ambiente e leitor CAIN 1.0.0: importação, duplicata, filtro, referências, backup/restore e origem ausente passaram sem modelos ou predictors instalados.

## Entrega arquitetural publicada — 11/09/2026

Versão **0.4.5** publicada: [release e artefatos](https://github.com/leonardosovienski/cain/releases/tag/v0.4.5). [CI de engenharia aprovada](https://github.com/leonardosovienski/cain/actions/runs/34628951943) para a fonte `37cdc604d4c3bbb66684c018c76a4ea38713ee2a`. Consulte [ARCHITECTURE_IMPLEMENTATION.md](ARCHITECTURE_IMPLEMENTATION.md) para comportamento, migração e limites. Este registro atualiza a entrega de software; estados científicos e registros datados abaixo conservam sua autoridade e contexto histórico.
