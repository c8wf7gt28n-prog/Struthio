#!/bin/bash
# usage: merge_one.sh OUTDIR SAVEDIR KEY WORKTREE_AGENT_ID  -> applies, union-merges the registration files, rebuilds, smokes
S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad
cd /home/user/Struthio || exit 9
B=$1; SV=$2; K=$3; A=$4; mkdir -p $SV
[ -n "$A" ] && { git worktree remove -f -f .claude/worktrees/agent-$A 2>/dev/null; git branch -D -q worktree-agent-$A 2>/dev/null; }
cp $B/$K.patch $B/$K.progress.md $B/$K.build.result.json $SV/ 2>/dev/null
git apply -3 $B/$K.patch 2>&1 | grep -iE "error|conflict"
git checkout HEAD -- docs/GRAPHITE_0.1_REGISTRY.json
for f in $(git diff --name-only --diff-filter=U); do case $f in workbench/engineering_*.py|workbench/activity.py) sed -i -E '/^(<<<<<<< ours|=======|>>>>>>> theirs)$/d' $f; git add $f; echo "union-merged $f";; *) echo "REAL CONFLICT $f"; exit 3;; esac; done
python3 $S/work/fix_observers.py workbench/activity.py; git add workbench/activity.py
$S/work/finish_merge.sh
