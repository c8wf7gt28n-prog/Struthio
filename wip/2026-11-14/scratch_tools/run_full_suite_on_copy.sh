#!/bin/bash
# Full suite on a copy of the working tree, two modules at a time, each isolated.
cd /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/t084/tree
PY=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/venv/bin/python
one(){ m=$1; h=$(mktemp -d); s=$(date +%s); nice -n 19 unshare --pid --fork --mount-proc --kill-child env HOME=$h QT_QPA_PLATFORM=offscreen $PY -B -m unittest tests_integrated.$m > /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/t084/logs/$m.log 2>&1; rc=$?; e=$(date +%s); echo "$m exit=$rc $((e-s))s $(grep -E '^Ran |^OK|^FAILED' /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/t084/logs/$m.log | tr '\n' ' ')" >> /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/t084/summary.txt; rm -rf $h; }
export -f one; export PY
: > /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/t084/summary.txt
ls tests_integrated/test_*.py | xargs -n1 basename | sed 's/\.py$//' | xargs -P2 -I{} bash -c 'one {}'
echo "DONE modules=$(wc -l < /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/t084/summary.txt) failing_modules=$(grep -c -v 'exit=0' /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/t084/summary.txt)"
grep -v 'exit=0' /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/t084/summary.txt
awk '{for(i=1;i<=NF;i++) if($i=="Ran") t+=$(i+1)} END {print "tests run:", t}' /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/t084/summary.txt
