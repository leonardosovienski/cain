# Procedimento selection-comparison/3

Estado: **disponível somente para comparação documental local autorizada**.
Substitui /2, retirada após reprodução de falso sucesso na segunda retomada.

Finalidade: confrontar dois artefatos de seleção (relações compactas e cards) com
valores de campos JSON lidos independentemente da fonte; gravar evidência,
interromper e retomar sem duplicar ações confirmadas.

Entradas: banco de snapshots autorizado de até 128 MiB, política atual, identidade
exata, ponteiros esperados e pasta de saída nova. O texto precisa ser JSON íntegro,
com uma versão de conteúdo por ponteiro. Cópias byte-idênticas são consolidadas
com referências preservadas; versões divergentes não são escolhidas implicitamente.
A contagem usa campos, nunca experimentos, tamanho de amostra ou suporte semântico.

Permissões: leitura conforme política do receptor; SQLite fonte aberto somente
leitura para backup. A cópia e recibos são as únicas saídas. Não há inferência,
embeddings, downloads ou gravação nas fontes. Revalidação da política a cada
retomada. Hash da implementação inclui script, grounding, workflows, analysis e
field_review; mudança requer nova execução com nova pasta.

Ambiente: Python 3.11+, dependências existentes do CAIN. Script fixo, sem código
fornecido pelo agente/modelo. Audit hook bloqueia sockets, subprocessos e escrita
Python fora da saída, e restringe conexões SQLite à cópia. Deadline efetivo de
30 segundos no processo encerra com 124. Limites do inspetor/seletor continuam
vigentes. Não é sandbox para Python adversário ou bibliotecas nativas hostis;
não existe executor genérico neste procedimento. Não há quota de RAM do SO alegada.

Execução no checkout, com PYTHONPATH apontado ao src:

```powershell
python scripts/verify_evidence_selection.py start --output NOVA_PASTA --database BANCO --policy POLITICA --identity ID --pointer /grupo/ID --pointer /trials/ID
# Em outro processo/sessão:
python scripts/verify_evidence_selection.py resume --output NOVA_PASTA
```

O objetivo, restrições e parâmetros ficam em task.json; checkpoint.json registra
inspect e a próxima etapa search. A retomada usa o workflow persistido. O relatório
final contém o estado atualizado em workflow e referencia as versões de fonte.
O manifest de entrada permanece histórico; a pendência atual vem do workflow.

Verificador /3: ponteiro resolvido por parsing independente; SHA-256 de fonte;
offset e quote literais; chave e valor da quote iguais ao campo esperado. Depois,
exige que todos os campos esperados estejam selecionados. verification.json traz
verified, expected_fields, selected_expected_fields e compact_expected_fields.
verification.sha256 detecta alterações acidentais do recibo. Repetir resume só
retorna sucesso se o recibo existir, estiver aprovado e tiver hash correto.
Recibo reprovado, incompleto ou alterado permanece reprovado. Hash lateral não é
assinatura criptográfica contra quem pode editar simultaneamente ambos os arquivos.

Recuperação: preserve toda a pasta e recibos de falha. Com fonte/política/implementação
alterada ou estado cancelado, recuse a retomada e crie novo caso conforme autorização.
Não reative cancelados. Uma falha antes de verification.json permite tentar a causa
transitória no mesmo contrato. Um recibo reprovado não é promovido por nova chamada.
Preferência de apresentação não muda fonte, campo ou resultado verificado.

Critérios de disponibilidade e histórico nesta rodada:

1. Proposto: regressão demonstrou falso sucesso de /2; nenhum dado corrigido por edição.
2. Revisado: comparação de valores e integridade de recibos explícitas, fronteiras preservadas.
3. Testado: suíte completa 502 pass/1 skip, incluindo adulteração, revogação,
   troca de ponteiro para quote literal errada, recusa por orçamento e idempotência.
4. Disponível no escopo: dois casos documentais autorizados passaram (2/2 campos
   cada), em processos separados, e um terceiro recusou ponteiro ausente.

Autoridade: verificações determinísticas e testes reproduzíveis, não autorrelato
LLM. Recibos privados: C:/CAIN/work/cain-mandate-receipts-20260912/procedure-h4,
procedure-h6 e procedure-refuse. São desenvolvimento conhecido, não avaliação
reservada. Não usar para causas, inferência científica, decisões financeiras,
seleção automática da última revisão ou abertura de acesso. Correção futura exige
nova versão e retirada/supersessão quando as condições deste procedimento não valem.
