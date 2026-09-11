# ADR 0013 — Três produtores e recuperação completa

Status: aceito para validação de engenharia em 11/09/2026.

O mandato atual amplia os exemplos documentais Stocks/Brasileirão para exportadores
reais dos produtores. Supersede somente essa restrição do piloto histórico; mantém
L0, fontes admitidas e ausência de autoridade científica/financeira.
Uma raiz única obriga copiar publicações entre projetos ou admitir uma raiz excessiva.
A política v2 associa cada escopo a uma raiz; políticas v1 continuam suportadas.
Não se alteram bancos, ambientes ou contratos científicos dos produtores.

A auditoria 0.4.2 identificou que backup SQLite sozinho não contém knowledge/.
O comando administrativo archive preserva catálogo consistente e arquivos imutáveis
por hash, além de research e política. Restore só escreve destino novo e confirma
conclusão por marcador; falha deixa diretório incompleto, sem anunciar sucesso.
O manifesto garante integridade observável, não autentica um atacante que o reescreva.
Backup externo, criptografia e falha física do host não são certificados.

Alternativas rejeitadas: raiz C:\; juntar bancos; instalar runtime científico no Cain;
framework de agentes/grafo sem avaliação de benefício. A configuração v2 exige 0.4.4;
rollback para 0.4.3 requer restaurar a política v1 preservada, mantendo os bancos.
Fonte da escolha e critérios: ../research/market-comparison-20260911.md.
