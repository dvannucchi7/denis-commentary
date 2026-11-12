"""Merge one finished article into data/commentary/<book>.json and switch the book on in the app.

usage: python3 tools/add_article.py work/matthew-05.json

The work file holds one article:
{
  "book": "matthew", "chapter": 2,
  "work": "Enarratio in Evangelium secundum Matthæum",
  "source": "Dionysii Cartusiani Opera Omnia, t. XI (Montreuil)",
  "num": "IV", "title": "…Latin title…", "title_en": "…English title…", "pages": "pp. 21–25",
  "note": "(optional)",
  "paras": [ {"v": [1, 6], "t": "Latin…", "en": "English with [[ref|DR|Vulgate]] markers…"}, … ]
}
An article already in the file with the same number and chapter is replaced (so a run can be redone).
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
def rom(s):
    n = 0
    for i, c in enumerate(s):
        v = R[c]; n += -v if i + 1 < len(s) and R[s[i + 1]] > v else v
    return n

art = json.load(open(sys.argv[1]))
book, ch = art.pop("book"), str(art.pop("chapter"))
work, source = art.pop("work"), art.pop("source")
for k in ("num", "title", "title_en", "pages", "paras"):
    assert k in art, f"missing {k}"
for p in art["paras"]:
    assert set(p) >= {"v", "t", "en"}, p.keys()

path = os.path.join(ROOT, "data", "commentary", book + ".json")
data = json.load(open(path)) if os.path.exists(path) else {"work": work, "source": source, "chapters": {}}
arts = [a for a in data["chapters"].get(ch, []) if a["num"] != art["num"]] + [art]
arts.sort(key=lambda a: rom(a["num"]))
data["chapters"][ch] = arts
data["chapters"] = dict(sorted(data["chapters"].items(), key=lambda kv: int(kv[0])))
json.dump(data, open(path, "w"), ensure_ascii=False, indent=1)

# make sure the app knows this book has commentary
idx = os.path.join(ROOT, "index.html")
html = open(idx).read()
m = re.search(r"const COMMENTARY_BOOKS = \[(.*?)\];", html)
books = re.findall(r'"([^"]+)"', m.group(1))
if book not in books:
    books.append(book)
    html = html.replace(m.group(0), "const COMMENTARY_BOOKS = [" + ", ".join(f'"{b}"' for b in books) + "];")
    open(idx, "w").write(html)
print(f"added {book} {ch}, Art. {art['num']} ({len(art['paras'])} paragraphs)")
