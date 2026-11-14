import sys, sqlite3, json, collections
con = sqlite3.connect("file:" + sys.argv[1] + "?mode=ro&immutable=1", uri=True)
plat = collections.Counter(); py = collections.Counter(); cwd = collections.Counter(); argv0 = collections.Counter(); tv = collections.Counter(); iso = collections.Counter(); hw = collections.Counter()
for (pl,) in con.execute("select payload from evidence"):
    d = json.loads(pl)
    e = d.get("environment", {})
    plat[str(e.get("platform"))] += 1; py[str(e.get("python"))] += 1; hw[str(e.get("physical_hardware"))] += 1
    iso[json.dumps(e.get("isolation"), sort_keys=True)] += 1
    cwd[str(d.get("cwd"))] += 1
    a = d.get("argv"); argv0[" ".join(map(str, a[:4])) if isinstance(a, list) else str(a)] += 1
    tv[json.dumps(d.get("tool_versions"), sort_keys=True)] += 1
for name, c in (("platform", plat), ("python", py), ("physical_hardware", hw), ("isolation", iso), ("cwd", cwd), ("argv[:4]", argv0), ("tool_versions", tv)):
    print(name, dict(c))
