#!/bin/bash
# take.sh TREE OUT APPEARANCE W H
S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad
D=$S/work/yellow_review_look
TREE=$1; OUT=$2; A=$3; FW=$4; FH=$5
mkdir -p $OUT $S/tools/field/run
before=$(ls $S/tools/field/run)
cd $D && GRAPHITE_APPEARANCE=$A REHEARSAL_MODEL=x REHEARSAL_SCRIPT=${SCRIPT:-$D/code/look.py} PYTHONUNBUFFERED=1 QT_QPA_PLATFORM=offscreen timeout 600 nice -n 10 unshare --pid --fork --mount-proc --kill-child $S/work/venv/bin/python -u -B $S/tools/field/nomodel.py $TREE $OUT $FW $FH 2>&1 | grep -v "propagateSizeHints\|^QFont::\|qt.qpa\|does not support"
for d in $(ls $S/tools/field/run); do echo "$before" | grep -qx "$d" || rm -rf $S/tools/field/run/$d; done
