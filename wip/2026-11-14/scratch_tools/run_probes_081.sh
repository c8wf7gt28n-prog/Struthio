#!/bin/bash
# the probe set on the working tree at one size: run_probes_049.sh W H
S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad
cd $S/work; tag=${1}x${2}; L=$S/work/logs081/set_$tag; O=$S/work/shots/l081; rm -rf $L; mkdir -p $L $O
for p in look_probe head_probe glow_probe centre_probe audit_probe mouse_probe mouse2_probe pages_probe more_probe icons_probe crash_probe boxes_probe map_probe find_probe zoom_probe amber_probe green_probe cascade_probe ux044_probe first_probe eq_probe pane_probe line_probe hand_probe start_probe door_probe kasandra_probe; do
  A=; [ $p = kasandra_probe ] && A=kasandra; GRAPHITE_APPEARANCE=$A REHEARSAL_MODEL=x REHEARSAL_SCRIPT=$S/tools/field/$p.py PYTHONUNBUFFERED=1 timeout 300 ./venv/bin/python -u -B $S/tools/field/nomodel.py /home/user/Struthio $O $1 $2 > $L/$p.log 2>&1
  echo "$p $tag exit $? tracebacks $(grep -c Traceback $L/$p.log) done $(grep -c '^DONE' $L/$p.log) wrong $(grep -c 'WRONG\|FAIL\|terminate called' $L/$p.log)"
done
for p in window stacy regress; do
  timeout 300 ./venv/bin/python -u -B $S/tools/field/$p.py /home/user/Struthio $O $1 $2 > $L/$p.log 2>&1
  echo "$p $tag exit $? tracebacks $(grep -c Traceback $L/$p.log)"
done
echo ALL DONE $tag
