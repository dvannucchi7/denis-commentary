"""Expand shorthand quotation markers in a work file, filling in the exact wording from the sources.

usage: python3 tools/expand_quotes.py work/matthew-10.json      (add_article.py runs this itself)

So a run does not have to copy out the Douay-Rheims and Vulgate words of every quotation, a marker
in a work file may give each side as a few words from the start and end of the quoted part:

  [[Ps 44:8|hath anointed … fellows|Unxit … tuis]]
      -> [[Ps 44:8|hath anointed thee with the oil of gladness above thy fellows|Unxit te Deus oleo lætitiæ præ participibus tuis]]
  [[5:3|*|*]]                    the whole verse, both sides
  [[John 3:34|God doth not … measure|*]]

"…" or "..." separates the two anchors (each one or more whole words, case, accents, æ/ae, j/i and
v/u ignored). Each anchor must occur only once in the verse (the end anchor: once after the start);
otherwise the script asks for more words. Two or three words at each end are usually enough. The Latin side is looked for first in the paragraph's own Latin ("t") (the span closest in length to the Vulgate one), so it keeps
Denis's wording where he quotes a different form from the Clementine text; failing that, in the
Vulgate verse. "*" on the Latin side always gives the Vulgate verse. The span runs from the start anchor to the first end anchor after it. "*" means the
whole verse. A side with no "…" and no "*" is taken as written (it must still match the verse).
If an anchor is not found the script stops and prints the verse, so nothing is written half-expanded.
"""
import json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from check_quotes import ABBR  # noqa: E402

Q = re.compile(r"\[\[([^|\]]+)\|([^|\]]*)\|([^\]]*)\]\]")
ELL = re.compile(r"\s*(?:…|\.\.\.)\s*")
_cache = {}

def verse(folder, book, c, v):
    key = (folder, book)
    if key not in _cache:
        _cache[key] = json.load(open(os.path.join(ROOT, folder, book + ".json")))
    return _cache[key][c - 1][v - 1]

def norm_map(s):
    """Normalized letters-and-spaces string, and for each of its characters the index in s."""
    out, pos = [], []
    for i, ch in enumerate(s):
        base = unicodedata.normalize("NFD", ch.lower())[0]
        rep = {"æ": "ae", "œ": "oe", "j": "i", "v": "u", "’": "'"}.get(base, base)
        if not rep.isalpha():
            rep = " "
        for r in rep:
            if r == " " and (not out or out[-1] == " "):
                continue
            out.append(r); pos.append(i)
    return "".join(out), pos

def finds(hay, needle, start=0):
    """All (start, end) places of needle in hay at word boundaries, at or after start."""
    rx = re.compile(r"(?<![a-z])" + re.escape(needle) + r"(?![a-z])")
    return [(m.start(), m.end()) for m in rx.finditer(hay) if m.start() >= start]

def anchors(side):
    parts = ELL.split(side.strip())
    if len(parts) != 2 or not all(parts):
        return None
    return norm_map(parts[0])[0].strip(), norm_map(parts[1])[0].strip()

def cut(text, pos, i0, j0):
    i, j = pos[i0], pos[j0 - 1] + 1
    while j < len(text) and text[j].isalpha():
        j += 1
    if j < len(text) and text[j] in "?!":
        j += 1
    return text[i:j]

def expand_side(side, text):
    """Expand one side against a verse; anchors must be unambiguous there."""
    side = side.strip()
    if side == "*":
        return text.strip()
    an = anchors(side)
    if not an:
        return side
    hay, pos = norm_map(text)
    s1 = finds(hay, an[0])
    if not s1:
        raise LookupError(f"start '{an[0]}' not found")
    if len(s1) > 1:
        raise LookupError(f"start '{an[0]}' occurs {len(s1)} times in the verse: give more words")
    s2 = finds(hay, an[1], s1[0][1] if an[1] != an[0] else s1[0][0])
    if not s2:
        raise LookupError(f"end '{an[1]}' not found after the start")
    if len(s2) > 1:
        raise LookupError(f"end '{an[1]}' occurs {len(s2)} times after the start: give more words")
    return cut(text, pos, s1[0][0], s2[0][1])

def from_denis(side, latin, target_words):
    """The same quotation in Denis's own Latin: start anchor to end anchor, the span whose length is
    closest to the Vulgate span's (within 40%). None if there is no such span."""
    an = anchors(side)
    if not an or not latin:
        return None
    hay, pos = norm_map(latin)
    best = None
    for a0, a1 in finds(hay, an[0]):
        for b0, b1 in finds(hay, an[1], a1 if an[1] != an[0] else a0):
            n = len(hay[a0:b1].split())
            if target_words and abs(n - target_words) > max(2, 0.4 * target_words):
                continue
            score = abs(n - target_words) if target_words else n
            if best is None or score < best[0]:
                best = (score, a0, b1)
    return cut(latin, pos, best[1], best[2]) if best else None

def expand(en, book, latin=""):
    def one(m):
        ref, dr, vul = m.group(1).strip(), m.group(2), m.group(3)
        r = re.match(r"^(.*?)\s*(\d+):(\d+)$", ref)
        if not r:
            raise LookupError(f"bad ref '{ref}'")
        abbr, c, v = r.group(1), int(r.group(2)), int(r.group(3))
        target = ABBR.get(abbr) if abbr else book
        if not target:
            raise LookupError(f"unknown abbreviation '{abbr}' in {ref}")
        drt = verse("data/bible/drc", target, c, v)
        vt = verse("sources/vulgate", target, c, v)
        try:
            drx = expand_side(dr, drt)
            if anchors(vul):            # Latin side: Denis's own words, sized by the Vulgate span
                try:
                    vx = expand_side(vul, vt)
                except LookupError:
                    vx = None           # anchors in Denis's wording only (a variant reading)
                lat = from_denis(vul, latin, len(norm_map(vx)[0].split()) if vx else 0) or vx
                if not lat:
                    raise LookupError(f"Latin anchors '{vul}' found neither in the verse nor in Denis's paragraph")
            else:
                lat = expand_side(vul, vt)
            return f"[[{ref}|{drx}|{lat}]]"
        except LookupError as e:
            raise LookupError(f"{m.group(0)}: {e}\n    DR: {drt}\n    V:  {vt}")
    return Q.sub(one, en)

def expand_work(path):
    art = json.load(open(path))
    errors = []
    for i, p in enumerate(art["paras"]):
        try:
            p["en"] = expand(p["en"], art["book"], p.get("t", ""))
        except LookupError as e:
            errors.append(f"para {i + 1}: {e}")
    if errors:
        print("\n".join(errors)); sys.exit(1)
    json.dump(art, open(path, "w"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    expand_work(sys.argv[1])
    print("quotations expanded")
