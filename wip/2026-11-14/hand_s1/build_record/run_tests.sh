#!/bin/bash
# usage: run_tests.sh <tree> <outdir> module...   (one module at a time, each in its own pid namespace)
TREE=$1;OUT=$2;shift 2;mkdir -p "$OUT"
VENV=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/venv/bin/python
for m in "$@";do
  start=$(date +%s)
  (cd "$TREE" && QT_QPA_PLATFORM=offscreen nice -n 10 unshare --pid --fork --mount-proc --kill-child $VENV -B -m unittest tests_integrated.$m) > "$OUT/$m.log" 2>&1
  rc=$?;end=$(date +%s)
  echo "$m rc=$rc secs=$((end-start)) $(tail -3 "$OUT/$m.log" | tr '\n' ' ')" >> "$OUT/summary.txt"
done
echo DONE >> "$OUT/summary.txt"
