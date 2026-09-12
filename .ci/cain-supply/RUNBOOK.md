# Execução Linux preparada — ainda não executada

Este kit NÃO é evidência Linux verde. Somente sua sintaxe Python foi verificada no
Windows. Não executa push, merge, commit, tag, release ou ativação operacional.
O candidato congelado é identificado por CANDIDATE_MANIFEST.json, não pelo HEAD.

## Preparar o host e transportar o candidato

Use Linux real, usuário comum, Python 3.13 ou 3.14 e filesystem Linux nativo.
Não execute testes sobre /mnt/c, drvfs, NTFS, CIFS ou como root. WSL poderá ler
checkouts em /mnt/c apenas para copiá-los para o filesystem nativo; os testes e
seus temporários precisam ficar no filesystem Linux. Registre findmnt/stat.

Os cinco repositórios precisam estar em clones limpos nos HEADs exatos do manifesto.
Os HEADs locais dos produtores não devem ser presumidos disponíveis no GitHub.
De um checkout acessível read-only, prepare cada clone local sem publicar:

```bash
git clone --no-hardlinks --no-checkout /CAMINHO/DA/FONTE/REPO /FS_LINUX/REPOS/REPO
git -C /FS_LINUX/REPOS/REPO checkout --detach HEAD_EXATO_DO_MANIFESTO
```

Não copie inputs científicos restritos só para esta validação. O kit usa fixtures
sintéticas existentes. Caso transportar a história Git inteira não seja autorizado,
pare e disponibilize somente um checkout legítimo do mesmo HEAD com a história
mínima exigida pelos testes; não substitua silenciosamente os testes históricos.

Copie localmente este kit, os overlays e o manifesto. Os overlays contêm somente
arquivos modificados/criados já registrados, incluindo documentação e wheel
candidato; ficam separados nas raízes dos produtores:

- CAIN: `C:/CAIN/work/bundle-linux-validation-20260912/cain/overlay.zip`
- Ecosystem: `C:/CAIN/work/bundle-linux-validation-20260912/ecosystem/overlay.zip`
- Crypto: `C:/CRIPTO/operacao/relatorios/bundle-linux-validation-20260912/overlay.zip`
- Brasileirão: `C:/BRASILEIRAO/work/bundle-linux-validation-20260912/overlay.zip`
- Stocks: `C:/STOCKS/work/bundle-linux-validation-20260912/overlay.zip`

Cada pasta também contém candidate.patch (git diff --binary HEAD), status.txt,
HEAD.txt e repository.json. O overlay preserva os bytes reais, inclusive CRLF,
evitando recriar o patch manualmente. Não use seu wheel como prova de build Linux.

Crie roots.json no host Linux, com caminhos absolutos dos clones preparados:

```json
{"cain":"/FS_LINUX/REPOS/cain","ecosystem":"/FS_LINUX/REPOS/ecosystem","crypto":"/FS_LINUX/REPOS/crypto","brasileirao":"/FS_LINUX/REPOS/brasileirao","stocks":"/FS_LINUX/REPOS/stocks"}
```

Crie overlays.json, apontando cada nome para o respectivo overlay.zip transferido.
Então execute, com os nomes reais dos diretórios:

```bash
python3.13 restore_candidate.py --manifest CANDIDATE_MANIFEST.json --roots roots.json --overlays overlays.json
python3.13 run_linux.py --manifest CANDIDATE_MANIFEST.json --roots roots.json --out /FS_LINUX/RESULTADOS/RODADA_NOVA
```

restore_candidate exige clones limpos, confere HEAD e SHA do overlay e escreve
somente os arquivos declarados. run_linux verifica novamente HEAD, população de
arquivos alterados e cada hash antes dos testes. Divergência causa STOP.
Base Git identifica arquivos não alterados; os 28 arquivos da remediação devem
coincidir byte a byte. Diferença inesperada em fonte relevante exige investigação,
nunca normalização de evidência para obter PASS.

## O que o runner executa

1. Inventário uname/distro/kernel/user/umask/Python/filesystem/mount e equivalência.
2. Builds Linux de Bundle, CAIN, Crypto exportador e Snapshot 1.0.1. Snapshot 1.0.0
   do receptor é reconstruído do commit exato indicado por vendor/provenance.json;
   não se troca o pin do CAIN nem se reutiliza o wheel Windows como build Linux.
3. Venv receptor sem PYTHONPATH para o checkout, pip check, ferramentas de testes.
4. Gate dirigido: suites de Bundle, Snapshot, remediação e test_posix_gate.py.
   O runner exige test_symlink_import_escape executado e nenhum skip nesse gate.
5. Regressão CAIN/Bundle, wheel verifier existente e E2E de consumo instalado.
6. Ambiente separado para Crypto/Snapshot 1.0.1 e testes dos três exportadores.
7. Mini-auditoria novamente, com ataques POSIX e recibos separados.

Comandos, cwd, stdout, stderr, exit codes, XML, hashes dos wheels e E2E são salvos
na raiz NOVA de resultados. Em falha o runner para; preserve o candidato/logs,
classifique a causa e só então ajuste produto ou teste. Não execute novamente
usando a mesma raiz de resultados. A configuração de pip/testes será registrada
nos logs; ela não é instalação operacional.

Os probes POSIX adicionais cobrem symlink/dangling/FIFO/diretório trocado, role
revogada com blob existente/ausente/corrupto, CAS sem permissão, hard link,
fonte alterada/deletada durante leitura, permissão da fonte revogada, falhas de
mkdir/write/fsync/link/DB e ordem observada de sincronização antes do commit.
São testes preparados e NÃO executados nesta rodada.

## O que ainda requer revisão após executar

Uma execução verde do runner NÃO fecha automaticamente o gate de estabilização.
Confira todos os casos das seções 6–28 do mandato, particularmente os observáveis
completos dos dois mundos F03, compatibilidade histórica e configuração efetiva da
transformação. Registre casos individualmente. A suite Ecosystem principal precisa
de ambiente compatível com seus próprios metadados e deve ser registrada à parte
se executada. Não execute suites científicas/coortes ou testes protegidos BR.

O E2E preparado é consumo de fixture existente, não exportação de fontes reais.
Ele torna indisponível a import root antes da consulta/evidence/lineage/verify e
materialização após restore. REAL_PRODUCER_EXPORT_LINUX permanece NOT_EXECUTED.
O E2E real Windows anterior é evidência distinta.

O runner cobre uma versão Python por invocação. Execute separadamente 3.13 e 3.14
se disponíveis; avalie CAIN/contratos/exportador standalone também em 3.11/3.12.
O intervalo integrado dos runtimes principais é >=3.13,<3.15; o standalone declara
>=3.11 sem teto. Não reduza suporte por conveniência. Matriz incompleta é PARTIAL.

Depois de verde e da revisão clean-sheet, avalie o gate completo. Nunca converta
PASS_PREPARED_SUITES em READY_FOR_STABILIZATION_REVIEW automaticamente.
