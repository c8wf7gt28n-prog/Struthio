import sys, sqlite3, json, re
con = sqlite3.connect("file:" + sys.argv[1] + "?mode=ro&immutable=1", uri=True)
keys = set()
def walk(o, pre=""):
    if isinstance(o, dict):
        for k, v in o.items(): keys.add(pre + k); walk(v, pre + k + ".")
    elif isinstance(o, list):
        for v in o[:3]: walk(v, pre + "[].")
for t, col in (("jobs", "payload"), ("evidence", "payload"), ("settings", "value")):
    keys.clear()
    for (pl,) in con.execute(f"select {col} from {t}"):
        try: walk(json.loads(pl))
        except Exception: pass
    interesting = sorted(k for k in keys if re.search(r"host|user|name|path|home|cwd|env|machine|cpu|gpu|kernel|platform|python|exec|argv|command", k, re.I))
    print(t, "keys total", len(keys), "interesting:", interesting[:60])
