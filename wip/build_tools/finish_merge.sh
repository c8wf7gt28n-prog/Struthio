#!/bin/bash
# after conflicts are resolved: compile, rebuild the seed, smoke both looks
S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad; PY=$S/work/venv/bin/python
cd /home/user/Struthio || exit 9; export QT_QPA_PLATFORM=offscreen
for f in $(git diff --name-only HEAD -- '*.py'; git ls-files --others --exclude-standard -- '*.py'); do [ -f "$f" ] && { $PY -m py_compile "$f" || { echo "COMPILE FAIL $f"; BAD=1; }; }; done
$PY tools/package_graphite.py --manifest-only >/dev/null 2>&1 && $PY tools/record_registry.py >/dev/null 2>&1 && $PY tools/package_graphite.py --manifest-only >/dev/null 2>&1 && $PY tools/record_registry.py --check >/dev/null 2>&1; rc=$?; echo "seed rc=$rc"; [ $rc -ne 0 ] && BAD=1
for look in graphite kasandra day night; do h=$(mktemp -d); env HOME=$h GRAPHITE_APPEARANCE=$look timeout 120 $PY -B -c "
import sys;sys.path.insert(0,'.')
from workbench.qt_app import make_app, WorkbenchWindow
from workbench import locations
from workbench.session import Session
import tempfile,pathlib
run=pathlib.Path(tempfile.mkdtemp());app=make_app([]);root=locations.office(run/'workspace');s=Session(run/'profile/session.json',root)
w=WorkbenchWindow(root,s,restore=False);w.resize(1366,768);w.show();app.processEvents();print('$look window opened',w.width(),w.height())
" 2>&1 | tail -1 | tee /dev/stderr | grep -q 'window opened' || BAD=1; rm -rf $h; done

[ -n "$BAD" ] && { echo "MERGE CHECK FAILED"; exit 1; }
exit 0
