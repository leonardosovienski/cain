# ADR 0016 — Integração e análise com trechos endereçáveis

Pedido de 11/09/2026: executar as pendências da entrega 0.4.6. Integrar a branch
arquitetural preservando factories, permissões e histórico; extrair campos JSON
e tabelas literalmente, sem exigir inferência; usar IDs curtos para selecionar
citações no debate, resolvendo texto e offsets no consumidor. Interpretação
continua proposta, nunca novo estado científico.

Antes de avaliar: congelar casos novos, separados dos seis casos de desenvolvimento
anteriores. Avaliar identidade, referência, campo/valor, ausência de suporte,
permissões e injeção; variantes PT/EN são pareadas. Não chamar uma avaliação
automática elaborada pelo implementador de avaliação humana independente.
Não ajustar os casos nem redefinir acertos após ver resultados. Usar inferência
local real e manter falhas nos recibos. Comparação semântica independente ampla
exige avaliadores/dados externos, não um segundo rótulo para testes próprios.

Aceite: H6 deve preservar estado/trial separados; strings escapadas não podem
ganhar citações falsas; tabela não pode juntar células de linhas distintas;
citação do debate deve resolver para texto recebido, com rechecagem de permissão;
workflow novo fixa protocolo /3 e jobs antigos não avançam com prompts novos.
Backup, distribuição, interface, CI e correspondência local/remota obrigatórios.

Revisão da implementação: /3 foi preservado nos primeiros recibos. O protocolo
final /4 usa addressable-review/2, sem classificar uma limitação da fonte como
abstenção do assistente; ausência de evidência ainda exige abstenção. Casos e
critérios congelados não foram alterados.

Propostas de trading, apostas, alteração científica dos produtores e fontes pagas
permanecem fora do mandato original. Trocar frameworks sem benefício mensurado
não é requisito de paridade; as capacidades são verificadas no Cain existente.
