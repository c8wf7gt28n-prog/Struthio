#!/bin/bash
# usage: run.sh script.py [nomodel|model]  -> runs the offscreen window on the PRISTINE HEAD snapshot
D=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/memory-programs
S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad
cd $S/work && REHEARSAL_MODEL=x REHEARSAL_SCRIPT=$1 timeout ${3:-300} unshare --pid --fork --mount-proc --kill-child ./venv/bin/python -B $S/tools/field/nomodel.py ${PROGRAM:-$D/pristine} $D/out 1920 1200 2>&1
