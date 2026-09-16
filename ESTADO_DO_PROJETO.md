# Estado CAIN — 16/09/2026

Consulte a [prontidão Stocks](docs/STOCKS_STUDY_READINESS_20260915.md) para código,
acervo, instalação, testes e limites de interpretação. As correções anteriores
estão integradas pelas [PR #4](https://github.com/leonardosovienski/cain/pull/4) e
[PR #5](https://github.com/leonardosovienski/cain/pull/5).
O piloto real encerrou com três respostas e nenhuma aprovação semântica geral;
os motivos estão no relatório de prontidão.

O acervo principal recebeu 48 fontes e contém 88 registros Stocks: 87 admitidos
nesta rodada e o registro anterior preservado. A leitura literal de H1, das
duas revisões da H17 e dos critérios da H22 passou em QA e na instalação principal. Isso não certifica
interpretação livre do modelo nem executa um experimento científico.

Evidências e cópias de recuperação: `C:/CAIN/work/stocks-study-20260915`.
Nada foi apagado. Consulte os recibos de ativação para o caminho exato do runtime.

<details>
<summary>Histórico preservado — não representa o estado corrente</summary>

# Estado do projeto — integração Stocks com main

| Área | Estado desta revisão |
|---|---|
| Código | Main `2bdb570` conciliada com Stocks `f6c86d3` na PR #3 |
| Pesquisa | Tabelas literais e seleção balanceada preservadas; listas JSON e filtro documental incorporados |
| Catálogo | Observações H17 tipadas por revisão preservadas; exportador combinado `/4` |
| Campos técnicos | Valores literais com abstenção explícita de interpretação |
| Validação | 861 testes aprovados, 1 pulado; Ruff aprovado. [Relatório de integração](docs/INTEGRACAO_STOCKS_MAIN_20260915.md) |
| Instalação principal | Preservada; integração Git não equivale a instalação |
| Limites | Sem nova certificação de inferência, hipóteses ou resultado econômico |

Os resultados de 831, 854 e 794 testes abaixo ou em relatórios anteriores pertencem
a versões diferentes; não são somados nem tratados como teste desta composição.



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

</details>
