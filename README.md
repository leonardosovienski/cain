# Cain 0.4.7 — conversa, memória e pesquisa local L0

<!-- DOC-SYNC-20260912 -->
> **Estado de publicação em 12/09/2026:** leia [a continuidade atual](PUBLICATION_STATUS_20260912.md). Branch `feature/research-bundle-v1`. O código deste projeto foi publicado na branch indicada. O candidato CAIN Supply permanece sem aprovação de estabilização. Afirmações anteriores de “sem push” descrevem a etapa histórica anterior à autorização.
<!-- /DOC-SYNC-20260912 -->


**Atualização operacional autorizada:** a revisão foi instalada e publicada na branch
`review/individual-models-20260911`. Leia [o recibo de instalação](docs/research/INSTALACAO_REVISAO_20260911.md).
As afirmações de não instalação abaixo descrevem a etapa anterior à autorização.

Entrega atual: [streaming, visão, busca, relações, debate, workflows e MCP](docs/DELIVERY_047.md).
Os resultados de versões anteriores abaixo são históricos.

Esta branch contém a [validação individual de modelos e relatos de pesquisa](docs/research/TESTES_INDIVIDUAIS_20260911.md)
e correções isoladas. Os testes não substituíram a instalação principal nem
estabeleceram confiabilidade da interpretação livre dos modelos.

A revisão deste chat está em [Revisão independente](docs/research/REVISAO_INDEPENDENTE_20260911.md),
na branch `review/individual-models-20260911`. Ela separa defeitos herdados,
regressões da entrega anterior e erros dos modelos. Não houve merge nem instalação
operacional dessa revisão; os relatórios anteriores permanecem como histórico.

Cain usa um modelo local para resumir, gerar/analisar código e consultar fontes.
Guarda preferências explícitas em SQLite e mostra quais valores se aplicam à conversa.

O piloto **[L0 Historian](docs/RESEARCH_L0.md)** acrescenta importação de publicações
admitidas, consulta determinística, cobertura e inspeção de evidências na CLI e na
interface. Importar e consultar não exige Ollama. A explicação opcional usa o provider
existente; conversa e feedback não se tornam evidência científica.

## Instalação principal nesta máquina

Use `C:\CAIN\ABRIR_CAIN.cmd` e http://127.0.0.1:8877. Essa instalação contém
runtime próprio e bancos em `C:\CAIN\dados`. Para retomar sem o chat, leia
[CONTINUIDADE.md](CONTINUIDADE.md) e o [índice documental](docs/README.md).

## Instalação genérica do repositório

Dê dois cliques em **[ABRIR_CAIN.cmd](ABRIR_CAIN.cmd)**. A interface abre em
[127.0.0.1:8000](http://127.0.0.1:8000/); o inicializador reutiliza o Python e
os modelos já instalados e inicia os serviços locais quando necessário.
[INICIAR_CAIN.cmd](INICIAR_CAIN.cmd) continua disponível para conversar pelo terminal.

1. Crie um projeto pelo botão **+**. Cada projeto tem documentos e conversas próprios.
2. Em **Documentos**, adicione um `.txt`, `.md` ou `.rst` de até 256 KiB.
3. Peça: “Busque nos documentos o que está definido sobre…”. Abra os trechos abaixo da resposta para conferir a fonte e a versão.
4. Declare “Neste projeto, prefiro respostas em passos” ou ajuste **Minha memória**.
5. Use “Só nesta resposta…” para uma exceção temporária. Nova conversa conserva a preferência do projeto, mas não a da conversa anterior.

O contexto **Geral** consulta os caminhos de `cain.toml`. Projetos consultam apenas
seus próprios arquivos e histórico. O nome de usuário seleciona um perfil local;
não é uma conta autenticada. O serviço permanece em execução ao fechar a página.

## O que mudou

- Interface com conversas persistentes, projetos, importação de textos e painel de preferências.
- Preferências de formato, extensão e idioma por resposta, conversa, projeto ou usuário, com origem, remoção e validade opcional.
- Busca híbrida por palavras e embeddings locais, com cache por versão do modelo e trechos rastreáveis.
- Feedback “Foi útil” ou motivo de problema. É registrado para revisão; não altera o perfil automaticamente.
- Roteamento por JSON com schema quando o LLM é necessário; perguntas diretas sobre o perfil usam o estado armazenado.

A precedência é **resposta → conversa → projeto → padrão geral**. Remover ou expirar
uma preferência revela o valor do escopo inferior. A auditoria anterior permanece
no banco; remoção de preferência não apaga conversas. Sem escopo declarado, uma
preferência explícita vira padrão geral. O seletor do campo de mensagem permite
escolher o escopo; conflitos com a frase são recusados, sem salvar globalmente.

## Instalar em outro computador

É necessário Python 3.11+. Ollama é necessário para inferência e embeddings, mas não
para ajuda, importação, consulta L0 ou abertura da interface. Pesos não acompanham o pacote.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --find-links vendor -e ".[api]"
ollama pull qwen2.5:3b
ollama pull qwen3-embedding:0.6b
.\ABRIR_CAIN.cmd
```

O `cain.toml` deste checkout seleciona `qwen3.5:0.8b`. O inventário local observado
em 11/09/2026 também contém `qwen2.5:3b` e `qwen3-embedding:0.6b`; não contém
`qwen3.5:4b`. A [comparação v0.3](docs/research/inspecao-modelos-v03.md) é histórica
e não deve ser usada como inventário atual de modelos.

`cain.toml` fixa o digest observado do embedding. Se o download da tag retornar
outros pesos, a busca recusa a divergência: confira `/api/tags` do Ollama e atualize
o digest conscientemente. Para operar sem embeddings, configure `search.mode =
"lexical"`. Falhas de inferência não acionam um modelo simulado nem repetição oculta.

## Configuração e comandos

Os exemplos com `python` pressupõem o ambiente virtual ativo (`.\.venv\Scripts\Activate.ps1`).
Também é possível substituir `python` pelo caminho `.\.venv\Scripts\python.exe`.

`CAIN_PROVIDER`, `CAIN_MODEL`, `CAIN_DB` e `CAIN_OLLAMA_URL` substituem as opções
correspondentes. Caminhos no TOML são resolvidos a partir de `cain.toml`;
`--source` e `--db` fornecidos na CLI são relativos ao diretório atual.

```powershell
python -m cain doctor
python -m cain chat --user leo
python -m cain run "Resuma: contratos definem entradas e saídas." --user leo
python -m cain profile --user leo
python -m cain profile --user leo --forget format
python -m cain run "Busque nos documentos o protocolo" --source docs/research
```

Use `--project ID` e `--session ID` nos comandos para selecionar o contexto criado
na interface/API; `--preference-scope session` escolhe onde a declaração vale.
No comando `profile`, `--scope` seleciona o escopo de remoção. O comando de chat
`/esquecer format` atua no padrão geral; a interface oferece controle por escopo.

`--source` aceita arquivos/diretórios de texto e pode ser repetido. `--no-web`
desativa leitura de URLs públicas explícitas. URLs têm limites de conteúdo e tempo;
Cain não oferece um buscador geral da internet. O agente Código entrega texto e
não executa os programas gerados.

## API e verificações

```powershell
powershell -File scripts/start-cain.ps1 -Mode api
python -m pip install --find-links vendor -e ".[dev]"
python -m ruff check .
python -m pytest -q
```

O esquema completo está em `http://127.0.0.1:8000/openapi.json`. A interface funciona
sem bibliotecas externas de navegador. A API local usa somente `127.0.0.1`, verifica
Host/Origin e não tem autenticação; não deve ser publicada como serviço multiusuário.

| Operação | Endpoint |
|---|---|
| Responder e guardar conversa | `POST /run` |
| Consultar/ajustar preferências | `GET /profile/{user}`; `PUT/DELETE /profile/{user}/preferences/{key}` |
| Projetos | `GET/POST /projects/{user}` |
| Documentos de projeto | `GET/POST /projects/{user}/{project}/documents` |
| Conversas e histórico | `GET/POST /sessions/{user}`; `GET /sessions/{user}/{session}` |
| Avaliar uma resposta | `POST /feedback/{turn_id}` |

`/run` recebe `user_id`, `session_id`, `payload`, `project_id` opcional e
`preference_scope` opcional. Retorna fontes, preferências usadas e o perfil atual.
O `turn_id` de respostas novas é o `decision_id`, inclusive no histórico.
Uma falha de geração pode ocorrer depois de uma preferência explícita ser salva;
a interface atualiza o painel também nesse caso.

Os [scripts de verificação](scripts) incluem execução real da API e da recuperação.
O [relatório v0.3](RELATORIO_V03.md) distingue os testes de engenharia da inspeção
de qualidade e documenta as limitações. O painel tem integração WebMCP opcional,
ativada apenas em navegadores que disponibilizem essa API.

## Pesquisa e entregas anteriores

A pesquisa continua provisória: não houve avaliação humana independente,
validação de novidade, aceitação automática de ADRs ou coleta formal.

- [Memória por escopo](docs/architecture/memoria-por-escopo-v03.md)
- [Busca híbrida](docs/architecture/busca-hibrida-v03.md)
- [Comparação dos geradores](docs/research/comparacao-geradores-v03.md)
- [Resultado v0.2](RELATORIO_V02.md) e [entrega inicial](RELATORIO_EXECUCAO.md)
- [Caminho para a UFPR](docs/research/caminho-ufpr.md)
- [Auditoria bibliográfica](docs/research/auditoria-fontes.md)
- [ADRs](docs/adr/README.md)

Os cinco anexos originais e os resultados anteriores estão preservados.
# Ampliação 0.4.5

Consulte [o dossiê de pesquisa e sua validação](docs/DELIVERY_045.md) e
[o inventário ampliado dos rivais](docs/research/capability-inventory-20260911.md).
Nova inspeção local de relações, datas, revisões e lacunas, via interface/API/CLI.

Arquitetura integrada: [factories e revogação](ARCHITECTURE_IMPLEMENTATION.md).
