# Entrega das duas correções de arquitetura — Cain 0.4.3

## Resultado durável e histórico recuperável

A API agora registra um recibo por `(user_id, run_id)` antes de iniciar o processamento.
Repetir a mesma chave com outro conteúdo ou contexto é rejeitado. Uma chave em
processamento ou com falha não inicia outra geração, inclusive em outra instância.
Clientes devem gerar e conservar `run_id` antes do POST; a UI faz isso e conserva o
recibo para reenvio manual após perda de conexão. Sem armazenamento do navegador,
essa conservação fica limitada à página aberta. Clientes que omitem a chave recebem
uma chave gerada pelo servidor, mas não têm deduplicação de uma resposta HTTP perdida.

O evento append-only `completed` e o resultado integral da API são gravados na mesma
transação SQLite. O recibo só fica `ready` quando ambos são confirmados. O resultado
inclui resposta, fontes, perfil usado no retorno, metadados e identidade estável do turno.
Os eventos anteriores de mediação e os sinais de identidade continuam preservados.

O histórico é uma projeção recuperável. Se sua gravação falhar, a API retorna o resultado
já preservado com `history_status=pending`. `GET /runs/{user_id}/{run_id}`, um POST idêntico
ou a abertura da conversa recuperam a projeção sem chamar o provider ou reaplicar
preferências. A gravação é idempotente; falha depois do commit também não duplica turnos.
A recuperação mantém a data original do recibo. `history_status=saved` significa
histórico gravado, não confirmação de que o navegador recebeu a resposta HTTP.

Se o processo morrer antes da conclusão atômica, o recibo permanece em processamento
ou falha: não há promessa de recuperar uma resposta que nunca foi confirmada. O Cain
bloqueia regeneração silenciosa com HTTP 409. Os efeitos anteriores auditados podem
existir, e uma nova tentativa intencional exige uma nova chave. Não há retry automático
de modelo, alteração de eventos passados ou transação aberta durante inferência.

A migração é aditiva (`run_receipts` e índice). Históricos anteriores continuam legíveis;
a garantia de recibo aplica-se a pedidos registrados pela API 0.4.3. A CLI de geração
mantém seu contrato anterior; o defeito corrigido era a fronteira API/histórico da UI.

## Perfil sem índice global

`build_profile` compõe apenas o serviço de identidade e seu armazenamento. API e CLI
usam essa composição para consultar, definir, remover e limpar preferências. Nenhum
agente, transporte de modelo ou reconstrução do histórico é necessário. As preferências
continuam persistidas com a mesma auditoria e resolução por escopo. A composição de
conversação permanece separada, com sua recuperação de memória existente.

## Verificação

Dez testes novos cobrem falha antes/depois da gravação do histórico, recuperação por
leitura da conversa, replay e conflito de chave/contexto, isolamento por usuário,
rollback atômico do resultado com o evento de conclusão, recibo abandonado, concorrência
entre duas instâncias e controles de perfil API/CLI com 500 sinais de outro usuário.
Três casos encerram abruptamente um subprocesso antes da conclusão, depois da conclusão
e depois do histórico: ao reabrir, não ocorre nova inferência nem duplicação de sinais.

As simulações de geração usam providers explícitos de teste; não são inferência real
ou validação científica/econômica. O acervo L0 e os repositórios dos predictors não
foram alterados por estas duas correções.

Resultado da suíte completa: **374 aprovados, 1 skip** (privilégio de symlink no Windows), com dois avisos de depreciação HTTP de teste. Lint e sintaxe JavaScript aprovados. Wheel não editável em venv limpo e smoke instalado de CLI/API/L0, importação, reimportação, rebuild e backup/restauração aprovados. A interface instalada recuperou uma entrega HTTP perdida sem aumentar o contador do provider simulado.
