import sys, os, re, zlib, struct
for p in sys.argv[1:]:
    data = open(p, "rb").read()
    n = os.path.basename(p)
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        i = 8; chunks = []
        while i < len(data):
            ln, typ = struct.unpack(">I4s", data[i:i+8]); body = data[i+8:i+8+ln]
            if typ in (b"tEXt", b"iTXt", b"zTXt", b"eXIf", b"tIME", b"pHYs"):
                chunks.append((typ.decode(), body[:120]))
            elif typ not in (b"IDAT",):
                chunks.append((typ.decode(), ln))
            i += 12 + ln
        print("PNG", n, chunks)
    elif data[:5] == b"%PDF-":
        print("PDF", n, data[:8], "objs", len(re.findall(rb"\d+ \d+ obj", data)))
        for key in (b"/Author", b"/Creator", b"/Producer", b"/Title", b"/Subject", b"/Keywords", b"/CreationDate", b"/ModDate"):
            for m in re.finditer(re.escape(key) + rb"\s*(\([^)]{0,120}\)|<[0-9A-Fa-f]{0,240}>)", data):
                print("    ", key.decode(), m.group(1)[:140])
        # decompress streams, extract text show operators
        txt = []
        for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
            raw = m.group(1)
            try: dec = zlib.decompress(raw)
            except Exception: continue
            for t in re.findall(rb"\(((?:[^()\\]|\\.)*)\)\s*Tj", dec): txt.append(t.decode("latin-1"))
            for arr in re.findall(rb"\[((?:[^\]\\]|\\.)*)\]\s*TJ", dec):
                txt.append("".join(x.decode("latin-1") for x in re.findall(rb"\(((?:[^()\\]|\\.)*)\)", arr)))
            if b"xmpmeta" in dec: print("     XMP in stream:", dec[:400])
        if b"xmpmeta" in data: 
            k = data.find(b"<x:xmpmeta"); print("     XMP:", data[k:k+600])
        print("     text items:", len(txt)); 
        for t in txt[:60]: print("       |", t[:140])
        print("     fonts:", set(re.findall(rb"/BaseFont\s*/([A-Za-z0-9+_-]+)", data)))
