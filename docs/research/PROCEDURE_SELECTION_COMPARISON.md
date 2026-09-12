# Procedimento selection-comparison/2

Estado: **disponível no escopo de verificação documental local**, sustentado por
verificador determinístico e testes executados; não é aprovação operacional geral.

Finalidade: comparar campos JSON esperados entre o extrator compacto existente e
o seletor de evidências, com retomada persistente e proveniência por SHA-256.
Entradas: banco ResearchSnapshotV1 local autorizado, política vigente, identidade,
ponteiros JSON explícitos e diretório de saída novo. Unidades: campos literais.
Condições: fonte JSON íntegra, uma versão de conteúdo por ponteiro; duplicações
byte a byte são consolidadas com referências preservadas. Permissão necessária:
leitura do acervo; não há inferência, embeddings, reranking, download ou divulgação.

Ambiente: Python 3.11+ com dependências do CAIN, checkout desta entrega. Script fixo
`scripts/verify_evidence_selection.py`; não aceita código ou comandos do modelo.
Cria backup SQLite por conexão somente leitura e trabalha nessa cópia. O processo
instala um audit hook que bloqueia sockets/subprocessos e escrita fora da saída;
SQLite só pode abrir a cópia. Essa fronteira foi testada, mas não é sandbox para
executar Python hostil ou bibliotecas nativas adversárias. A suíte impõe 30 segundos
por subprocesso. Não foi medida uma quota de memória do sistema operacional.

Passos (substituir os argumentos pelos caminhos autorizados):

```powershell
python scripts/verify_evidence_selection.py start --output NOVA_PASTA --database BANCO --policy POLITICA --identity ID --pointer /grupo/ID --pointer /trials/ID
# Encerrar o processo/sessão; retomar depois:
python scripts/verify_evidence_selection.py resume --output NOVA_PASTA
```

`start` grava objetivo, parâmetros e hash da implementação, cria workflow
inspect/search e executa apenas inspect. `resume` revalida política/implementação,
executa search e verifica os campos com parsing independente dos ponteiros,
SHA-256 do texto, trechos/offsets e presença dos ponteiros selecionados. Produz
`verification.json` com expected_fields, selected_expected_fields e
compact_expected_fields. Aprovação exige todos os campos esperados selecionados,
sem fabricar conteúdo. Sucesso do workflow isoladamente não satisfaz o verificador.

Recuperação: uma falha deixa task/checkpoint e workflow consultáveis. Não remover
bancos/entradas; corrigir a causa dentro do contrato ou iniciar nova pasta com
nova versão. Política ou implementação alterada requer novo caso. Um recibo já
confirmado não é reescrito; cancelamento impede retomada. Preferência de formato
não altera registros nem valores de origem.

Histórico e critérios: /1 foi proposta em desenvolvimento e recusou referências
repetidas. /2 consolida somente conteúdo byte-idêntico e vincula a implementação.
Foi revisada pelo implementador e testada automaticamente em dois casos com
identidades distintas (incluindo Unicode), retomada entre processos, idempotência,
recusa de campo ausente e bloqueio efetivo de rede/escrita externa. Dois casos
locais autorizados de estado/trial passaram com 2/2 campos, com recibos privados
`procedure-h4-v2` e `procedure-h6-v2`. Esses casos são desenvolvimento, não reserva.
Autoridade da transição: verificador determinístico /2 + suíte
`tests/integration/test_selection_procedure.py`; nenhuma aprovação por autorrelato
LLM. Escopo da disponibilidade: repetir essa verificação em cópia autorizada.

Não usar para resolver causalidade, significado estatístico, decidir última versão,
executar hipóteses, comparar identidades ambíguas ou conceder acesso. JSON inválido,
campos ausentes e versões divergentes exigem recusa/adaptação; valores longos podem
não caber e produzir reprovação explícita. Correção posterior exige nova versão,
novos testes e retirada/supersessão deste estado quando suas condições deixarem
 de valer. Resultados de teste não se tornam regras factuais de pesquisa.
