#!/bin/bash
# make_brief_11.sh KEY -> the builder's brief for a 1.1 slice: BRIEF_HEADER_1.1.md with <KEY> filled, then the slice's
# text from PLAN_1.1.md section 5 (from its "**KEY ·" paragraph to the next slice or heading).
S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad
D=/home/user/Struthio/wip/2026-11-27_distribution; K=$1; mkdir -p $S/work/briefs $S/work/b110/$K
OUT=$S/work/briefs/110_$K.md
sed "s/<KEY>/$K/g" $D/BRIEF_HEADER_1.1.md > $OUT
python3 -I - "$D/PLAN_1.1.md" "$K" >> $OUT <<'PY'
import sys,re
text=open(sys.argv[1],encoding='utf-8').read(); key=sys.argv[2]
m=re.search(r'^\*\*'+re.escape(key)+r' ·.*?(?=^\*\*[A-Z]+[0-9]* ·|^###|^## |\Z)', text, re.S|re.M)
if not m: sys.exit('no slice '+key)
print(m.group(0).strip())
PY
echo $OUT
