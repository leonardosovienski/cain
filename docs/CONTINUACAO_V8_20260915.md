| Capacidade | Causa confirmada | Correção | Evidência na candidata final | Veredicto | Pendência |
|---|---|---|---|---|---|
| Memória/retificação | Contexto precisava preservar fatos do usuário e atualizações | Histórico factual e escopo preservados | V8 offline; V7 M02/M03 3/3 cada | V8 não confirmada | Repetir episódios completos e isolamento |
| Aprofundamento | Instrução adicional prejudicava cálculo; “Explique” perdia resposta anterior | Removido reforço redundante e incluída continuação explícita | V7 variantes numérica e não numérica 3/3; V8 offline | Parcial por versão | Nova geração V8 |
| Múltiplas IDs | Seleção podia perder identidades e relações | Reserva por identidade e resultados; V8 reserva motivo de encerramento | Testes de seleção; cadastro consultado no pacote instalado | Parcial | BR001/002/003, abreviações, inversão, ausente e cruzamento com geração final |
| H17 contrato/semântica | V7 cumpriu tamanho, mas inventou causa de falha do ZIP | Contrato preservado; instrução distingue falta de medição de efeito zero | V8 sem geração; não demonstrada correção da invenção do ZIP | Semântica falha em V7 / V8 não executada | Confirmar revisões, datas, proporções, exit2 e três papéis |
| H4/H5 | Motivo de encerramento perdido na seleção; instrução induzia ausência de efeito | Reserva motivo; corrige instrução e reconhecimento de português | Novos testes offline; seleção prototipada retém motivo e IDs | Parcial | Confirmar geração, completude e ausência de refutação indevida |
| Timeouts | Há recibos de transporte e durações; causa de hardware não estabelecida | Observação serial e interrupção diante de conclusão incerta | Histórico sanitizado; comparação final mínima/completa não executada | Bloqueado | Restaurar runtime autorizado e executar diagnóstico controlado |
| Cadastro | 231 arquivos/71 candidatos/64 entradas/51 linhas têm escopos distintos | Tipificação, proveniência e correção de locators | Consulta real do consumidor V8 separada de geração | Documental; independência científica parcial | Validar interpretação gerada e ambiguidades científicas |
| Matriz completa | PASS antigos e contagens de tags não certificam a versão final | Mapeamento original, versões e contagens separados | 831 PASS offline, 1 skip; 36 famílias reais V8 NOT_RUN | Sem aprovação geral | CLI/API/browser e ensaios obrigatórios finais |

# Continuação focada — entrega V8

## Estado efetivo

A candidata V8 foi construída e instalada em QA não editável dentro da pasta permitida desta tarefa. Seus 70 arquivos de produto foram comparados byte a byte entre fonte, wheel e instalação. Dependências iguais à V7. O pacote conserva a versão nominal 0.4.12; o hash identifica a candidata.

O ambiente mudou durante a segunda repetição científica H17 da V7. A sessão passou a impedir gravações em C:/CAIN e acesso de rede. Solicitações de acesso não receberam concessão. O trabalho independente continuou em cópia no workspace; não houve substituição do backend, troca de modelo/configuração nem uso de outro canal para contornar a restrição. Novas gerações, navegador final e comparação mínima/completa ficaram NOT_RUN. Não há aprovação geral.

O checkout canônico C:/CAIN/work/readiness-main-20260914 continua em 3397116293bc37898fccfc49234f4df27222601f com alterações V7 locais. A cópia permitida preservou esse estado em cb3a6689519263084100dc8e2a79dbc5a3f5bf39 e contém as correções V8. A instalação principal não recebeu esta candidata. Nenhum push, merge, release, admissão principal ou operação financeira foi executado. O remote foi verificado antes da mudança de ambiente; não foi novamente consultado depois dela.

## Resultados preservados por versão

- V4 permanece congelada. Seus erros não foram reescritos.
- V6: 821 testes offline aprovados e um skip. Bateria geral: 35 PASS e nove FAIL em 44 episódios. Falhas de cálculo, aprofundamento não numérico e B08 foram preservadas.
- V7: 825 testes offline aprovados e um skip. Bateria geral: 46 episódios/85 turnos, 43 PASS e três FAIL B08. A recusa usa a palavra proibida; segue falha obrigatória. Casos M02 e M03 tiveram três episódios completos cada; M04 novo numérico e não numérico tiveram três cada. Seis controles extras passaram no escopo descrito. Esses PASS pertencem à V7.
- Científica V7: 13 episódios planejados; quatro concluídos (três FAIL_SEMANTICS e um PARTIAL_COMPLETENESS), um interrompido por transporte e oito não executados. Os quatro concluídos percorreram support/challenge/synthesis e cumpriram o limite de caracteres; isso não os torna semanticamente corretos. A segunda tentativa H17 contém support concluído e challenge com erro; conclusão da geração do challenge permanece desconhecida.
- V8: 831 testes offline aprovados, um skip de symlink Windows, duas advertências de dependências; Ruff aprovado. Seis novos testes exercitam seleção de motivo e instrução em português, sem inferência real. Duas tentativas anteriores de testes ficaram registradas: problemas de ACL temporária e expectativas de teste desatualizadas foram corrigidos. O primeiro build falhou por setuptools ausente; o runtime local empacotado construiu o wheel offline, sem downloads.

## Fatos científicos e limites

H17 inicial: 5348/5399 válidas, 51 ausentes, IC -0,013189 e spread -0,252221 p.p. Corrigida: 5352/5399 válidas, 47 ausentes, IC -0,013201 e spread -0,161341 p.p. Ambas são observações de 07/09/2026 inconclusivas por qualidade de dados, sem P&L executável. O runbook de 06/09 informa exit code 2 como falha; não prova falha na leitura do ZIP. A V7 inventou essa causa mesmo com fontes pertinentes presentes. A V8 não recebe aprovação sem resposta real correta.

H4: o identificador literal das nove respostas antigas auditadas foi v2-dpl-gemini-h7; “H4v2-dpl-gemini-h7” era concatenação no relatório, não alteração das respostas. Amostra n=5, encerramento por decisão do responsável e risco de cota Gemini, sem veredicto estatístico. Na V7, a síntese isolada omitiu a cota; no contraste H4/H5 houve associação indevida de REFUTED e afirmação indevida de ausência de efeito. A correção V8 reserva o motivo e retira a instrução que confundia comparação bloqueada com efeito não observado. O protótipo de seleção é diagnóstico, não validação semântica. Um verificador inicialmente buscou “cota Gemini” e marcou falso; o texto continha “cota do Gemini”. A tentativa e sua retificação estão preservadas.

Cadastro: 78/47/106 arquivos, total231; 71 IDs candidatos foram classificados em64 entradas tipadas e7 exclusões justificadas. As64 incluem44 rótulos H (9 Crypto,22 Stocks,13 linhagens Brasileirão),5 famílias AR/BR e15 claims. As51 linhas nativas de ledger têm outro denominador. Há37 associações literais verificadas; as27 restantes têm categorias explicitadas, não equivalem a27 trials perdidas. A triagem por arquivo não certifica equivalência semântica integral. Relações documentais verificadas não estabelecem hipóteses cientificamente independentes. Consulta do consumidor e interpretação por modelo são resultados separados.

## Tempos e utilidade

Os recibos contêm 275 chamadas /api/generate: 273 com done=true e duas sem conclusão comprovada; tags e embeddings não contam como geração. Há arquivo adicional para despachos sem recibo. A contagem legada observed_generation_count incluía tags e não deve ser usada como total de inferências. Memória é disponibilidade física do sistema amostrada, não RSS do processo. O backend fornece durações agregadas, não instantes internos de início/fim de cada fase; tempo residual permanece sem causa atribuída.

A tarefa H4 comparou recuperação nativa de12 registros em0,339s com workflow de345,723s. Support e challenge cobriram4/4 aspectos; synthesis3/4. Isso é utilidade parcial nesta tarefa, sem medir tempo humano ou provar superioridade geral. O diagnóstico mínimo/completo final ficou não executado. Um diagnóstico anterior H17 mínimo levou cerca735s apesar de HTTP200, com grande tempo residual não atribuído; não prova incapacidade do hardware ou modelo.

## Preservação, reprodução e retomada

Manifesto, patches, wheel, testes, respostas completas sanitizadas, matriz e recibos acompanham a entrega. Bancos pessoais, dumps de ambiente e segredos não entram no pacote. Fontes produtoras e artefatos antigos foram somente lidos e tiveram preservação verificada. Serviços temporários antigos ficaram sem verificação conclusiva após a troca de identidade/permissão; não se afirma encerramento confirmado. Nenhum servidor substituto foi iniciado.

O patch completo parte do checkpoint V4 ad212200c96346c87046725ff0c615b03fa25299. O patch incremental parte dos bytes do checkout canônico V7 preservado, incluindo alterações locais; não aplicar o patch completo novamente sobre esse checkout. Ambos são verificados por aplicação em cópias isoladas e reconstrução de bytes. A pasta work mantém histórico local e QA; os links desta entrega apontam apenas para outputs.

A próxima etapa exige runtime acessível no escopo autorizado: confirmar a candidata final em ensaios lacrados, incluindo as36famílias, três repetições instáveis, multiIDs, fonte hostil recuperada com geração, CLI/API/browser e comparação serial mínima/completa. Mudança adicional no produto exige nova candidata; não reutilizar a identidade V8 para código diferente. O mesmo agente implementou e revisou: não há avaliação independente.

Wheel V8 SHA-256: `e684e7ad5ed36b6b27d8889b6fe5e0ac6f48d7b9cf5eab52f13e7a2930cb1216`.
