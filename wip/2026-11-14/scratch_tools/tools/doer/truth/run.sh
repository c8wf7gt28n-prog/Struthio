#!/bin/bash
# usage: run.sh script.py outname
S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad
D=$S/tools/doer/truth
cd $S/work && REHEARSAL_MODEL=x REHEARSAL_SCRIPT=$D/$1 unshare --pid --fork --mount-proc --kill-child timeout 300 ./venv/bin/python -B $S/tools/field/nomodel.py /home/user/Struthio $D/out 1920 1200 > $D/out/$2 2>&1
echo exit $? ; wc -l $D/out/$2
