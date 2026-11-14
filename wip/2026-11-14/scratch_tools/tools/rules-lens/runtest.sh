#!/bin/bash
# usage: runtest.sh <label> <tree> <module>
cd "$2" && TMPDIR=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/tmp HOME=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/home PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen timeout 900 /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/venv/bin/python -B -m unittest tests_integrated.$3 > /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/tests/$1/$3.out 2>&1
echo "$1 $3 exit $?" >> /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens/tests/exits.txt
