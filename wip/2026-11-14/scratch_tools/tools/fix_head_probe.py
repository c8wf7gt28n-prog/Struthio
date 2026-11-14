import io
p = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/field/head_probe.py'
t = io.open(p, encoding='utf8').read()
old = "save('Head_%s_%s.png' % (name, tag))\n        finally: m.close()"
print('found', t.count(old))
t = t.replace(old, "m.grab().save(str(OUT / ('Head_%s_%s.png' % (name, tag))))\n        finally: m.close()")
io.open(p, 'w', encoding='utf8').write(t)
