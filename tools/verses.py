"""Print the Douay-Rheims and Vulgate wording of verses, for building quotation markers.

usage: python3 tools/verses.py "Matt 5:3" "Ps 26:13" "Gen 2:24-25" ...
       python3 tools/verses.py --chapter matthew 5      (whole chapter, both versions)

References use the abbreviations in ABBR (tools/check_quotes.py), Vulgate numbering.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_quotes import ABBR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(kind, book):
    path = os.path.join(ROOT, "data/bible/drc" if kind == "drc" else "sources/vulgate", book + ".json")
    return json.load(open(path))

def show(book, c, v1, v2):
    d, l = load("drc", book), load("vul", book)
    for v in range(v1, v2 + 1):
        print(f"{book} {c}:{v}\n  DR: {d[c-1][v-1]}\n  V:  {l[c-1][v-1]}")

if sys.argv[1:2] == ["--chapter"]:
    book, c = sys.argv[2], int(sys.argv[3])
    show(book, c, 1, len(load("drc", book)[c - 1]))
else:
    for ref in sys.argv[1:]:
        m = re.match(r"^(.*?)\s*(\d+):(\d+)(?:-(\d+))?$", ref)
        if not m or m.group(1) not in ABBR:
            print("?? cannot read", ref); continue
        show(ABBR[m.group(1)], int(m.group(2)), int(m.group(3)), int(m.group(4) or m.group(3)))
