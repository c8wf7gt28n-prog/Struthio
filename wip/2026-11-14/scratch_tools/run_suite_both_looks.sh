#!/bin/bash
# The full suite on a fresh COPY of the tracked tree (without wip/ and .claude/), every module isolated, two at a time,
# in each look named on the command line (default: "default kasandra"). Results: $T/summary.<look>.txt and $T/logs.<look>/.
# Usage: run_suite_both_looks.sh [look ...]      S and REPO may be set in the environment.
REPO=${REPO:-/home/user/Struthio}
S=${S:-/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad}
PY=$S/work/venv/bin/python; T=${T:-$S/work/t084}
LOOKS="${*:-default kasandra}"
rm -rf $T/tree; mkdir -p $T/tree; cd $REPO && git ls-files -z | grep -z -v -E '^(wip/|\.claude/)' | xargs -0 cp --parents -t $T/tree
cd $T/tree && git -C $REPO rev-parse HEAD > $T/commit.txt
QT_QPA_PLATFORM=offscreen $PY tools/record_registry.py --check > /dev/null 2>&1 || { echo "SEED NOT CURRENT in the copy"; exit 2; }
one(){ m=$1; h=$(mktemp -d); s=$(date +%s)
  if [ "$LOOK" = default ]; then e="env -u GRAPHITE_APPEARANCE"; else e="env GRAPHITE_APPEARANCE=$LOOK"; fi
  nice -n 19 unshare --pid --fork --mount-proc --kill-child timeout 900 $e HOME=$h QT_QPA_PLATFORM=offscreen $PY -B -m unittest tests_integrated.$m > $T/logs.$LOOK/$m.log 2>&1; rc=$?
  echo "$m exit=$rc $(( $(date +%s)-s ))s $(grep -E '^Ran |^OK|^FAILED' $T/logs.$LOOK/$m.log | tr '\n' ' ')" >> $T/summary.$LOOK.txt; rm -rf $h; }
export -f one; export PY T
for LOOK in $LOOKS; do export LOOK; rm -rf $T/logs.$LOOK; mkdir -p $T/logs.$LOOK; : > $T/summary.$LOOK.txt; s0=$(date +%s)
  ls tests_integrated/test_*.py | xargs -n1 basename | sed 's/\.py$//' | xargs -P2 -I{} bash -c 'one {}'
  echo "LOOK $LOOK: modules=$(wc -l < $T/summary.$LOOK.txt) failing_modules=$(grep -c -v 'exit=0' $T/summary.$LOOK.txt) tests=$(awk '{for(i=1;i<=NF;i++) if($i=="Ran") t+=$(i+1)} END {print t}' $T/summary.$LOOK.txt) seconds=$(( $(date +%s)-s0 )) commit=$(cut -c1-7 $T/commit.txt)"
  grep -v 'exit=0' $T/summary.$LOOK.txt
done
