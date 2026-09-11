# ADR 0014 — Inspeção local das evidências admitidas

11/09/2026. O usuário pediu ampliar a adoção das capacidades dos rivais.
Reabrimos as decisões de adiar navegação relacional e diagnóstico: as três
integrações agora permitem perguntas concretas sobre revisões, origem e lacunas.

Implementar um dossiê determinístico com grafo de proveniência, linha do tempo,
comparação explícita de revisões, achados de qualidade e métricas locais.
Estas operações somente projetam campos já recebidos, sob a política atual.
Não extrair entidades por modelo nem inferir causalidade, validade temporal,
contradição científica ou uma revisão vencedora. Não alterar o contrato.

Aceite definido antes dos testes: relações de supersessão limitadas ao namespace;
revisões ausentes e ciclos sinalizados; datas desconhecidas preservadas; mesmo
instante com fusos distintos ordenado corretamente; mudanças de estado exibidas
sem chamá-las de contradição; usuário/projeto/acervo e revogação isolados; saída
limitada; API, CLI e interface disponíveis sem modelo ou produtor ligado.
Casos PT/EN são inspeção estrutural, não benchmark de entendimento linguístico.

Nenhuma nova dependência, serviço ou telemetria externa. Consulta única consistente
por transação, com rejeição se o arquivo de política mudar durante o trabalho.
Limites de 2.000 revisões e 1 MB de saída: exigir filtro, nunca truncar em silêncio.
O trabalho usa worktree próprio devido a alterações concorrentes no checkout.
