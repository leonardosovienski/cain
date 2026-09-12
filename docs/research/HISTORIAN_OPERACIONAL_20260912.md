# Correção operacional do Historian — 12/09/2026

O usuário solicitou continuar testando, corrigindo e validando até o fluxo funcionar. A atualização é baseada no código operacional 86c38f8a333f278084adac3abc2ebe40c48b616c, sem promover a arquitetura Supply inteira.

## Mudanças e motivação

A explicação Snapshot passa a selecionar trechos literais, informar os registros filtrados e rejeitar sínteses livres, mesmo com citações válidas. Referências curtas internas são resolvidas para a proveniência original. Campos textuais JSON completos e limitados acompanham os trechos quando são literais; não são truncados nem reescritos. A solução preserva contexto documental, não certifica raciocínio do modelo ou verdade científica.

A interface apresenta contexto e referências, explica abstenções e falhas em português, orienta perguntas vazias e remove resultados antigos antes de novas explicações. Histórico e revalidação de permissões continuam ativos.

O teste do wheel encontrou 13 falhas e quatro erros por arquivos de cenários ausentes na instalação. Os quatro recursos sintéticos de avaliação agora são empacotados, byte a byte conforme seus originais, e localizados via importlib.resources. A identidade das avaliações registra os bytes executados em vez de inferir um checkout vizinho. Nenhuma alteração nos protocolos ou fontes científicas dos produtores.

## Verificação

- Testes do código operacional corrigido antes do reparo de empacotamento: 455 passes, um skip.
- Primeiro wheel: 438 passes, 13 falhas, quatro erros, um skip. Resultado preservado.
- Avaliações após reparo: 28 passes.
- Wheel final instalado isoladamente, sem src no pythonpath: 457 passes, zero falhas/erros, um skip Windows de symlink. Ruff e sintaxe JavaScript passaram.
- Interface isolada: H6 com geração real, histórico preservado, fonte inexistente, pergunta vazia, excesso de contexto e modelo indisponível conferidos. Saídas inválidas recusadas; controles recuperados.

Wheel final SHA-256: 58dbc220c5eb4408d06d1abc3360a89a2e3bfb289e9f4b2515843f50cd00c89c. Versão de distribuição 0.4.7; identificar este reparo pelo Git e hash, não somente pelo número da versão.

Os testes não certificam todos os casos possíveis, Windows symlinks, Linux ou CI remota. A discrepância documental de poder n=60/n=84 não foi recalculada. Respostas e acervos privados não foram adicionados ao Git.

## Instalação e reversão

A instalação local é executada apenas após os checks acima, com wheel offline, sem reinstalar dependências. Recibos finais, confirmação do caso H6 na instalação principal, hashes de preservação e rollback ficam em C:/CAIN/entregas/historian-operational-20260912. Este documento descreve o procedimento; AFTER_INSTALL.json e o relatório final registram sua execução efetiva.

O diretório guarda cópias SQLite anteriores, configuração e atalhos, o novo wheel e o wheel operacional anterior verificado (SHA ce43f2bed45be8b191da775aa85d643453e6200d94ff0e8a0044b51b3cf18600). Reverter apenas o código com o wheel em rollback, sem restaurar automaticamente bancos que podem conter consultas posteriores.

A publicação remota não faz parte desta rodada. O aplicativo permanece local, com grants e fontes preservados. Consulta de uso gera recibos/histórico; isso não é alteração das hipóteses ou dos payloads recebidos.
