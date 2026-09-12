# Auditoria ampliada do CAIN — 12/09/2026

A rodada testa a instalação local: conversa, memória, projetos, documentos, busca, API/CLI/MCP, Historian, workflows, restauração e streaming. Não certifica todos os casos possíveis ou a precisão geral do modelo.

## Defeito encontrado e correção

Os checks mecânicos da busca passaram, mas o modelo negou a chave explicitamente presente no documento e se apoiou no histórico. Separar documentos e histórico não eliminou a resposta falsa. A busca composta pela CLI/API agora entrega trechos literais e proveniência, sem síntese do modelo. O histórico é fallback apenas quando não há documento recuperado. O agente de baixo nível conserva síntese somente quando escolhido diretamente; a instalação operacional não a seleciona para busca.

Os testes de regressão verificam documentos conflitantes com o histórico, isolamento entre projetos, ausência de chamada de geração na busca e presença literal do fato. O avaliador funcional foi atualizado para verificar esse contrato, em vez de exigir geração onde ela foi removida. O verificador real ganhou três checks que teriam rejeitado a primeira resposta.

## Evidência e limites

Antes da nova correção: 457 testes passaram e um foi ignorado no Windows. Os 14 checks da API real passaram, embora a inspeção textual tenha encontrado falhas semânticas. Após a busca literal, 17 checks da API real passaram e a chave documental ficou visível sem inferência. Resultados finais do pacote, recibos e instalação ficam em C:/CAIN/entregas/full-operational-audit-20260912; logs intermediários em C:/CAIN/work/full-operational-audit-20260912.

Os três workflows reais concluíram seis etapas cada e preservaram registros/cobertura. Restauração dos três acervos sem pastas dos produtores passou. Streaming respondeu OK; visão identificou a imagem sintética vermelha. MCP instalado inicializou, anunciou quatro ferramentas e consultou H6. Projetos, documento, preferência de projeto, nova conversa e feedback foram conferidos na interface isolada.

Resumos livres ainda alteraram nuances de autorização/data em ensaios reais. Ajustar o prompt não demonstrou solução robusta e essa tentativa não foi promovida. Qualidade semântica geral permanece reprovada/inconclusiva, separada da validação técnica. Workflows concluídos não certificam interpretações, independência dos papéis ou validade científica. Sem reprodução da pesquisa ou edição de fontes dos produtores. Sem push nesta rodada.
