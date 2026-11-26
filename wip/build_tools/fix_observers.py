# Join an OBSERVER_OPERATIONS list that a union merge closed early: "...'})\n # comment\n 'x'})" -> one list.
import re,sys
p=sys.argv[1]; s=open(p).read()
new=re.sub(r"'\}\)\n( # [^\n]*\n '[^\n]*\}\))", r"',\n\1", s)
while new!=s:
    s=new; new=re.sub(r"'\}\)\n( # [^\n]*\n '[^\n]*\}\))", r"',\n\1", s)
open(p,'w').write(s)
