# Auditoria ampliada do CAIN — 12/09/2026

A rodada testa a instalação local: conversa, memória, projetos, documentos, busca, API/CLI/MCP, Historian, workflows, restauração e streaming. Não certifica todos os casos possíveis ou a precisão geral do modelo.

## Defeito encontrado e correção

Os checks mecânicos da busca passaram, mas o modelo negou a chave explicitamente presente no documento e se apoiou no histórico. Separar documentos e histórico não eliminou a resposta falsa. A busca composta pela CLI/API agora entrega trechos literais e proveniência, sem síntese do modelo. O histórico é fallback apenas quando não há documento recuperado. O agente de baixo nível conserva síntese somente quando escolhido diretamente; a instalação operacional não a seleciona para busca.

Os testes de regressão verificam documentos conflitantes com o histórico, isolamento entre projetos, ausência de chamada de geração na busca e presença literal do fato. O avaliador funcional foi atualizado para verificar esse contrato, em vez de exigir geração onde ela foi removida. O verificador real ganhou três checks que teriam rejeitado a primeira resposta.

## Evidência e limites

Antes da nova correção: 457 testes passaram e um foi ignorado no Windows. Os 14 checks da API real passaram, embora a inspeção textual tenha encontrado falhas semânticas. Após a busca literal, 17 checks da API real passaram e a chave documental ficou visível sem inferência. Resultados finais do pacote, recibos e instalação ficam em C:/CAIN/entregas/full-operational-audit-20260912; logs intermediários em C:/CAIN/work/full-operational-audit-20260912.

Os três workflows reais concluíram seis etapas cada e preservaram registros/cobertura. Restauração dos três acervos sem pastas dos produtores passou. Streaming respondeu OK; visão identificou a imagem sintética vermelha. MCP instalado inicializou, anunciou quatro ferramentas e consultou H6. Projetos, documento, preferência de projeto, nova conversa e feedback foram conferidos na interface isolada.

Resumos livres ainda alteraram nuances de autorização/data em ensaios reais. Ajustar o prompt não demonstrou solução robusta e essa tentativa não foi promovida. Qualidade semântica geral permanece reprovada/inconclusiva, separada da validação técnica. Workflows concluídos não certificam interpretações, independência dos papéis ou validade científica. Sem reprodução da pesquisa ou edição de fontes dos produtores. A auditoria terminou localmente; a publicação das correções foi autorizada depois, na branch `fix/historian-integrity-20260912`. Veja [Continuidade](../../CONTINUIDADE.md).


## Instalação final confirmada

Código `0c8814901d3d365a2eec4b0c7386b59f460d349d`, wheel SHA-256
`a09b56c744260468702bd4a8ab71e132e8ede354f34e8c0ef491d5783ced2e1b`.
Suíte final: 459 passes, zero falhas/erros, um skip de symlink Windows e duas
advertências de depreciação do cliente de testes. Ruff passou. Os 55 arquivos
instalados conferiram com o wheel; pip check passou e health respondeu ok.
Health não executa inferência; os ensaios reais estão registrados separadamente.
A suíte usou o pacote em destino isolado; alguns testes de subprocesso fixam
seu próprio caminho de importação. Não se afirma que cada subprocesso testou
exclusivamente o wheel. A CLI, MCP e streaming foram exercitados no runtime principal.

A consulta da interface final retornou o fato literal e preservou a data não
definida, com fonte e versão. Bancos e política principais mantiveram seus
hashes durante os testes e a instalação. Servidor temporário encerrado;
principal disponível na porta 8877. Recibos privados permanecem apenas locais.
