# Estado verificado do CAIN

CAIN **0.4.10**, código instalado **dcde48490a15af33048b764cfdb952af7599c3a8**. Checkout C:/CAIN/projeto em main; instalação não editável C:/CAIN/.venv; interface na porta 8877.

| Item | Estado |
|---|---|
| Modelo | qwen3.5:4b, parâmetros preservados |
| Mudança | Instruções de continuação, cópia exata e JSON puro |
| Engenharia | 631 testes antes do último ajuste; 33 afetados depois; Ruff e wheel offline aprovados |
| Preservação | Bancos íntegros, linhas anteriores e configurações preservados |
| Contratos | Snapshot 1.0.1 e Bundle 1.0.0, dependências preservadas |
| Limites | CPU lenta, elaboração desnecessária em alguns casos; sem certificação semântica geral |

[Relatório desta rodada](docs/LLM_FIX_20260913.md) contém resultados reais, falhas intermediárias, retestes e limites. [Manifesto operacional](operational-state.json) identifica wheel, código e verificação local. A CI remota não foi verificada para esta referência.

As falhas registradas na [0.4.9](docs/LLM_RETESTE_20260912.md) são históricas. Testes anteriores de documentos, projetos, pesquisa e workflows permanecem em [teste integral](docs/TESTE_INTEGRAL_20260912.md); esta rodada não repetiu integralmente essas áreas.

Para continuar: [CONTINUIDADE.md](CONTINUIDADE.md). Não substituir bancos atuais por backups antigos.

Pendência nova: preferência ativa de inglês não foi respeitada em uma pergunta portuguesa; tentativas sem melhora foram descartadas. Consulte o relatório antes de considerar idiomas aprovados.

Fechamento documental de 13/09/2026: serviço 8877 respondeu como 0.4.10/qwen3.5:4b; 61 arquivos do pacote, integridade e preservação dos bancos/configurações reconferidos. Não houve nova rodada de inferência nem mudança de código nesse fechamento. A [continuidade](CONTINUIDADE.md#retomada-sem-este-chat--fechamento-de-13092026) contém reprodução da pendência e instruções para retomar sem o chat.
