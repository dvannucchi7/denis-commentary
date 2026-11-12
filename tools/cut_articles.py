"""Cut each queued article out of the OCR pages into sources/<vol>/articles/<id>.txt.

usage: python3 tools/cut_articles.py t11

For every item still to do, joins the pages in its range (tools/assemble.py) and keeps the text from
the item's own ARTICULUS heading up to the next ARTICULUS heading. If the heading cannot be found
(OCR damage), no file is written and a translation run cuts the article by hand from the pages.
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
vol = sys.argv[1]
base = os.path.join(ROOT, "sources", vol)
q = json.load(open(os.path.join(base, "queue.json")))
os.makedirs(os.path.join(base, "articles"), exist_ok=True)
R = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
def rom(s):
    s = s.upper().replace("1", "I").replace("L", "L")
    if not re.fullmatch(r"[IVXLC]+", s): return None
    n = 0
    for i, c in enumerate(s):
        v = R[c]; n += -v if i + 1 < len(s) and R[s[i + 1]] > v else v
    return n
HEAD = re.compile(r"^\s*[A-Z]{0,2}RT[I1l]C[UV]?L?[UV]?S?\s+([IVXLCl1]+|PRIMUS)\b", re.M)
_rom = rom
def rom(s):
    return 1 if s.upper() == "PRIMUS" else _rom(s)

made = skipped = 0
for it in q["items"]:
    if it["status"] == "done": continue
    a, b = it["pages"]
    pages = [os.path.join(base, "pages", f"p{p}.txt") for p in range(a, b + 1)
             if os.path.exists(os.path.join(base, "pages", f"p{p}.txt"))]
    tmp = "/tmp/_cut.txt"
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "assemble.py"), tmp] + pages,
                   check=True, capture_output=True)
    text = open(tmp).read()
    heads = [(m.start(), rom(m.group(1))) for m in HEAD.finditer(text)]
    mine = [i for i, (pos, n) in enumerate(heads) if n == it["art"]]
    if not mine:
        skipped += 1; continue
    i = mine[0]
    start = heads[i][0]
    end = next((pos for pos, n in heads[i + 1:] if n != it["art"]), len(text))
    out = os.path.join(base, "articles", it["id"] + ".txt")
    open(out, "w").write(text[start:end].strip() + "\n")
    made += 1
print(f"{vol}: {made} article files written, {skipped} left for runs to cut by hand")
