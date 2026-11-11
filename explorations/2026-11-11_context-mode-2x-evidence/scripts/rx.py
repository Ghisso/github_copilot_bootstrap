"""Print regex matches with context from a file: rx.py <file> <regex> [ctx] [max]."""
import re, sys
text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 120
limit = int(sys.argv[4]) if len(sys.argv) > 4 else 20
for i, m in enumerate(re.finditer(sys.argv[2], text)):
    if i >= limit:
        break
    s, e = max(0, m.start() - ctx), min(len(text), m.end() + ctx)
    print(f"@{m.start()}: ...{text[s:e]}...".replace("\n", "\\n"))
