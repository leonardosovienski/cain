# CAIN Supply — retomar sem o chat

## Retomada após o diagnóstico de partida — 12/09/2026

Leia primeiro [o diagnóstico, as evidências e o próximo caso](DIAGNOSTICO_PARTIDA_20260912.md). Diagnóstico encerrado; verificação de H4 pela interface ainda não executada. A branch de entrega é `validation/cain-supply-completion-20260912`; a instalação principal permanece separada. Este é o próximo trabalho recomendado; as instruções de execução das rodadas anteriores abaixo são históricas.


Esta é a entrada atual da entrega de engenharia. A branch é `validation/cain-supply-completion-20260912`; o checkout local é `C:/CAIN/work/supply-publish-20260912`. O código final agora está diretamente em `src/`, além do overlay preservado. Não usar `main` ou a instalação ativa como substitutos deste candidato.

Leia [o fechamento](FECHAMENTO_DO_PROMPT.md), [o guia de uso](USER_ACCEPTANCE.md) e [o handoff de evidências](FINAL_HANDOFF.md). O mapa [LOCAL_LAYOUT.json](LOCAL_LAYOUT.json) identifica pastas, bancos, políticas, ambiente e histórico. A pasta de entrega local é `C:/CAIN/entregas/supply-20260912`.

## Estado e limites

Base `d00bbc6fb910b3c51be6720d21012f4655258468adb7d7335451974929c58752`, código instalado `7da108d0172b7ccc2675404b7dbf0b8a21ad248ee814ea14f199225003d23861`. Windows: 575 aprovados e um skip de privilégio. Linux 3.11–3.14: 574 aprovados e dois skips exclusivos do Windows por versão; evidência anterior em [CI do candidato](https://github.com/leonardosovienski/cain/actions/runs/34702803998).

A rodada suplementar local possui identidade `3f3b34cf116201aea601459668b70480570fa9583575e727228e75fd0c2a8063`: 33 documentos reais de três fontes, 47 chamadas, persistência/restore/revogação aprovados e comparação estrutural neutra. Não é ganho de aprendizado. Qualidade semântica do modelo continua inconclusiva; fontes restritas não foram liberadas por conveniência.

Pronto para revisão de congelamento da engenharia delimitada; preview limitado em staging. Não houve merge, release, implantação ou alteração da instância ativa. Seu aceite pessoal não foi presumido.

## Abrir e encerrar

```powershell
& 'C:/CAIN/work/supply-final-20260912/venv/Scripts/python.exe' 'C:/CAIN/work/supply-final-20260912/web_preview.py' --legacy
```

Abra `http://127.0.0.1:8889`; encerre com Ctrl+C nesse terminal. O guia contém consultas CLI e seus scopes. Nenhum serviço é iniciado automaticamente por esta organização.

## Reconstrução e continuidade

O Git contém código, testes, recursos empacotados, workflows, manifestos, documentação e um arquivo dos scripts locais em `.ci/completion/local-delivery-harness.zip`. O arquivo de scripts é material de reprodução/consulta, não um instalador nem uma ordem para executar tudo. Os scripts históricos criam destinos exclusivos e alguns verificam commits antigos intencionalmente.

Bancos, objetos recebidos, pesos de modelos, ambientes e saídas privadas permanecem nas pastas originais indicadas no inventário. Não presumir que um clone do Git recupera esse conteúdo. Para recuperar o acervo, use os backups e o procedimento de archive restore registrados no handoff, em destino novo. Não remover as pastas históricas ou reais para "limpar" a máquina.

As referências a branches, ausência de Linux ou instalação nos relatórios anteriores são históricas. O recibo local `GIT_DELIVERY.json` registra o commit final e a conferência remota desta publicação; os relatórios de testes permanecem vinculados aos respectivos commits/candidatos. Novas alterações exigem nova identidade e validação pertinente.

Para continuar: leia esta entrada, confira `git status`, `git rev-parse HEAD` e `git ls-remote origin refs/heads/validation/cain-supply-completion-20260912`, preserve alterações encontradas e use o candidato/ambiente indicado. Não misture commits dos produtores com este repositório consumidor.
