"""List the places where Denis quotes the chapter he is treating, with the wording ready to use, and then the quotations from anywhere else in the Bible.

usage: python3 tools/find_quotes.py ARTICLE.txt BOOK CHAPTER [--min 3]
  e.g. python3 tools/find_quotes.py sources/t11/articles/matthew-10.txt matthew 5

It compares Denis's Latin with the Vulgate text of the chapter and prints, in the order they occur in
the article, every run of at least --min consecutive words (default 3) that matches a verse, together
with the verse's full Douay-Rheims and Vulgate text. Spelling differences (æ/e, j/i, v/u, quum/cum)
are ignored. It is a helper, not a judge: check each hit, choose the exact Douay-Rheims words that
correspond to what Denis quotes.

A second list covers the rest of the Bible: every run of at least 4 words (6 for very common
phrases) that matches a verse outside this chapter, with its reference already in the Douay form
used by the markers (Ps 44:8, 1 Kings 2:6, Matt 5:3). Where the same words occur in several places
(Gospel parallels, repeated psalm verses) all of them are listed: pick the one Denis means (in a
Gospel commentary, the parallel he names, or else the one whose wording fits best). The marginal
references of the printed edition are lost in the OCR, so this is how to identify a quotation's
source; anything it misses (short quotations, free citations) still needs tools/verses.py.
Each hit ends with a shorthand marker ready to complete (see tools/expand_quotes.py).
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

# ---- the rest of the Bible -------------------------------------------------------------------
sys.path.insert(0, os.path.join(ROOT, "tools"))
from check_quotes import ABBR
REV = {v: k for k, v in ABBR.items()}
flat, where = [], []                      # every Vulgate word, and (book, c, v) for each
for b in REV:
    for ci, chap in enumerate(json.load(open(os.path.join(ROOT, "sources/vulgate", b + ".json"))), 1):
        for vi, vs in enumerate(chap, 1):
            for _, w in tok(vs):
                flat.append(w); where.append((b, ci, vi))
index, index3 = {}, {}
for i in range(len(flat) - 2):
    index3.setdefault(tuple(flat[i:i + 3]), []).append(i)
    if i < len(flat) - 3: index.setdefault(tuple(flat[i:i + 4]), []).append(i)
STOP = set("et in ad de non est sunt qui que quod ut cum enim autem sed ego tu ipse eius eum ei me te se nos uos".split())

def drv(b, c, v):
    return json.load(open(os.path.join(ROOT, "data/bible/drc", b + ".json")))[c - 1][v - 1]

out, j = [], 0
while j < len(aw) - 2:
    c4 = index.get(tuple(aw[j:j + 4]), [])
    c3 = index3.get(tuple(aw[j:j + 3]), [])
    # a 3-word match counts only if those words are rare in the Bible and not mostly little words
    rare3 = len(c3) <= 3 and sum(w not in STOP and len(w) > 3 for w in aw[j:j + 3]) >= 2
    cands, need = (c4, 4) if c4 else ((c3, 3) if rare3 else ([], 0))
    best, refs = 0, []
    for i in cands[:400]:
        if where[i][0] == book and where[i][1] == ch: continue
        k = need
        while j + k < len(aw) and i + k < len(flat) and aw[j + k] == flat[i + k]: k += 1
        if len(cands) > 40 and k < 6: continue
        r = (where[i], where[i + k - 1])
        if k > best: best, refs = k, [r]
        elif k == best and r not in refs: refs.append(r)
    if best:
        out.append((j, best, refs)); j += best
    else:
        j += 1
print(f"\nElsewhere in the Bible ({len(out)}):")
for j, k, refs in out:
    a0, a1 = art[j][0], art[j + k - 1][0] + len(art[j + k - 1][1])
    words_ = text[a0:a1].replace("\n", " ")
    first = " ".join(words_.split()[:2]); last = words_.split()[-1]
    print(f"  Denis: {words_}")
    for (b, c, v), (_, c2, v2) in refs[:4]:
        ref = f"{REV[b]} {c}:{v}"
        span = f" (runs on to {c2}:{v2}: one marker per verse)" if (c2, v2) != (c, v) else ""
        print(f"    {ref}{span}  DR: {drv(b, c, v)}")
        if span: print(f"    {REV[b]} {c2}:{v2}  DR: {drv(b, c2, v2)}")
        print(f"      [[{ref}|… |{first} … {last}]]")
    if len(refs) > 4: print(f"    (+{len(refs) - 4} more places)")
