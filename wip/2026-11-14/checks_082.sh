#!/bin/bash
# 0.8.2 release checks on one exported commit, one after another: the scene through the campaign in both appearances,
# the probe set at two sizes, the crawler and the name sweep in both appearances, the UI gate.
S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad
C=$1; T=$S/work/tree_082c; L=$S/work/logs082; PY=$S/work/venv/bin/python
cd $S/work; rm -rf $T $L t_crawl t_ui; mkdir -p $T $L t_crawl t_ui shots/l082 shots/crawl082 shots/sweep082
git -C /home/user/Struthio archive $C | tar -x -C $T; git -C /home/user/Struthio archive $C | tar -x -C t_crawl; git -C /home/user/Struthio archive $C | tar -x -C t_ui
echo "tree $C"
unshare --pid --fork --mount-proc --kill-child $PY -B $S/tools/tests/run_modules.py $T $S/work/modules_082.json $PY > $L/modules.log 2>&1; echo "suite $(tail -1 $L/modules.log)"
for A in graphite kasandra; do
  rm -rf $S/work/scene082_$A
  (cd $T && GRAPHITE_APPEARANCE=$([ $A = kasandra ] && echo kasandra) QT_QPA_PLATFORM=offscreen timeout 2400 unshare --pid --fork --mount-proc --kill-child $PY -B tools/campaign.py run --set scenes --fixtures $S/work/campaign_fixtures --out $S/work/scene082_$A > $L/scene_$A.log 2>&1)
  echo "scene $A exit $? $(grep -E -i 'pass|fail|blocked' $S/work/scene082_$A/SUMMARY.md 2>/dev/null | head -8 | tr '\n' ' ')"
done
for size in "1920 1200" "1366 768"; do
  set -- $size; tag=${1}x${2}; mkdir -p $L/set_$tag
  for p in look_probe head_probe glow_probe centre_probe audit_probe mouse_probe mouse2_probe pages_probe more_probe icons_probe crash_probe boxes_probe map_probe find_probe zoom_probe amber_probe green_probe cascade_probe ux044_probe first_probe eq_probe pane_probe line_probe hand_probe start_probe door_probe kasandra_probe; do
    A=; [ $p = kasandra_probe ] && A=kasandra
    GRAPHITE_APPEARANCE=$A REHEARSAL_MODEL=x REHEARSAL_SCRIPT=$S/tools/field/$p.py PYTHONUNBUFFERED=1 timeout 300 unshare --pid --fork --mount-proc --kill-child $PY -u -B $S/tools/field/nomodel.py $T $S/work/shots/l082 $1 $2 > $L/set_$tag/$p.log 2>&1
    echo "$p $tag exit $? tracebacks $(grep -c Traceback $L/set_$tag/$p.log) done $(grep -c '^DONE' $L/set_$tag/$p.log) wrong $(grep -c 'WRONG\|FAIL\|terminate called' $L/set_$tag/$p.log)"
  done
  for p in window stacy regress; do
    timeout 300 unshare --pid --fork --mount-proc --kill-child $PY -u -B $S/tools/field/$p.py $T $S/work/shots/l082 $1 $2 > $L/set_$tag/$p.log 2>&1
    echo "$p $tag exit $? tracebacks $(grep -c Traceback $L/set_$tag/$p.log)"
  done
done
for A in graphite kasandra; do
  GRAPHITE_APPEARANCE=$([ $A = kasandra ] && echo kasandra) CRAWL_MODE=icons REHEARSAL_MODEL=x REHEARSAL_SCRIPT=$S/tools/field/crawl_probe.py PYTHONUNBUFFERED=1 timeout 1700 unshare --pid --fork --mount-proc --kill-child $PY -X faulthandler -u -B $S/tools/field/nomodel.py $S/work/t_crawl $S/work/shots/crawl082 1366 768 > $L/crawl_$A.log 2>&1
  echo "crawl $A exit $? $(tail -3 $L/crawl_$A.log | tr '\n' ' ')"
  GRAPHITE_APPEARANCE=$([ $A = kasandra ] && echo kasandra) REHEARSAL_MODEL=x REHEARSAL_SCRIPT=$S/tools/field/name_sweep.py PYTHONUNBUFFERED=1 timeout 900 unshare --pid --fork --mount-proc --kill-child $PY -u -B $S/tools/field/nomodel.py $S/work/t_crawl $S/work/shots/sweep082 1920 1200 > $L/sweep_$A.log 2>&1
  echo "sweep $A exit $? $(grep -E 'NAME SWEEP|DONE' $L/sweep_$A.log | tr '\n' ' ')"
done
H=$(mktemp -d -p $S/work); cd $S/work/t_ui && HOME=$H QT_QPA_PLATFORM=offscreen timeout 3000 unshare --pid --fork --mount-proc --kill-child $PY -B tools/check_release.py --ui --output $S/work/reports2/ui_082.json > $L/gate.log 2>&1; echo "gate exit $?"
$PY $S/tools/tests/compare_ui.py $S/work/reports2/ui_070d.json $S/work/reports2/ui_082.json | tail -25
echo "CHECKS DONE"
