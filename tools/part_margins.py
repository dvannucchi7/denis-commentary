"""Keep only the margin notes that belong to one part of an article (for splitting an article among workers).

usage: python3 tools/part_margins.py MARGINS.txt PART.txt > PART-margins.txt

MARGINS.txt is the output of `python3 tools/margins.py VOL ID CHAPTER` for the whole article; PART.txt is
the part's Latin. A note is kept when any 15 letters in a row of the Latin line it stands beside occur in
the part (the margin reader and the page OCR read the same line, with small differences), so each worker
sees only its own notes, and notes on a line shared by two parts go to both (the worker on the earlier
part takes a note at the end of its text; see tools/agent_brief.md).
"""
import re, sys, unicodedata

def norm(s):
    s = unicodedata.normalize("NFKD", s.lower()).replace("æ", "ae").replace("œ", "oe")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("j", "i").replace("v", "u")
    s = re.sub(r"-\s+", "", s)               # words broken across lines
    return " ".join(re.findall(r"[a-z]+", s))

lines = open(sys.argv[1]).read().split("\n")
part = norm(open(sys.argv[2]).read()).replace(" ", "")
out, page, page_shown = [], None, False
for ln in lines:
    if ln.startswith("-- PDF"):
        page, page_shown = ln, False
        continue
    m = re.search(r"beside:\s*(.*)$", ln) or re.search(r"begins:\s*(.*)$", ln)
    if not m:
        if ln and not ln.startswith(" "):
            out.append(ln)                  # title line
        continue
    b = norm(m.group(1)).replace(" ", "")
    n = min(15, len(b))
    keep = n >= 8 and any(b[i:i + n] in part for i in range(len(b) - n + 1))
    if keep:
        if not page_shown:
            out.append(page); page_shown = True
        out.append(ln)
print("\n".join(out))
