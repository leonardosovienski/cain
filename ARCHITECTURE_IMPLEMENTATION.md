# Implementação arquitetural — 2026-09-11

Esta alteração complementa a entrega 0.4.4 existente, preservando os três produtores, backup e configuração de import roots implementados em outra tarefa.

As factories de provedores estão em `cain.providers`. API e CLI de pesquisa não importam a CLI principal; nomes antigos continuam reexportados para compatibilidade. A configuração fake continua independente de modelo instalado.

A importação exige um grant para o escopo antes de abrir o arquivo de publicação. Histórico de consultas registra publicações de origem; a listagem reavalia permissões e oculta filtros/perguntas derivados quando as fontes foram revogadas. Reabrir uma consulta remove metadados internos antes de executar novamente os filtros. Entradas antigas sem vínculo suficiente são tratadas conservadoramente na listagem. Não há migração destrutiva nem escrita nos produtores.

Validação delimitada: 82 testes aprovados e um skip já previsto pela plataforma, abrangendo transporte, raízes, backup, história, revogação e factories. Dois avisos de depreciação vêm do ambiente de teste FastAPI/Starlette. Ruff aprovado. Testes usam bases e modelos sintéticos; nenhum modelo local real foi iniciado ou substituído.

Rollback de código não remove o histórico; preservar o banco e o contrato V1. A revogação de acesso continua independente de permissões declaradas pelo pacote recebido.
