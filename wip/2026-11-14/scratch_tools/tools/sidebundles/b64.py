import sys, json, base64, re
j = json.load(open(sys.argv[1], encoding="utf-8"))
for k in ("dock_state", "geometry"):
    raw = base64.b64decode(j["layout"][k])
    txt = raw.decode("utf-16-be", "ignore")
    print(k, len(raw), "utf16 words:", re.findall(r"[A-Za-z]{4,}", txt))
print("top-level keys:", sorted(j.keys()))
