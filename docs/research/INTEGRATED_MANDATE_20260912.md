# CAIN: integração e execução dos comparadores pendentes

## Resultado entregue

Este ciclo atende ao pedido posterior de integrar o candidato e executar as
comparações pendentes. Não representa aprovação de todo o produto ou da geração
livre. Bundle e a correção de evidências agora pertencem ao mesmo código e pacote.
Hermes, Qwen3.5-4B, SmolLM3-3B e Qwen3-Reranker-0.6B foram executados localmente.
Não houve push, merge de branches, release pública ou instalação na área principal.

Base: `12f0c7b65df9bda2969f32a02928ff50d9b95368`.
Branch: `integration/cain-full-mandate-20260912`.
Checkout: `C:\CAIN\work\cain-full-mandate-20260912`.
Recibos privados: `C:\CAIN\work\cain-full-receipts-20260912`.

## Integração real

Foi aplicada a parte pertinente de Bundle da referência histórica `9001a33`,
preservando as correções posteriores do Historian e da seleção. A integração
inclui arquivo de objetos, backup, verificação, política por operação, projeções,
diagnósticos, CLI e rotas Bundle. A dependência `predictor-research-bundle==1.0.0`
e seu wheel vendorizado acompanham o candidato. Não foram importadas configurações
de CI, overlays de outros produtores ou alterações históricas não necessárias.

O conflito no Historian foi resolvido conservando o contrato Snapshot atual e
adicionando os caminhos de metadados Bundle. A interface ganhou uma consulta
delimitada a metadados, com identidade, estado, revisão e relações visíveis;
fontes e cobertura ficam disponíveis em detalhes. O retorno é descartado se o
usuário, projeto ou acervo mudar durante a consulta.

O teste da rota Snapshot também verifica que sua autorização não abre acesso ao
Bundle. Não foi formada uma união permissiva de políticas. As duas instâncias de
teste usam o mesmo código, com os bancos e políticas já existentes em seus escopos:

- `http://127.0.0.1:8882`: Snapshot, resposta literal de H4 verificada pela UI.
- `http://127.0.0.1:8883`: Bundle, estado, revisão e relação de trial de H4
  verificados pela UI; 47 objetos copiados e verificados no backup isolado.

A consulta Bundle não abre automaticamente artefatos nem infere a partir deles.
Sua política existente não autoriza geração, e essa restrição foi preservada.
O relato Snapshot distingue campos presentes de motivo/amostra não localizados
nos trechos selecionados; não transforma ausência no recorte em inexistência.

## Comparadores executados

O protocolo adicional foi registrado em `evaluation/full-mandate-comparison.json`
antes das execuções a que se aplica. O contraste dos geradores reutiliza a pergunta,
rubrica, fontes e orçamento já congelados no ciclo anterior. São casos conhecidos
de desenvolvimento; as condições não são episódios independentes.

| Componente/condição | Tempo observado | Resultado no caso |
|---|---:|---|
| Qwen3.5-4B, evidência selecionada | 172,24 s | Estado/trial corretos e amostra ausente; trata o nome do estado como confirmação do motivo. Não aprovado integralmente pela rubrica estrita |
| Qwen3.5-4B, fonte integral autorizada | 217,70 s | Atribui contagem de outra identidade ao alvo; reprovado |
| SmolLM3-3B Q4_K_M, evidência selecionada | 65,15 s | Fatos obrigatórios e limitações adequados neste caso conhecido |
| SmolLM3-3B Q4_K_M, fonte integral autorizada | 98,76 s | Omite a trial obrigatória; reprovado |
| Hermes 0.21.2 + Qwen3.5-0.8B, recorte selecionado | 73,97 s | Uma chamada real; omite trial e interpreta incorretamente a disponibilidade de motivo/amostra; reprovado |
| Qwen3-Reranker-0.6B, H4 | 42,76 s de scoring | 2/2 campos antes e depois; sem ganho de retenção |
| Qwen3-Reranker-0.6B, H6 | 45,31 s de scoring | 2/2 campos antes e depois; sem ganho de retenção |

Nos geradores, foram mantidos temperatura 0, seed 42, contexto 8192, saída máxima
768, `think=false` e limite de entrada 6500 bytes. Bytes não são tokens: os tokens
medidos pelo Ollama constam nos recibos. Um modelo de inferência por vez foi usado
na máquina de aproximadamente 8 GB de RAM. Downloads/instalações ocorreram durante
parte da preparação; os tempos não são benchmark de máquina ociosa.

SmolLM3 usa o GGUF da organização ggml-org, derivado de HuggingFaceTB/SmolLM3-3B,
na quantização Q4_K_M. A tag genérica tentada no Ollama não existia; o GGUF foi
obtido e registrado como `cain-test-smollm3:3b`. Isso é uma configuração identificada
do candidato, não execução dos pesos BF16 originais. O template efetivo foi salvo.

O reranker usa Transformers 4.57.6 e PyTorch 2.14.0+cpu, BF16, revisão
`e61197ed45024b0ed8a2d74b80b4d909f1255473`. Seu score é a probabilidade normalizada
dos logits finais de `yes`/`no`, conforme a interface documentada, não uma resposta
de chat improvisada. Entrada admitida para geração, guardas antes/depois, scoring
offline, sem truncamento silencioso. Foram preservados até 2 cards/2200 bytes.
Os pools conhecidos contêm apenas os dois campos relevantes; essa comparação
não mede qualidade geral de ranking nem justifica integrar o reranker ao produto.
O carregamento observado foi 1,00 s, separado do tempo de scoring.

Hermes foi instalado em ambiente próprio, pela modalidade editável suportada,
no commit `1c671beab29164d8931c5d01c5739502267089d8`. Usa home isolado, endpoint
Ollama em loopback, ferramentas desabilitadas, sem memória importada ou fontes
externas. Um audit hook recusou conexões fora do endpoint local. Recebeu os mesmos
trechos/pergunta, com o modelo histórico, mas seu prompt nativo e a interface de
saída diferem do CAIN. É comparação documental delimitada de produto, não isolamento
causal da camada de agente, nem teste de todas as capacidades nativas do Hermes.
O estado `completed` do Hermes significa término da execução, não acerto da tarefa.

O desenho 2×2 com reranker não foi forçado: a retenção já é completa nos dois casos
e o ranking não acrescentou informação. A comparação contexto×gerador não é
rotulada como ranking×gerador. Não há promoção automática de componente.

## Continuidade, comparação e procedimento

O procedimento `selection-comparison/3` foi novamente iniciado e retomado em
processos distintos no candidato integrado. H4 e a variante H6 verificaram dois
campos cada. A tentativa com um caminho ausente foi recusada e não criou aprovação.
O piloto executou novamente reconstrução literal, leitura do estado concluído,
comparação determinística e reutilização sem repetição de efeitos.

O controle simples chegou ao mesmo resultado documental. Não foram medidos tempo
humano, superioridade geral ou avaliação independente. As quatro missões reutilizam
dois casos conhecidos e não equivalem a oito episódios independentes. Relações de
versão só são apresentadas quando documentadas, não são reconstruídas por suposição.

## Limite do anexo histórico

O relatório `CAIN_decisao_tecnica_e_evidencias.md` foi localizado. O ZIP original,
seu manifesto, `probe_grounding.py` e `grounding_results.json` não foram localizados
nas áreas consultadas. A condição original é usar anexos **quando disponíveis**.
Foi preservada a referência histórica identificada e foram executadas regressões
separadas; isso não é reprodução byte a byte do script ausente. Não foi criado um
substituto apresentado como anexo original. Para essa reprodução exata ainda será
necessário fornecer o pacote original. Esse limite não foi escondido como sucesso.

## Matriz final de uso

Validação conjunta inicial: **566 passed, 1 skipped**. Validação final usando os
módulos extraídos do wheel instalado em diretório isolado: **566 passed, 1 skipped**
em 125,82 s. Os dois avisos são de depreciação do ambiente FastAPI/Starlette.
O teste final inclui negação de acesso Bundle sob autorização apenas Snapshot.
Ruff e `git diff --check` passaram. Não foi executado Linux neste ciclo.

Wheel: `cain_research-0.4.7-py3-none-any.whl`, SHA-256
`dca07f89244e4be9d69b811faaa4b54576fe30055eea2272036bf3df13beb93c`.
A versão nominal 0.4.7 foi preservada; o hash e o commit distinguem este candidato
da instalação anterior. O wheel não foi instalado na área principal. As UIs usam
o checkout; a suíte do wheel usa `wheel-runtime` como origem dos módulos.

| Parte | Implementado/testado/utilizável |
|---|---|
| Seleção, identidade, literalidade e proveniência | Implementado; regressões e suíte conjunta executadas |
| Review e Historian/Snapshot | Integrados; resposta de campos explícitos utilizável no recorte; Historian exercitado na UI |
| Bundle | Integrado no mesmo pacote; API/CLI/backup/política testados; UI de metadados exercitada com fonte autorizada |
| Comparação e retomada | Procedimento v3 executado no candidato, com variante, recusa e repetição verificada |
| Geradores nomeados | Execuções reais concluídas; resultados mistos; nenhum promovido |
| Reranker nomeado | Scoring real concluído; nenhum ganho neste recorte; fora do caminho padrão |
| Hermes | Instalado e executado no recorte documental; erro de resposta registrado |
| Produto completo/científico | Não aprovado por estes testes |
| Pacote histórico original | Indisponível; reprodução exata não executada |

## Repetir, preservar e reverter

Os recibos incluem payloads/saídas autorizados, revisão/digest/template dos modelos,
instalações, erros de preparação, resultados, bancos de teste e backup de objetos.
Eles ficam fora do Git. Scripts locais: `generator_comparison.py`, `hermes_probe.py`,
`score_reranker.py`, `prepare_preview.py`, `preview_app.py`.

No checkout, com `PYTHONPATH` apontando para `src`, o Python existente de
`C:\CAIN\work\supply-final-20260912\venv\Scripts\python.exe` executa `pytest -q`
e `scripts\assess_mandate_missions.py --receipts C:\CAIN\work\cain-full-receipts-20260912`.
Para reiniciar as UIs, no diretório de recibos e com o mesmo Python:

```powershell
python -m uvicorn preview_app:app --host 127.0.0.1 --port 8882
python -m uvicorn preview_app:bundle_app --host 127.0.0.1 --port 8883
```

São comandos separados para terminais separados. Não iniciar outra instância se
a porta correspondente já estiver servindo. Os PIDs da preparação estão nos recibos.
Reversão operacional: encerrar apenas essas instâncias. Nenhuma configuração de
modelo padrão, grant ou fonte de produtor foi alterada. Os modelos adicionais foram
baixados para o armazenamento local de modelos, sem substituir os já existentes.

## Fontes técnicas

- [Qwen3-Reranker-0.6B: licença e scoring](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B).
- [Qwen3.5-4B no Ollama](https://ollama.com/library/qwen3.5:4b).
- [SmolLM3 GGUF e origem](https://huggingface.co/ggml-org/SmolLM3-3B-GGUF).
- [Hermes: código-fonte](https://github.com/NousResearch/hermes-agent).

Essas referências descrevem componentes. Os resultados acima vêm das execuções
locais, não de benchmarks publicados pelos fornecedores.
