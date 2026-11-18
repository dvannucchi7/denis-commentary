"""Keep only the margin notes that belong to one part of an article (for splitting an article among workers).

usage: python3 tools/part_margins.py MARGINS.txt PART.txt > PART-margins.txt

MARGINS.txt is the output of `python3 tools/margins.py VOL ID CHAPTER` for the whole article; PART.txt is
the part's Latin (or the whole article's, for a single worker: this also drops the notes on the first and
last pages that belong to the neighbouring articles). A note is kept when the Latin line it stands beside
matches a stretch of the part at least 80% letter for letter (the margin reader and the page OCR read the
same line with small differences, so an exact match misses notes). A note on a line shared by two parts
goes to both; the worker whose text holds the clause takes it (see tools/agent_brief.md).
"""
import re, sys, unicodedata, difflib

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
    keep = False
    if len(b) >= 12:
        for i in range(0, len(b) - 7):      # each 8-letter piece of the line that occurs in the part
            for hit in re.finditer(re.escape(b[i:i + 8]), part):
                start = max(0, hit.start() - i)
                if difflib.SequenceMatcher(None, b, part[start:start + len(b)]).ratio() >= 0.8:
                    keep = True; break
            if keep: break
    if keep:
        if not page_shown:
            out.append(page); page_shown = True
        out.append(ln)
print("\n".join(out))
