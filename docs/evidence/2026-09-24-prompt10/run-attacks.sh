#!/usr/bin/env bash
# P10 runtime: the attack suite against the real Docker Desktop engine (called from WSL).
set -euo pipefail
REPO=/home/superleo13/predictors/work/cain-p10
VENV=/home/superleo13/predictors/runtime/cain-p10/venv
RUN=/mnt/c/Users/Superleo13/AppData/Local/Temp/claude/E--D16-DADOS/2c2e4552-3830-4daa-a8e4-3d40ad96f6a9/scratchpad/p10-run
DOCKER="/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"
IMAGE="python:3.13-slim@sha256:8d9d0b8bcf6506481eae4907c18f5e3e7902e629f5f6d684f9e7c32e85e3ddf0"
OUT=$REPO/docs/evidence/2026-09-24-prompt10
mkdir -p "$RUN/evaluator" "$RUN/holdout" "$RUN/allowed" "$RUN/ws" "$OUT"
cp "$REPO/loops/brasileirao/evaluator.py" "$RUN/evaluator/evaluator.py"
printf 'value\n0.1812\n0.2093\n' > "$RUN/holdout/holdout.csv"
printf 'value\n1\n2\n3\n4\n' > "$RUN/allowed/allowed.csv"
sha256sum "$RUN/evaluator/evaluator.py" "$RUN/holdout/holdout.csv" "$RUN/allowed/allowed.csv" | sed "s#$RUN#<run>#" > "$OUT/inputs.sha256"
cd "$REPO"
start=$(date -u +%FT%TZ)
"$VENV/bin/cain" sandbox --docker "$DOCKER" --windows-paths --image "$IMAGE" --timeout 30 \
  --workspace-root "$RUN/ws" attacks \
  --evaluator-file "$RUN/evaluator/evaluator.py" --holdout-file "$RUN/holdout/holdout.csv" \
  --allowed-data "$RUN/allowed/allowed.csv" --tamper-evaluator --output "$OUT/attacks-report.json" \
  | tee "$OUT/attacks-summary.json"
echo "started $start finished $(date -u +%FT%TZ)"
sha256sum "$RUN/evaluator/evaluator.py" | sed "s#$RUN#<run>#"
cmp "$REPO/loops/brasileirao/evaluator.py" "$RUN/evaluator/evaluator.py" && echo "evaluator copy restored byte-identical"
"$DOCKER" ps -a --filter name=cain-attempt --format '{{.Names}}' | wc -l | sed 's/^/leftover containers: /'
