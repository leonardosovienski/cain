# Zhong et al. — MemoryBank: Enhancing Large Language Models with Long-Term Memory

**Fonte:** [AAAI, artigo e PDF](https://ojs.aaai.org/index.php/AAAI/article/view/29946), pp. 19724–19731. **Versão:** publicação 24/03/2024, 38(17). **DOI:** [10.1609/aaai.v38i17.29946](https://doi.org/10.1609/aaai.v38i17.29946). **Consulta:** 07/09/2026.

**O que mede.** Recuperação de memórias e respostas personalizadas no cenário de companhia SiliconFriend.

**Como mede.** Histórico, resumos e retrato do usuário; atualização inspirada na curva de esquecimento. Avaliação inclui exemplos reais e 194 sondas bilíngues sobre dez dias simulados para 15 usuários; humanos pontuam recuperação, correção, coerência e preferência entre variantes.

**O que achou.** As variantes recuperam informações e ajustam respostas ao perfil; resultados variam por modelo/idioma. Exemplos de empatia incluem ajuste com dados de diálogo psicológico. Não transferir benefícios globais do SiliconFriend para uma arquitetura sem fine-tuning, nem supor eficácia clínica.

**O que implica para o Cain — proposta.** ADR-0007 deve separar evidência de preferência, atualização do perfil e retenção de episódios. Comparar retenção integral, recência e decaimento; curvas humanas não justificam sozinhas uma política ótima para software. Preferências explícitas precisam de política própria de revisão. Medir convergência à preferência conhecida, sem tratar qualquer alteração de estado como aprendizado. Persistência de fatos e personalidade do agente são construtos distintos.
