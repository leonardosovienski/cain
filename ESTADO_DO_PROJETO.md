> Estado final desta cópia: V8 em QA isolado no workspace; 831 testes offline, sem confirmação com modelo e sem aprovação geral. Checkout canônico continua V7; instalação principal preservada. Veja [continuação V8](docs/CONTINUACAO_V8_20260915.md). O conteúdo anterior abaixo conserva o histórico.

# Continuação corrente — 15/09/2026

V6 congelada em QA local, confirmação em andamento e sem aprovação geral.
Checkpoint V4 local `ad21220`; mudanças posteriores ainda não commitadas.
Relatório corrente: [CONTINUACAO_POS_V4_20260915.md](docs/CONTINUACAO_POS_V4_20260915.md).
Evidências: `C:/CAIN/work/readiness-continuation-20260915`.
Instalação principal e produtores permanecem fora do escopo de escrita.

## Histórico preservado da rodada V4

# Rodada atual: prontidão CAIN — 14/09/2026

**Candidata V4 local, sem aprovação geral e sem promoção operacional.**
Branch `fix/readiness-main-20260914`, baseline `origin/main`
`8d4297a575ec1231ad7ec909faa8be0ea795e546`. O checkout original
`C:/CAIN/projeto` permanece no checkpoint `24f784c5dde1fa66c262ad5899f4fd8d02526adf`.

Foram corrigidos precisão decimal, cópia literal delimitada, seleção lexical de
entidade e transporte de contexto ao classificador. V4: 809 testes aprovados,
1 ignorado, 2 avisos; wheel não editável com 70 arquivos conferidos em QA.
SHA do wheel: `fba0a82859d408ea8a5f426e2536a673455cc19039fa422257685d1021aaae1e`.

Persistem falhas de retificação, memória após distrações, follow-up e seleção/
interpretação científica. São 94 fontes e 247 ocorrências em QA; 64 registros
derivados tipados não constituem denominador validado de hipóteses. Instalação
principal, dados/configurações e produtores preservados. Sem push, merge ou release.

Relatório vigente: [READINESS_RESULT_20260914.md](docs/READINESS_RESULT_20260914.md).
Ele identifica versões realmente ensaiadas, regressões, limites e retomada.
Recibos e scripts: `C:/CAIN/work/readiness-evidence-20260914`.
Entrega: `C:/Users/leona/Documents/Codex/2026-09-14/lei/outputs`.

## Histórico preservado abaixo

As entradas a seguir pertencem às rodadas anteriores; caminhos, branches,
contagens e resultados nelas não substituem o estado atual descrito acima.

---

# Estado verificado do CAIN

CAIN **0.4.12**, código instalado `dfabf6dab05df1662e9882ebe1091236daa14724`. Main em `C:/CAIN/projeto`; instalação `C:/CAIN/.venv`; serviço http://127.0.0.1:8877/.

Proteção contra interpretação de tabelas sem rótulos, contexto de origem/tempo e protocolo de workflow atualizado já instalados. [Relatório](docs/ANALYSIS_GUARD_20260913.md). Recibos em `C:/CAIN/work/install-dfabf6d-20260913`: health OK, 62 arquivos idênticos a fonte/wheel, 20 testes do pacote instalado aprovados, bancos/configurações e dependências de terceiros preservados. A tabela abaixo é o registro da rodada anterior à proteção, não uma nova certificação semântica.

| Item | Resultado |
|---|---|
| Engenharia | 680 testes aprovados, 1 skip Windows, 2 avisos; Ruff e sintaxe JavaScript aprovados |
| Instalação | Wheel offline, pip check e 62 arquivos iguais à fonte/wheel/instalação |
| Acervos conectados | Todos os registros, entidades, artefatos e referências dos seis acervos auditados |
| Cobertura dos produtores | Parcial; não são projetos inteiros |
| Bundles adicionais em QA | 36 entidades, 19 artefatos; 14 conteúdos verificados e 5 referências |
| Workflows | 3 fluxos de seis etapas completos e reabertos; redação semanticamente parcial/falha |
| Falha semântica | Brasileirão confundiu hipótese com resultado estabelecido; também houve extrapolações em Crypto/Stocks |
| Preservação | Bancos íntegros, linhas anteriores/configurações mantidas; só cain-research atualizado; produtores intactos |
| Publicação e CI | Recibos externos `git-publication.json` e `ci-final.json` na rodada atual |

[Relatório](docs/COBERTURA_PROJETOS_20260913.md), [continuidade](CONTINUIDADE.md), [instalação](docs/LOCAL_INSTALLATION.md). A aprovação de importação, recuperação e citações não certifica a interpretação do modelo.
