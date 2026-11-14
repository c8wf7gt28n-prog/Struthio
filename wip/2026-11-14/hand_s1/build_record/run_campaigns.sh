#!/bin/bash
# The scenes set through the campaign, in the Kasandra appearance and then in Graphite's own, on a copy of the worktree.
B=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/hand_build
VENV=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/venv/bin/python
FIX=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/campaign_fixtures
cd $B/camp_tree
GRAPHITE_APPEARANCE=kasandra QT_QPA_PLATFORM=offscreen nice -n 10 unshare --pid --fork --mount-proc --kill-child $VENV -B tools/campaign.py run --set scenes --fixtures $FIX --out $B/${1:-campaign}_kasandra > $B/${1:-campaign}_kasandra.log 2>&1
env -u GRAPHITE_APPEARANCE QT_QPA_PLATFORM=offscreen nice -n 10 unshare --pid --fork --mount-proc --kill-child $VENV -B tools/campaign.py run --set scenes --fixtures $FIX --out $B/${1:-campaign}_graphite > $B/${1:-campaign}_graphite.log 2>&1
echo CAMPAIGNS_DONE
