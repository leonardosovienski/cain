# Resposta verificável de campos — 2026-09-12

## Resultado

O caso de revisão que omitira a trial e afirmara indevidamente a disponibilidade
da amostra agora devolve os valores literais disponíveis e explicita o que não foi
localizado nos trechos selecionados. O caso real conhecido e uma variante passaram.
São casos de desenvolvimento; não são avaliação reservada ou aceite global.

A menor mudança adotada é um caminho determinístico para consulta explícita de
múltiplos campos, na etapa `support` de revisão. O modelo e sua configuração foram
preservados; nesse caminho não há inferência. Isso corrige a resposta dessa tarefa,
não demonstra melhora da capacidade de síntese livre do modelo.

## Referências e implementação

Base: `88bfd20681ba9c7a73f343c62a0973066d809bf8`.
Checkout isolado: `C:/CAIN/work/verified-field-review-20260912`.
Branch local: `fix/verified-field-review-20260912`.

`field_review.py` reconhece apenas consultas explícitas com dois ou mais campos
entre estado, trial, motivo e amostra, sem termos interpretativos desconhecidos.
Usa os cards já selecionados. Formatos aceitos: campos filhos diretos da identidade
(`state/status/estado`, `trial/trial_id/trial_name/ensaio`, `reason/motivo/justificativa`,
`sample/sample_size/amostra/tamanho_da_amostra`) e mapas explícitos
`hypotheses/<identidade>` e `hypothesis_trials/<identidade>`. Esses nomes são o
contrato suportado, não interpretação arbitrária de quaisquer chaves JSON.

Valores inteiros são preservados, inclusive negações, qualificadores e unidades.
Não se extraem números de texto livre. Campos não reconhecidos, aninhamentos não
suportados ou campos fora da seleção não são declarados inexistentes. Valores
conflitantes são mostrados com referências, sem escolher uma versão como atual.

`analysis.review` revalida texto completo por hash, offsets e política antes de
entregar `status=literal_fields`, campos estruturados, texto compatível com a UI,
referências e método `literal-json-field-review/1`. `model_calls=0` e
`generation.called=false`. O acesso continua passando pelo recorte admitido para
geração; nenhuma permissão foi ampliada mesmo sendo um caminho sem inferência.

Workflow novo: `/8`, impedindo que jobs antigos pendentes executem sob semântica
nova. Leitura/cancelamento históricos permanecem. Prompt da geração livre segue
`addressable-review/5` e suas respostas continuam sem certificação semântica.
Não houve alteração no Historian/Snapshot, Bundle, challenge ou synthesis.

## Validação

- Na base, as quatro regressões iniciais tiveram **3 falhas e 1 aprovação**.
- Suíte final: **497 passaram, 1 skip, 2 avisos de depreciação** em Windows.
- Ruff dos arquivos alterados e `git diff --check`: aprovados.
- API: criar job e avançar support com modelo que falha se chamado; resposta
  completa, zero inferências e workflow concluído.
- Testes de identidade distinta/Unicode, negação no pedido, perguntas interpretativas,
  valores conflitantes, qualificadores/unidades e revogação durante resolução.
- Caso real anterior reaproveita a rubrica congelada. Estado e trial presentes;
  motivo e amostra explicitamente não localizados nos trechos selecionados.
- Variante real passou com os mesmos critérios. Não se transferiram números entre
  identidades. A existência de informação em outros trechos não é negada.

As fontes e respostas privadas estão em
`C:/CAIN/work/verified-field-review-receipts-20260912`, fora do Git:
`baseline.txt`, `suite.txt`, `suite.xml`, `rubric-before.json`,
`real-verification.json` e banco isolado. O controle anterior permanece intacto em
`C:/CAIN/work/evidence-selection-receipts-20260912/corrected-selection-real.json`.
Os checks do caso real são determinísticos e revisados pelo implementador, sem
juiz independente. Configuração preservada: Qwen3.5:0.8b, temperatura 0, seed 42,
contexto 8192, num_predict 768, think=false, timeout 240; não chamado nesta correção.

## Uso e limitações

Ambiente novo: `http://127.0.0.1:8880`.
Pesquisa → identidade → pergunta explícita de estado/trial/motivo/amostra → fluxo
→ etapa Analisar suporte. O botão separado de explicação Historian mantém seu
comportamento anterior. Perguntas interpretativas e consultas fora do contrato
seguem a geração livre, sem nova garantia de precisão. Renderer de campos em português.

Para repetir a suíte, no checkout:

```powershell
$env:PYTHONPATH='C:\CAIN\work\verified-field-review-20260912\src'
& C:\CAIN\work\independent-review-env-20260911\Scripts\python.exe -m pytest -q
```

Para reiniciar a instância isolada, no diretório de recibos, usando o mesmo ambiente:

```powershell
& C:\CAIN\work\independent-review-env-20260911\Scripts\python.exe -m uvicorn preview_app:app --host 127.0.0.1 --port 8880
```

A entrega anterior em 8879 é o controle. A instalação principal, bancos originais,
modelos e políticas não foram alterados. Nenhum push, merge ou instalação de wheel.
Reversão: parar apenas o servidor candidato; o estado operacional anterior continua
preservado. Runtime testado é o código-fonte deste checkout no ambiente de testes,
não um wheel novo nem Linux.

Próximo trabalho delimitado: avaliar consultas interpretativas fora deste contrato
com critérios próprios, sem apresentar campos literais como prova causal ou
científica. A disponibilização na instalação principal depende de autorização
específica, ausente no mandato original.

## Demonstração visual

Criado e executado pela interface da porta 8880 o job
`21077e48d99841fbae94d19fe8435094`: inspect, search, entities e support.
A etapa support exibiu estado, trial e as duas declarações de não localização,
com as duas citações, em 0,13 s nesta execução. Isso é tempo de uma observação,
não benchmark de desempenho. O job foi cancelado depois da etapa alvo, preservando
4/6 passos; challenge/synthesis não foram executados nem considerados corrigidos.
O recibo completo está em `ui-job.json` no diretório privado desta rodada.
