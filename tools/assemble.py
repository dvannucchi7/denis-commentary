"""Join column OCR files (in reading order) into clean running Latin.

usage: python3 assemble.py OUT.txt ocr/p14.txt ocr/p15.txt ...
"""
import re, sys

out, files = sys.argv[1], sys.argv[2:]
lines = []
for f in files:
    raw = open(f).read()
    left, right = raw.split("=====RIGHT=====")
    for col in (left.replace("=====LEFT=====", ""), right):
        for ln in col.splitlines():
            t = ln.strip()
            if not t: lines.append(""); continue
            if re.search(r"ENAR+ATIO|EXODI\.|— ART\.", t): continue          # running heads
            if re.fullmatch(r"[\W\d]{0,6}", t): continue                         # stray marks / page numbers
            t = re.sub(r"^[ABCD] (?=[a-zæœ])", "", t)                           # gutter letter at line start
            t = re.sub(r" [ABCD]$", "", t)                                        # gutter letter at line end
            lines.append(t)

text = ""
for t in lines:
    if not t:
        text += "\n"; continue
    if text.endswith("-"):
        text = text[:-1] + t                                                     # word broken across lines
    elif text and not text.endswith("\n"):
        text += " " + t
    else:
        text += t

FIX = {  # frequent OCR slips in this edition
    "preecept": "præcept", "precept": "præcept", "preecip": "præcip", "precip": "præcip",
    "prece": "præce", "pree": "præ", "seript": "script", "quie ": "quæ ", " eum populo": " cum populo",
    "Hebraei": "Hebræi", "Hebraeorum": "Hebræorum", "JEgypt": "Ægypt", "Egypti": "Ægypti",
    "Rabb!": "Rabbi", "jstud": "istud", "sie ": "sic ", "peceat": "peccat", "eundo": "cundo",
    " ae ": " ac ", "pena": "pœna", "poena": "pœna",
}
for a, b in FIX.items():
    text = text.replace(a, b)
text = re.sub(r"[ \t]+", " ", text)
text = re.sub(r"\n{2,}", "\n\n", text)
open(out, "w").write(text.strip() + "\n")
print(len(text.split()), "words")
