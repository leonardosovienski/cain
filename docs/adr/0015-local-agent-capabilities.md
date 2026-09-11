# ADR 0015 — Fechamento das capacidades locais pendentes

11/09/2026. O usuário reiterou a implementação de todos os blocos técnicos
pendentes. Autoriza instalar runtime/modelos locais e executar os testes;
permanecem os limites sobre capital, apostas e autoridade dos produtores.

Lotes: streaming NDJSON e imagem local; busca por relevância; entidades e
relações propostas com citações; debate de suporte/crítica/síntese; workflows
com passos duráveis, retomada e métricas; MCP stdio com escopo fixado no processo.
Não copiar código dos rivais nem substituir os produtores por calculadoras
financeiras. Referências: documentação Ollama /api/generate e /api/chat;
MCP 2025-06-18 lifecycle, tools e stdio.

Aceite prévio: terminal done obrigatório, truncamento e desconexão explícitos;
imagens limitadas em bytes/pixels e inferência somente loopback; citações exatas,
entidades presentes no trecho e propostas sem promoção a fato; revogação antes
e depois da inferência e em toda leitura de resultado; passos concluídos não
reexecutados, estado/corpus/prompt/modelo fixados; erro não conta como sucesso;
MCP sem execução arbitrária, ferramentas enumeradas e sem troca de escopo por
argumento; casos PT/EN e imagem sintética identificados como desenvolvimento.

Baseline: consulta literal + explicação extrativa existentes. Comparar mesmos
IDs/fontes e casos PT/EN; medir suporte de citações e ausência de evidência.
Modelos pequenos não são presumidos superiores. Nenhuma vitória sem avaliação
independente. Testar inferência real separadamente de mocks de transporte.

Workflows executam somente ferramentas de leitura e geração propostas. Cada
passo tem recibo transacional; falha após chamada externa e antes do recibo
permanece incerta e exige recuperação explícita, sem alegar exactly-once.
MCP é para cliente local autorizado: não registrar em cliente remoto nem
liberar publicações marcadas como não divulgáveis a serviços externos.
