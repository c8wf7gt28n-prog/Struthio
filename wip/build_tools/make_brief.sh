#!/bin/bash
# make_brief.sh KEY -> the builder's brief for a 1.0 slice: BRIEF_HEADER.md with <KEY> filled, then the slice's text
# from PLAN_1.0.md section 5 (from its "**KEY ·" paragraph to the next slice or heading).
S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad
D=/home/user/Struthio/wip/2026-11-26_road_to_1.0; K=$1; mkdir -p $S/work/briefs $S/work/b100/$K
OUT=$S/work/briefs/100_$K.md
sed "s/<KEY>/$K/g" $D/BRIEF_HEADER.md > $OUT
python3 -I - "$D/PLAN_1.0.md" "$K" >> $OUT <<'PY'
import sys,re
text=open(sys.argv[1],encoding='utf-8').read(); key=sys.argv[2]
m=re.search(r'^\*\*'+re.escape(key)+r' ·.*?(?=^\*\*[A-Z][0-9a-z]* ·|^###|^## |\Z)', text, re.S|re.M)
if not m: sys.exit('no slice '+key)
print(m.group(0).strip())
PY
echo $OUT
