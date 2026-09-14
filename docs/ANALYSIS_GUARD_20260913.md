# Proteção de análise e continuidade — 13/09/2026

Entrega posterior à auditoria de cobertura 0.4.12. O código está no checkout `C:/CAIN/projeto`, branch main. A instalação principal `C:/CAIN/.venv` permanece na entrega anterior: o hash do módulo analysis.py instalado difere do checkout. Não houve instalação nesta publicação.

## Mudança

As etapas support, challenge e synthesis agora se abstêm de gerar interpretação livre quando recebem uma linha de tabela sem os rótulos das colunas. Preservam fatos e citações, retornam `abstained_unlabelled_table` e não chamam o modelo. A abstenção evita atribuir significado inventado às colunas; não recupera os cabeçalhos ausentes nem demonstra que o projeto completo carece de informação.

Para os demais trechos, o contexto inclui identidade da fonte, localização, revisão e relógios científicos. O prompt distingue hipótese de resultado, estado recebido de estado atual verificado e informação ausente no recorte de informação ausente no produtor. Isso não certifica semanticamente a resposta. Prompt `addressable-review/6`; protocolo `research-workflow/10`, impedindo retomar execução antiga sob regras novas.

## Evidência e limites

A auditoria administrativa `tools/verify_project_coverage.py` também evoluiu para `project-coverage/2`: registra publicação, escopo, revisão, horários de exportação/recebimento separados dos relógios científicos, hashes atuais/recebidos, tentativas recentes de importação e fontes esperadas fornecidas pelo administrador. Mantém versões históricas e distingue arquivo ausente, divergente, não fornecido, ilegível ou acima do limite. Esses diagnósticos não autorizam novas fontes nem certificam a verdade atual do produtor.

Evidências locais preservadas em `C:/CAIN/work/knowledge-integration-20260913`: baseline, before, after, final, auditoria e logs. A execução `final/workflows.json` possui hashes iguais aos módulos analysis.py e workflows.py desta entrega. Nela, o caso Brasileirão completou seis etapas, com abstenção nas três etapas de análise e zero chamadas ao modelo. O arquivo consultado estava incompleto para Crypto e não continha resultado final de Stocks; não declarar aprovação dos três casos com base nesse arquivo.

Os 54 testes focados de `tests-guard.log` passaram após a proteção. A execução anterior de 681 testes precede essa última alteração. A suíte desta publicação passou com **688 testes, 1 skip e 2 avisos** em `tests-publication.log`. As mudanças posteriores da auditoria de cobertura também passaram nos **7 testes** de `tests/test_project_coverage.py`, executados separadamente porque foram alterados durante a suíte. Ruff passou sobre o checkout atualizado.

## Para retomar sem o chat

1. Ler CONTINUIDADE.md, ESTADO_DO_PROJETO.md e docs/COBERTURA_PROJETOS_20260913.md.
2. Conferir main local/remota e o ambiente instalado antes de promover um novo wheel. Esta publicação Git não atualiza automaticamente a instalação.
3. Completar a avaliação real de Crypto/Stocks com os hashes finais e preservar os resultados anteriores; não chamar abstenção de compreensão científica.
4. Para ampliar cobertura, exportar conteúdo e cabeçalhos/contexto dos produtores dentro das políticas aplicáveis. Os seis acervos recebidos são recortes; referências não equivalem a conteúdo legível. Os Bundles adicionais continuam restritos ao QA.
5. Preservar bancos/configurações do usuário e não restaurar backups antigos sobre o estado atual. Nenhum repositório produtor integra este commit.
