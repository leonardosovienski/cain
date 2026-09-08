# Cain — esqueleto executável de pesquisa

Implementação local derivada dos cinco documentos enviados em `files.zip`.
O núcleo e o harness permitem testes de engenharia. A identidade, a adaptação e o
roteamento continuam provisórios. Os resultados do dublê não demonstram a hipótese do TCC.

## Começar

Requer Python 3.11 ou superior. Na pasta deste projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m cain run "Resuma: Cain coordena agentes e mantém estado entre sessões." --intent resumo
.\.venv\Scripts\python -m pytest -q
```

Por padrão, usa um dublê determinístico, sem download de modelos ou chamadas externas.
Consulte `RELATORIO_EXECUCAO.md` para resultados verificados, limitações e próximos passos.

Para repetir a execução técnica de avaliação:

```powershell
.\.venv\Scripts\python -m cain.evaluation --mode smoke --output evaluation/results
```

## Ollama local

Com Ollama instalado e um modelo já obtido, use o mesmo nome que aparece em `ollama list`:

```powershell
.\.venv\Scripts\python -m cain run "Analise uma função Python que soma dois números" --intent codigo --provider ollama --model qwen2.5:3b
```

`qwen2.5:3b` é somente um exemplo configurável; nenhum modelo foi baixado nesta entrega.
Temperatura e seed são configuráveis com `--temperature` e `--seed`.
`--db`, `--user` e `--session` permitem repetir interações sobre o mesmo estado.

## API local

```powershell
.\.venv\Scripts\python -m uvicorn cain.api:create_app --factory --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000/docs`. O endpoint `POST /run` recebe
`user_id`, `session_id`, `payload` e `intent` opcional. `GET /health` informa o estado
da aplicação. A API é uma demonstração local sem autenticação. Configuração via
`CAIN_DB`, `CAIN_PROVIDER`, `CAIN_MODEL` e `CAIN_OLLAMA_URL`.

## Documentação

- [Relatório da execução](RELATORIO_EXECUCAO.md)
- [Auditoria bibliográfica](docs/research/auditoria-fontes.md)
- [Notas de leitura](docs/research/notas/README.md)
- [Posicionamento e propostas de pesquisa](docs/research/posicionamento.md)
- [Instrumento de avaliação](docs/research/avaliacao-tecnica.md)
- [Caminho para a UFPR](docs/research/caminho-ufpr.md)
- [ADRs disponíveis](docs/adr/README.md)
- [Escolhas de implementação](docs/architecture/decisoes-de-implementacao.md)

`ESTADO_DO_PROJETO.md` contém o mestre recebido, com aviso de estado atual.
As cópias byte a byte dos anexos estão em `docs/historico/importacao/`.

O workflow GitHub Actions executa lint e testes em Python 3.11, 3.12 e 3.13.
`requirements-dev.lock` registra as versões usadas na verificação local em Python 3.12.

## Limites desta versão

Busca lexical sobre corpus local; índice semântico ChromaDB pendente. Adaptação
no-op; perfil não aprende preferências. Regras de roteamento provisórias. Sem
adaptador de API comercial. A avaliação formal e o piloto com modelo real dependem
de fechar o protocolo e disponibilizar os instrumentos/modelos necessários.
