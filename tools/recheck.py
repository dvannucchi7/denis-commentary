"""Re-check a published article's references against the printed margins (Dave's rule: a quotation from
outside the chapter treated is tagged only where the margin gives a reference for it).

usage: python3 tools/recheck.py t11 matthew-01            (report)
       python3 tools/recheck.py --export t11 matthew-01   (work file(s) to edit, then tools/add_article.py)

For each paragraph it lists the tagged references from outside the chapter treated and the margin
references beside that paragraph, and marks each one:

  ok          tagged, and the margin gives the same verse
  differs     tagged, the margin names the same book but another verse: check which is right
  no-margin   tagged, but no margin reference for that book beside it: untag it (keep the words),
              unless an [unread] margin note beside it turns out to be its reference
  untagged    the margin gives a reference that no tag here uses: find the quotation and tag it,
              or leave it if Denis only alludes (allusion? usually means that)
  unread      a margin note that could not be read: look at what Denis quotes there

Margin references are placed in a paragraph by matching the Latin printed beside them; ones that match
no paragraph belong to the neighbouring articles on the first and last pages and are left out.
Lemmata (quotations of the chapter treated) are not part of this check.
"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import margins
from check_quotes import ABBR

Q = re.compile(r"\[\[([^|\]]+)\|([^|\]]*)\|([^\]]*)\]\]")
ROMAN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
         (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]

def roman(n):
    s = ""
    for v, r in ROMAN:
        while n >= v: s += r; n -= v
    return s

def words(s):
    s = s.lower().replace("æ", "ae").replace("œ", "oe").replace("j", "i").replace("v", "u")
    return set(w for w in re.findall(r"[a-z]{4,}", s))

def find_articles(book, num):
    data = json.load(open(os.path.join(ROOT, "data", "commentary", book + ".json")))
    return [(int(ch), a) for ch, arts in data["chapters"].items() for a in arts if a["num"] == num]

def outside(ref, book, ch):
    m = re.match(r"^(.*?)\s*(\d+):(\d+)$", ref)
    if not m: return None
    b = ABBR.get(m.group(1)) if m.group(1) else book
    if b == book and int(m.group(2)) == ch and not m.group(1): return None      # a lemma
    return b, int(m.group(2)), int(m.group(3))

def main(vol, item_id):
    q = json.load(open(os.path.join(ROOT, "sources", vol, "queue.json")))
    item = next(i for i in q["items"] if i["id"] == item_id)
    arts = find_articles(item["book"], roman(item["art"]))
    if not arts: sys.exit(f"{item_id}: no published article {roman(item['art'])} in {item['book']}")
    rows = margins.article(vol, item_id, str(arts[0][0]), quiet=True)
    if margins.article.missing:
        print(f"margins not read yet for PDF {margins.article.missing}: references there cannot be checked")
    paras = [(ch, a["num"], i, p) for ch, a in arts for i, p in enumerate(a["paras"])]
    pw = [words(p["t"]) for _, _, _, p in paras]
    # place each margin reference in the paragraph whose Latin best matches the text beside it
    placed = {k: [] for k in range(len(paras))}
    for r in rows:
        if r["kind"] == "verse": continue
        w = words(r.get("ctx") or r["beside"])
        scores = [len(w & x) for x in pw]
        best = max(range(len(paras)), key=lambda k: scores[k])
        if scores[best] >= 3: placed[best].append(r)
    total = {"ok": 0, "differs": 0, "no-margin": 0, "untagged": 0, "unread": 0}
    for k, (ch, num, i, p) in enumerate(paras):
        tags = [(m.group(1), m.group(2)) for m in Q.finditer(p.get("en", ""))]
        tags = [(ref, dr, outside(ref, item["book"], ch)) for ref, dr in tags]
        tags = [t for t in tags if t[2]]
        near = placed.get(k - 1, []) + placed[k] + placed.get(k + 1, [])
        lines, used = [], set()
        for ref, dr, (b, c, v) in tags:
            same = [r for r in near if r.get("book") == b]
            exact = [r for r in same if r["ch"] == c and r["v"] == v]
            same.sort(key=lambda r: (r["ch"] != c, abs((r["v"] or 0) - v)))
            if exact:
                st = "ok"; used.add(id(exact[0])); info = f"margin {exact[0]['printed']!r}"
            elif same:
                st = "differs"; used.add(id(same[0])); info = f"margin {same[0]['printed']!r} read as {same[0]['ref']} ({same[0]['kind']})"
            else:
                st = "no-margin"; info = ""
            total[st] += 1
            lines.append(f"   {st:<10} [{ref}] {dr[:60]!r} {info}")
        tagged = {(t[2][0], t[2][1], t[2][2]) for t in tags}
        for r in placed[k]:
            if id(r) in used or (r.get("book"), r.get("ch"), r.get("v")) in tagged: continue
            if r["kind"] == "unread":
                total["unread"] += 1
                lines.append(f"   {'unread':<10} margin {r['printed']!r} beside: {r['beside'][:60]}")
            else:
                total["untagged"] += 1
                lines.append(f"   {'untagged':<10} margin {r['ref']} ({r['kind']}, printed {r['printed']!r}) beside: {r['beside'][:60]}")
        if lines:
            print(f"-- ch. {ch}, Art. {num}, para {i + 1} (vv. {p['v'][0]}-{p['v'][1]})")
            print("\n".join(lines))
    print("summary:", ", ".join(f"{k} {v}" for k, v in total.items()))

def export(vol, item_id):
    """Write the published article as work file(s) for editing and re-merging with tools/add_article.py."""
    q = json.load(open(os.path.join(ROOT, "sources", vol, "queue.json")))
    item = next(i for i in q["items"] if i["id"] == item_id)
    data = json.load(open(os.path.join(ROOT, "data", "commentary", item["book"] + ".json")))
    os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
    for ch, a in find_articles(item["book"], roman(item["art"])):
        out = dict(book=item["book"], chapter=ch, work=data["work"], source=data["source"], **a)
        path = os.path.join(ROOT, "work", f"{item_id}-ch{ch}.json")
        json.dump(out, open(path, "w"), ensure_ascii=False, indent=1)
        print("wrote", os.path.relpath(path, ROOT))

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == "--export": export(a[1], a[2])
    elif len(a) == 2: main(a[0], a[1])
    else: sys.exit(__doc__)
