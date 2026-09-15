# Continuidade CAIN — fechamento V8, 15/09/2026

## Comece aqui após apagar o chat

O código da candidata V8 e seu histórico foram integrados ao checkout `C:/CAIN/work/readiness-main-20260914`, na branch `fix/readiness-main-20260914`. Esta rodada autoriza commit e envio dessa branch ao GitHub. O checkpoint é de engenharia e continuidade: **não há aprovação geral, merge em main nem instalação principal da V8**.

O recibo final de publicação e conferência fica em `C:/Users/leona/Documents/Codex/2026-09-14/lei/outputs/ENCERRAMENTO_GIT_20260915/VERIFICACAO_FINAL.json`: contém commit exato, ref remoto, hashes e resultado das verificações. Conferir esse recibo para o SHA de encerramento, que não pode ser embutido no próprio commit sem circularidade.

## Onde cada coisa está

| Conteúdo | Local e condição |
|---|---|
| Código, testes e Markdown | GitHub, branch `fix/readiness-main-20260914`; checkout canônico acima |
| V8 originalmente congelada | Cópia `C:/Users/leona/Documents/Codex/2026-09-14/lei/work/cain-v8`, commit `44a3f988955eb50ddded07b60dfba8977accc023`; preservada |
| Instalação QA V8 | `C:/Users/leona/Documents/Codex/2026-09-14/lei/work/evidence-v8/installed-qa-v8`; não editável |
| Entrega V8 verificável | `C:/Users/leona/Documents/Codex/2026-09-14/lei/outputs/CAIN_continuacao_V8_20260915` |
| Evidências V4 | `C:/CAIN/work/readiness-evidence-20260914` |
| Evidências V5/V6/V7 | `C:/CAIN/work/readiness-continuation-20260915` |
| Evidências V8 e scripts de fechamento | `C:/Users/leona/Documents/Codex/2026-09-14/lei/work` |
| Backup independente desta tarefa | `C:/CAIN/backups/continuidade-20260915-v8`; inventário com hashes, bundles Git, evidências e entregas |
| Cópia privada do chat | No backup, `CHAT_PRIVADO_ATE_BACKUP.jsonl`; prefixo completo até o instante da cópia, mais este handoff de encerramento |
| Instalação de uso preservada | `C:/CAIN/.venv`; checkout original `C:/CAIN/projeto` em `24f784c5dde1fa66c262ad5899f4fd8d02526adf` |

Os arquivos locais de QA, bancos, ambientes, configurações pessoais e transcrição privada não são parte do upload. Deletar a tarefa do Codex não deve ser confundido com apagar estas pastas no disco. A preservação desta rodada não é uma auditoria de todo o PC nem substitui backup externo contra falha do disco.

## Identidade e validação

Wheel nominal `cain-research 0.4.12`, SHA-256 `e684e7ad5ed36b6b27d8889b6fe5e0ac6f48d7b9cf5eab52f13e7a2930cb1216`. Os70arquivos de produto coincidem entre fonte V8, wheel e instalação QA. A integração no checkout canônico preserva esses bytes. Dependências iguais à V7. Testes V8: **831 PASS, um skip de symlink Windows, duas advertências; Ruff aprovado**. Consulta instalada do cadastro:64entradas, zero fontes obrigatórias ausentes; seis controles determinísticos de integridade aprovados. São resultados offline/de recuperação, não confirmação semântica de uso.

Modelo autorizado: `qwen3.5:4b`, digest `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`; embeddings `qwen3-embedding:0.6b`, digest `ac6da0dfba84a81fdbfbaf330198c33cd77c4cdfc53e8bc50eb581914a15621d`. Temperatura0, seed42, contexto8192, geração768, entrada6500bytes, timeout240s, think=false. Modelo e parâmetros não foram trocados.

## Resultados reais e pendências que não podem desaparecer

- V7 geral:46episódios/85turnos,43PASS e3FAIL B08 (recusa com palavra proibida). M02/M03 e variantes M04 numérica/não numérica passaram em três repetições cada, naquela versão.
- V7 científica:13episódios previstos;4concluídos,1interrompido e8não executados. Dos4concluídos:3FAIL_SEMANTICS e1PARTIAL_COMPLETENESS. Contrato de tamanho válido não significa resposta correta.
- H17: persistiu invenção de causa de falha na leitura do ZIP; exit2 informa falha, sem comprovar essa causa. Preservar primeira observação e correção de07/09/2026,51 versus47ausentes em5399, unidades e ausência de P&L executável.
- H4/H5: preservar trial literal `v2-dpl-gemini-h7`, H4 n=5, risco de cota e encerramento sem veredicto. V8 corrige seleção do motivo e instrução que confundia ausência de medição com efeito zero. Ainda falta geração final confirmatória.
- BR001/002/003, abreviações002/003, inversão, identidade ausente, domínios distintos e documento hostil efetivamente recuperado exigem confirmação completa por geração.
- Cadastro:231arquivos triados (78/47/106),71candidatos,64entradas tipadas,51linhas de ledger são denominadores diferentes.37associações literais verificadas. Fronteira documental não prova independência científica.
- Recibos:275chamadas de geração,273conclusões comprovadas e2desconhecidas; tags não contam como inferência. Não atribuir timeout a hardware sem comparação mínima/completa controlada.
- As36famílias V8 permanecem sem confirmação real completa. M07=outro usuário, M08=outro projeto, M12=falha explícita do backend. Controles de preferência/orçamento são suplementares.

Durante a rodada anterior o ambiente perdeu acesso de escrita/rede e interrompeu a confirmação. A sessão de fechamento voltou a ter acesso; isso não transforma testes não executados em PASS. Esta rodada organiza e publica o checkpoint, sem reiniciar a campanha científica. Estado dos serviços antigos deve ser verificado antes de uma retomada; não reutilizar active.json sem reconciliar o pedido interrompido.

## Próximo trabalho, com critérios preservados

1. Ler este documento, o relatório V8 e a matriz na entrega local; verificar hashes e ref remoto do recibo de fechamento.
2. Usar instalação QA isolada, corpus/política copiados e os mesmos parâmetros. Nunca usar o perfil pessoal `leo` para ensaios mutáveis.
3. Verificar runtime e reconciliar a tentativa interrompida. Uma geração por vez, recibos de despacho e resposta, conclusão desconhecida permanece desconhecida.
4. Confirmar variantes lacradas após o congelamento, três repetições instáveis e as demais famílias obrigatórias. Executar CLI/API e navegador real; ASGI não substitui navegador.
5. Fazer comparação mínima/completa com mesma configuração, sem alterar denominadores ou ocultar falhas. Mudança de produto exige nova candidata.

Nenhuma falha, parcial ou NOT_RUN recebe aprovação. Revisão e implementação foram feitas pelo mesmo agente; não há certificação independente. Não instalar na principal nem mesclar em main com base neste checkpoint.

## Documentos de apoio

- [Relatório histórico da entrega V8](CONTINUACAO_V8_20260915.md)
- [Continuação e diagnósticos V5–V7](CONTINUACAO_POS_V4_20260915.md)
- [Índice documental](README.md)
- [Continuidade de entrada](../CONTINUIDADE.md)
