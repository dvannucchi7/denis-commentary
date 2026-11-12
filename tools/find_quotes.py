"""List the places where Denis quotes the chapter he is treating, with the wording ready to use.

usage: python3 tools/find_quotes.py ARTICLE.txt BOOK CHAPTER [--min 3]
  e.g. python3 tools/find_quotes.py sources/t11/articles/matthew-10.txt matthew 5

It compares Denis's Latin with the Vulgate text of the chapter and prints, in the order they occur in
the article, every run of at least --min consecutive words (default 3) that matches a verse, together
with the verse's full Douay-Rheims and Vulgate text. Spelling differences (æ/e, j/i, v/u, quum/cum)
are ignored. It is a helper, not a judge: check each hit, choose the exact Douay-Rheims words that
correspond to what Denis quotes, and look up quotations from other books yourself (tools/verses.py).
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
mn = int(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 3
if "--min" in sys.argv: args.remove(str(mn))
text, book, ch = open(args[0]).read(), args[1], int(args[2])
drc = json.load(open(os.path.join(ROOT, "data/bible/drc", book + ".json")))[ch - 1]
vul = json.load(open(os.path.join(ROOT, "sources/vulgate", book + ".json")))[ch - 1]

def norm(w):
    w = w.lower().replace("æ", "e").replace("œ", "e").replace("ae", "e").replace("oe", "e")
    w = w.replace("j", "i").replace("v", "u")
    return "cum" if w == "quum" else w
tok = lambda s: [(m.start(), norm(m.group())) for m in re.finditer(r"[A-Za-zÆæŒœ]+", s)]
art = tok(text)
aw = [w for _, w in art]

hits = []
for vi, verse in enumerate(vul, 1):
    vw = [w for _, w in tok(verse)]
    need = min(mn, len(vw))
    seen = set()
    for i in range(len(vw)):
        for j in range(len(aw)):
            if aw[j] != vw[i] or (j, i) in seen: continue
            k = 0
            while i + k < len(vw) and j + k < len(aw) and aw[j + k] == vw[i + k]:
                seen.add((j + k, i + k)); k += 1
            if k >= need and not (i > 0 and j > 0 and aw[j - 1] == vw[i - 1]):
                vt = tok(verse)
                frag = verse[vt[i][0]: vt[i + k - 1][0] + len(re.findall(r"[A-Za-zÆæŒœ]+", verse)[i + k - 1])]
                hits.append((art[j][0], vi, frag))
hits.sort()
last = None
for pos, vi, frag in hits:
    ctx = text[max(0, pos - 40): pos].replace("\n", " ")
    print(f"{ch}:{vi}  Vulgate: {frag}")
    print(f"      …{ctx}⟨here⟩")
    if vi != last:
        print(f"      DR {ch}:{vi}: {drc[vi - 1]}")
    last = vi
print(f"\n{len(hits)} probable quotations of {book} {ch}.")
