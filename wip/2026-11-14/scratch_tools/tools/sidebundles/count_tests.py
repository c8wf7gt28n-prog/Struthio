import sys, ast, os
tot = 0
for p in sys.argv[1:]:
    t = ast.parse(open(p, encoding="utf-8").read())
    n = 0
    for node in ast.walk(t):
        if isinstance(node, ast.ClassDef):
            n += sum(1 for b in node.body if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)) and b.name.startswith("test"))
    print(os.path.basename(p), n); tot += n
print("total", tot)
