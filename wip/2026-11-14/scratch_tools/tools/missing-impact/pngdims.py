import sys, struct
for p in sys.argv[1:]:
    with open(p, 'rb') as f:
        head = f.read(26)
    if head[:8] == b'\x89PNG\r\n\x1a\n':
        w, h, depth, ctype = struct.unpack('>IIBB', head[16:26])
        print(w, 'x', h, 'depth', depth, 'colortype', ctype, p.rsplit('/', 1)[-1])
    else: print('not png', p)
