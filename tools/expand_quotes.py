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

def _words(hay):
    return [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"[a-z']+", hay)]

def _fuzzy(words, anchor, lo, guess, end=False):
    """Word index (first, last) of the best place for anchor words in words[lo:], or None. Exact runs first;
    otherwise the window sharing most words with the anchor (at least 60%), preferring one that begins (for a
    start) or ends (for an end) with the anchor's own first or last word; ties go nearest to guess."""
    a = anchor.split(); n = len(a); best = None
    for i in range(lo, len(words) - n + 1):
        w = [x[2] for x in words[i:i + n]]
        score = n + 1 if w == a else len(set(w) & set(a))
        if score < max(1, 0.6 * n): continue
        score += 0.5 * ((w[-1] == a[-1]) if end else (w[0] == a[0]))
        key = (-score, abs(i - guess) if guess is not None else 0)
        if best is None or key < best[0]: best = (key, i, i + n - 1)
    return best and (best[1], best[2])

def _best_window(words, q, guess=None):
    """(first, last) word indices of the stretch of words most like the word list q (words compared by their
    first four letters; about the same length in letters; at least half of q's words), or None."""
    from collections import Counter
    k4 = lambda w: w[:4]
    n = len(q); qc = Counter(map(k4, q)); qlen = sum(map(len, q)); best = None
    for L in range(max(1, int(n * .6)), int(n * 1.5) + 2):
        for i in range(0, len(words) - L + 1):
            w = [x[2] for x in words[i:i + L]]
            ov = sum((Counter(map(k4, w)) & qc).values())
            if ov < max(1, n / 2): continue
            sc = ov - 0.3 * abs(sum(map(len, w)) - qlen) / 5 + 0.5 * (k4(w[0]) == k4(q[0])) + 0.5 * (k4(w[-1]) == k4(q[-1]))
            key = (-sc, abs(i - guess) if guess is not None else 0)
            if best is None or key < best[0]: best = (key, i, i + L - 1)
    return best and (best[1], best[2])

def _snap(text, pos, words, i, end):
    """Move a guessed boundary up to two words to the nearest punctuation of the verse."""
    for d in (0, 1, -1, 2, -2):
        k = i + d
        if not 0 <= k < len(words): continue
        if end:
            j = pos[words[k][1] - 1] + 1
            if j >= len(text) or text[j] in ",;:.?!": return k
        else:
            j = pos[words[k][0]] - 1
            while j >= 0 and text[j] == " ": j -= 1
            if j < 0 or text[j] in ",;:.?!": return k
    return i

def expand_side_lenient(side, text, frac=None):
    """Like expand_side, but settles ambiguous or slightly misquoted anchors itself: an anchor that occurs
    more than once is taken at the place that fits the Vulgate span (frac = where the quotation starts and
    ends in the Latin verse, as fractions) or else gives the shortest quotation; an anchor not found word for
    word is taken at the window that shares most of its words. The result is always the Douay-Rheims's own
    words. Raises LookupError only when nothing fits."""
    an = anchors(side)
    if not an: return expand_side(side, text)
    hay, pos = norm_map(text); words = _words(hay); N = len(words)
    g0 = round(frac[0] * N) if frac else None; g1 = round(frac[1] * N) if frac else None
    exact0 = [i for i, w in enumerate(words) if [x[2] for x in words[i:i + len(an[0].split())]] == an[0].split()]
    cands = exact0 or ([_fuzzy(words, an[0], 0, g0)[0]] if _fuzzy(words, an[0], 0, g0) else [])
    if not cands and frac: cands = [_snap(text, pos, words, min(g0, N - 1), False)]
    best = None
    for i in cands:
        e = _fuzzy(words, an[1], i, g1, end=True)
        if not e and frac and g1 >= i:                                         # where the Latin span ends
            k = _snap(text, pos, words, min(max(g1 - 1, i), N - 1), True); e = (k, k)
        if not e: continue
        span = e[1] - i
        key = (abs(i - g0) + abs(e[1] - g1)) if frac else span
        if best is None or key < best[0]: best = (key, i, e[1])
    if not best: raise LookupError(f"anchors '{side}' could not be placed in the verse")
    return cut(text, pos, words[best[1]][0], words[best[2]][1])

def _frac(side, text):
    """Where a quotation (anchored, or written out) starts and ends in a verse, as fractions of its words;
    None if it cannot be placed."""
    try:
        side = side.strip()
        hay, _ = norm_map(text); words = _words(hay)
        if not words: return None
        if not anchors(side):
            if ELL.search(side): return None
            r = _best_window(words, norm_map(side)[0].split())
            return r and (r[0] / len(words), (r[1] + 1) / len(words))
        an = anchors(side)
        a = _fuzzy(words, an[0], 0, None)
        b = _fuzzy(words, an[1], a[0], None, end=True) if a else None
        if not (a and b): return None
        return a[0] / len(words), (b[1] + 1) / len(words)
    except Exception:
        return None

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
            if dr.strip() and dr.strip() != "*" and not anchors(dr) and norm_map(dr)[0].strip() not in norm_map(drt)[0]:
                # written out in full but not as the Douay-Rheims has it: a verse nearby, or its first and last words
                for dv in (1, -1, 2, -2):
                    try:
                        if norm_map(dr)[0].strip() in norm_map(verse("data/bible/drc", target, c, v + dv))[0]:
                            v += dv; ref = re.sub(r"\d+$", str(v), ref)
                            drt = verse("data/bible/drc", target, c, v); vt = verse("sources/vulgate", target, c, v); break
                    except Exception:
                        pass
                else:
                    if not ELL.search(dr):
                        hay, pos = norm_map(drt); words = _words(hay)
                        r = _best_window(words, norm_map(dr)[0].split())
                        if r is None and vul.strip():
                            f = _frac(vul, vt)
                            if f:
                                N = len(words)
                                r = (_snap(drt, pos, words, min(round(f[0] * N), N - 1), False),
                                     _snap(drt, pos, words, min(max(round(f[1] * N) - 1, 0), N - 1), True))
                        if r: dr = cut(drt, pos, words[r[0]][0], words[r[1]][1])
            try:
                drx = expand_side(dr, drt)
            except LookupError:
                drx = expand_side_lenient(dr, drt, _frac(vul, vt) if vul.strip() else None)
            if anchors(vul):            # Latin side: Denis's own words, sized by the Vulgate span
                try:
                    vx = expand_side(vul, vt)
                except LookupError:
                    try:
                        vx = expand_side_lenient(vul, vt)
                    except LookupError:
                        vx = None       # anchors in Denis's wording only (a variant reading)
                lat = from_denis(vul, latin, len(norm_map(vx)[0].split()) if vx else 0) or vx
                if not lat:
                    raise LookupError(f"Latin anchors '{vul}' found neither in the verse nor in Denis's paragraph")
            else:
                try:
                    lat = expand_side(vul, vt)
                except LookupError:
                    lat = expand_side_lenient(vul, vt)
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
