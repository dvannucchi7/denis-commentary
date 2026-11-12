"""Marginal scripture references of the Montreuil edition: read them once, then list them per article.

The printed edition gives the source of each quotation in the outer margin, in small italics
(Is. xi, 1 / Joann. i, 45 / Ibid. 46 / vers. 15), and the verse numbers of the chapter being treated.
The page OCR drops the margins, so they are read separately.

  python3 tools/margins.py read VOL PDF FIRST LAST
      Reads the margins of PDF pages FIRST..LAST (and the column line beside each note) into
      sources/VOL/margins/p<N>.json. Slow (about 15 s a page); done once, before the runs.

  python3 tools/margins.py VOL ID [CHAPTER]
      Lists, in reading order, the references in the margins of a queued article's pages, each
      checked against the Vulgate text of the book it names (the OCR misreads the small numerals,
      so the verse is confirmed by the Latin beside the note), with that Latin line. CHAPTER is the
      chapter being treated (default: the queue's chapter_guess), used for "vers. N" and verse numbers.

  Kinds: "printed" = the printed reference fits the text; "corrected" = the numerals were misread and
  the text matched a nearby verse of the same book; "allusion" = no clear match (Denis alludes, or the
  quotation is too free): the printed reference is given as read. The first and last pages of an
  article are shared with its neighbours: ignore notes before the article's heading or after its end.
"""
import json, os, re, subprocess, sys, difflib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from check_quotes import ABBR
REV = {v: k for k, v in ABBR.items()}

LAT = {  # Latin abbreviation (lower, no dots) -> book id
 "gen": "genesis", "exod": "exodus", "ex": "exodus", "lev": "leviticus", "num": "numbers", "deut": "deuteronomy",
 "jos": "joshua", "josue": "joshua", "judic": "judges", "jud": "judges", "jacob": "james", "js": "isaiah", "ruth": "ruth",
 "ireg": "i-samuel", "iireg": "ii-samuel", "iiireg": "i-kings", "ivreg": "ii-kings",
 "ipar": "i-chronicles", "iipar": "ii-chronicles", "iesdr": "ezra", "iiesdr": "nehemiah", "esdr": "ezra",
 "tob": "tobit", "judith": "judith", "esth": "esther", "job": "job", "ps": "psalms", "psal": "psalms",
 "prov": "proverbs", "eccle": "ecclesiastes", "eccles": "ecclesiastes", "cant": "song-of-solomon",
 "sap": "wisdom", "eccli": "sirach", "is": "isaiah", "isa": "isaiah", "jer": "jeremiah", "thren": "lamentations",
 "bar": "baruch", "ezech": "ezekiel", "dan": "daniel", "osee": "hosea", "joel": "joel", "amos": "amos",
 "abd": "obadiah", "jon": "jonah", "mich": "micah", "nah": "nahum", "hab": "habakkuk", "habac": "habakkuk",
 "soph": "zephaniah", "agg": "haggai", "zach": "zechariah", "mal": "malachi", "imach": "i-maccabees",
 "iimach": "ii-maccabees", "matth": "matthew", "matt": "matthew", "marc": "mark", "luc": "luke",
 "joan": "john", "joann": "john", "act": "acts", "rom": "romans", "icor": "i-corinthians", "iicor": "ii-corinthians",
 "gal": "galatians", "eph": "ephesians", "ephes": "ephesians", "philip": "philippians", "philipp": "philippians",
 "coloss": "colossians", "col": "colossians", "ithess": "i-thessalonians", "iithess": "ii-thessalonians",
 "itim": "i-timothy", "iitim": "ii-timothy", "tit": "titus", "philem": "philemon", "hebr": "hebrews",
 "jac": "james", "ipetr": "i-peter", "iipetr": "ii-peter", "ijoan": "i-john", "ijoann": "i-john",
 "iijoann": "ii-john", "iiijoann": "iii-john", "apoc": "revelation-of-john",
}

_vul = {}
def vul(b):
    if b not in _vul: _vul[b] = json.load(open(os.path.join(ROOT, "sources/vulgate", b + ".json")))
    return _vul[b]
def norm(s):
    s = s.lower().replace("æ", "e").replace("œ", "e").replace("ae", "e").replace("oe", "e").replace("j", "i").replace("v", "u")
    return re.findall(r"[a-z]+", s)
STOP = set("et in ad de non est sunt qui que quod ut cum quum enim autem sed ego tu ipse eius eum ei me te se nos uos a ab ex e per pro sicut quia".split())

def roman(s):
    """Roman numeral as the OCR reads it: n/u = ii, t/1 = i; l = 50 only at the start or after x."""
    s = s.lower().replace("n", "ii").replace("u", "ii").replace("t", "i").replace("1", "i").replace("m", "iii").replace("w", "iv")
    s = "".join("L" if c == "l" and ((i == 0 and len(s) > 1) or (i > 0 and s[i - 1] == "x")) else ("i" if c == "l" else c)
                for i, c in enumerate(s))
    R = {"i": 1, "v": 5, "x": 10, "L": 50, "c": 100}
    if not s or any(c not in R for c in s): return None
    n = 0
    for i, c in enumerate(s):
        v = R[c]; n += -v if i + 1 < len(s) and R[s[i + 1]] > v else v
    return n

def roman_alts(tok):
    """Every chapter number an OCR'd numeral could be (1/l = i or l; n/u = ii or iii; m = iii; w = iv or v)."""
    if not tok: return set()
    if tok.isdigit(): return {int(tok)}
    opts = {"1": ["i", "l"], "l": ["i", "l"], "n": ["ii", "iii"], "u": ["ii", "iii", "v"], "m": ["iii"],
            "w": ["iv", "v"], "t": ["i"]}
    seqs = [""]
    for c in tok.lower():
        seqs = [q + o for q in seqs for o in opts.get(c, [c])][:64]
    out = set()
    R = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}
    for q in seqs:
        if not q or any(c not in R for c in q): continue
        n = 0
        for i, c in enumerate(q):
            v = R[c]; n += -v if i + 1 < len(q) and R[q[i + 1]] > v else v
        if 0 < n <= 150: out.add(n)
    return out

# ---------------------------------------------------------------- reading the page images
def read(vol, pdf, first, last):
    import numpy as np
    from PIL import Image, ImageOps
    env = dict(os.environ, TESSDATA_PREFIX=os.environ.get("TESSDATA_PREFIX", "/home/claude/tessdata"))
    outdir = os.path.join(ROOT, "sources", vol, "margins"); os.makedirs(outdir, exist_ok=True)
    tmp = f"/tmp/_marg{os.getpid()}"
    def tsv(img, psm):
        img.save(tmp + ".png")
        out = subprocess.run(["tesseract", tmp + ".png", "-", "-l", "lat", "--psm", psm, "-c", "tessedit_create_tsv=1"],
                             capture_output=True, text=True, env=env).stdout
        lines = {}
        for row in out.splitlines()[1:]:
            f = row.split("\t")
            if len(f) < 12 or not f[11].strip(): continue
            L = lines.setdefault((f[2], f[3], f[4]), {"y": 10**9, "y2": 0, "w": []})
            y, hh = int(f[7]), int(f[9]); L["y"] = min(L["y"], y); L["y2"] = max(L["y2"], y + hh); L["w"].append(f[11])
        return sorted(({"y": (L["y"] + L["y2"]) / 2, "text": " ".join(L["w"])} for L in lines.values()), key=lambda l: l["y"])
    def text_box(g):
        h, w = g.shape; rows = (g < 128).sum(axis=1); inked = rows > w * .003
        ys = np.where(inked)[0]; top, bottom = ys[0], ys[-1]; y = top
        while y < h and inked[y]: y += 1
        blank = 0
        while y < h and not inked[y]: y += 1; blank += 1
        if blank > h * .006 and y < h * .2: top = y
        return max(0, top - 6), bottom
    def gutter(g):
        h, w = g.shape; ink = (g[int(h * .08):int(h * .95)] < 128).sum(axis=0).astype(float)
        lo, hi = int(w * .40), int(w * .60); k = max(3, w // 200)
        return lo + int(np.argmin(np.convolve(ink, np.ones(k) / k, mode="same")[lo:hi]))
    for p in range(first, last + 1):
        dest = os.path.join(outdir, f"p{p}.json")
        if os.path.exists(dest): continue
        subprocess.run(["pdftoppm", "-f", str(p), "-l", str(p), "-r", "600", "-gray", "-png", "-singlefile", pdf, tmp + "p"], check=True)
        im = Image.open(tmp + "p.png").convert("L"); g = np.array(im); h, w = g.shape
        if (g < 128).sum() < w:                       # a blank page
            json.dump([], open(dest, "w")); print(p, "blank", flush=True); continue
        try:
            top, bottom = text_box(g); gx = gutter(g); band = int(w * .018)
        except (IndexError, ValueError):
            json.dump([], open(dest, "w")); print(p, "no text block", flush=True); continue
        def outer(x0, x1, left):
            ink = (g[top:bottom, x0:x1] < 128).sum(axis=0).astype(float)
            k = max(5, w // 150); sm = np.convolve(ink, np.ones(k) / k, mode="same")
            d = np.where(sm > sm.max() * .30)[0]
            return x0 + max(0, d[0] - 10) if left else x0 + min(x1 - x0, d[-1] + 10)
        la, rb = outer(0, gx - band, True), outer(gx + band, w, False)
        res = []
        for side, mb, cb in (("L", (0, la), (la, gx - band // 3)), ("R", (rb, w), (gx + band // 3, rb))):
            m = ImageOps.expand(im.crop((mb[0], top, mb[1], bottom)).point(lambda v: 0 if v < 170 else 255), border=80, fill=255)
            ml = [dict(l, y=l["y"] - 80) for l in tsv(m, "6")]
            if not ml: continue
            col = im.crop((cb[0], top, cb[1], bottom)); col = col.resize((col.width // 2, col.height // 2))
            cl = [dict(l, y=l["y"] * 2) for l in tsv(col, "4")]
            for l in ml:
                i = min(range(len(cl)), key=lambda k: abs(cl[k]["y"] - l["y"])) if cl else 0
                res.append({"page": p, "side": side, "y": round(l["y"]), "raw": l["text"],
                            "beside": cl[i]["text"] if cl else "",
                            "ctx": " ".join(c["text"] for c in cl[max(0, i - 1): i + 3])})
        json.dump(res, open(dest + ".tmp", "w"), ensure_ascii=False, indent=0); os.replace(dest + ".tmp", dest)
        print(p, len(res), flush=True)
    for f in (tmp + ".png", tmp + "p.png"):
        if os.path.exists(f): os.remove(f)

# ---------------------------------------------------------------- turning readings into references
cur_book, cur_ch = None, None
last_chtok = None
KEYS = list(LAT)
FIX = [(r"^[\]\[|/(]\s*", "I"), (r"^[*'\"!»^:.\-\s]+", "")]
LETTERS = str.maketrans("ÁÀÂÉÈÍÌÓÒÚ", "AAAEEIIOOU")
BOOKFIX = {"hom": "rom", "bom": "rom", "heg": "reg", "zteg": "reg", "teg": "reg", "ateg": "reg", "fteg": "reg",
           "eg": "reg", "aeg": "reg", "reo": "reg", "fleg": "reg", "z1eg": "reg", "azteg": "reg", "aleg": "reg", "neg": "reg", "zeg": "reg", "p5": "ps", "ps5": "ps", "i5": "is", "1s": "is", "15": "is", "is5": "is",
           "s": "ps", "zod": "exod", "ezod": "exod", "ezrod": "exod", "lue": "luc", "ron": "rom", "acl": "act",
           "huth": "ruth", "luth": "ruth", "authn": "ruth", "zluth": "ruth", "1e": "gen", "3en": "gen", "8n": "gen",
           "id": "ibid", "jbbid": "ibid", "bid": "ibid", "lbidem": "ibid", "ibidem": "ibid", "ld": "ibid",
           "49g": "agg", "a9g9": "agg", "alat": "gal", "baruchw": "bar", "baruch": "bar", "lj": "is"}
NUMPRE = {"i": 1, "1": 1, "l": 1, "ii": 2, "il": 2, "ie": 2, "ll": 2, "i]": 2, "iii": 3, "ih": 3, "hl": 3, "ill": 3,
          "iv": 4}

def book_of(word):
    k = re.sub(r"[^a-z0-9]", "", word.lower())
    k = BOOKFIX.get(k, k)
    if k in LAT: return LAT[k], k
    kk = k.replace("1", "i").replace("5", "s")
    if kk in LAT: return LAT[kk], kk
    m = difflib.get_close_matches(kk, KEYS + ["ibid", "vers", "reg"], n=1, cutoff=0.67)
    return (LAT.get(m[0]), m[0]) if m else (None, None)

def parse(t, prev, cur_ch):
    t = t.translate(LETTERS).strip(" .;,")
    for a_, b_ in FIX: t = re.sub(a_, b_, t)
    # numeral prefix (I/II/III/IV) then the book word
    m = re.match(r"^([I1l\]H]{1,3}|IV|IE)[\s.]+([A-Za-z][A-Za-z ]{1,7}?)\.?\s*([ivxlcnutIVXLC1\d].*|)$", t)
    pre = 0
    if m and NUMPRE.get(m.group(1).lower().replace("]", "i")):
        pre = NUMPRE[m.group(1).lower().replace("]", "i")]; word, rest = m.group(2), m.group(3)
    else:
        m = re.match(r"^([A-Za-z0-9]{0,2}[A-Za-z]{1,8})\.?[\s,]*(.*)$", t)
        if not m: return None
        word, rest = m.group(1), m.group(2)
        if re.fullmatch(r"[ivxlcnut]+", word.lower()) and prev and not book_of(word)[0]:   # a bare "xxxi, 24" continues the last book
            word, rest = "", t
    if word == "":
        book, ch = prev[0], None
    else:
        b, key = book_of(word.replace(" ", ""))
        if pre:                                   # I/II/III + book: look the pair up as one key
            w0 = re.sub(r"[^a-z]", "", word.lower())
            w0 = {"heg": "reg", "aeg": "reg", "zteg": "reg", "fleg": "reg", "teg": "reg", "reo": "reg", "hom": "rom"}.get(w0, w0)
            cand = difflib.get_close_matches(w0, ["reg", "par", "cor", "thess", "tim", "petr", "joann", "joan", "mach", "esdr"], n=1, cutoff=0.6)
            if cand:
                key = cand[0]
                b = LAT.get({1: "i", 2: "ii", 3: "iii", 4: "iv"}[pre] + key)
                if key == "reg": key = "reg"
        if key == "ibid":
            if not prev: return None
            book, ch = prev
        elif key == "vers":
            book, ch = cur_book, cur_ch
        elif key == "reg":
            book, ch = {1: "i-samuel", 2: "ii-samuel", 3: "i-kings", 4: "ii-kings"}.get(pre or 1), None
        elif b:
            if pre and key in ("par", "cor", "thess", "tim", "petr", "joann", "mach", "esdr"):
                b = LAT.get({1: "i", 2: "ii", 3: "iii"}.get(pre, "i") + key, b)
            elif pre and LAT.get("i" * pre + key): b = LAT["i" * pre + key]
            book, ch = b, None
        else:
            return None
    orig = re.findall(r"[ivxlcnutmw1]*[ivxlcnutmw][ivxlcnutmw1]*|[0-9]+", rest.lower())
    rest = re.sub(r"(?<=[ivxlcnutmw])1|1(?=[ivxlcnutmw])", "i", rest.lower())
    toks = re.findall(r"[0-9]+|[ivxlcnutmw]+", rest)
    global last_chtok
    last_chtok = None
    if toks and not toks[0].isdigit() and roman(toks[0]):
        ch = roman(toks[0]); last_chtok = orig[0] if orig else toks[0]; toks = toks[1:]
    elif ch is None and toks and toks[0].isdigit() and len(toks) > 1:
        ch = int(toks[0]); toks = toks[1:]
    vs = [int(x) for x in toks if x.isdigit()]
    return book, ch, vs

def sc(words, verse):
    vw = set(w for w in norm(verse) if w not in STOP and len(w) > 2)
    return sum(1 for w in set(words) if w in vw)

def resolve(book, ch, vs, ctx):
    words = norm(ctx); chs = vul(book)
    def get(c, v):
        try: return sc(words, chs[c - 1][v - 1])
        except (IndexError, TypeError): return -1
    allv = [(sc(words, verse), ci, vi) for ci, chap in enumerate(chs, 1) for vi, verse in enumerate(chap, 1)]
    best = max(allv)
    # 1. the printed reference (any reading of its numerals) if its verse fits the text at all
    cands = sorted({ch} | roman_alts(last_chtok or ""), key=lambda c: c != ch) if ch else []
    for v in vs[:1]:
        fits = [(get(c, v), c) for c in cands]
        fits = [f for f in fits if f[0] >= 2]
        if fits:                                  # the plain reading wins whenever it fits at all
            main = [f for f in fits if f[1] == ch]
            s_, c_ = main[0] if main else max(fits)
            return c_, v, s_, "printed"
    # 2. the printed verse in a neighbouring chapter (the chapter numeral misread)
    if ch and vs:
        alt = [(get(c, vs[0]), c) for c in range(ch - 2, ch + 3) if c != ch]
        a = max(alt) if alt else (0, 0)
        if a[0] >= 2 and a[0] >= 0.6 * best[0]: return a[1], vs[0], a[0], "printed"
    # 3. near the printed chapter (numerals are often misread by one)
    if ch:
        near = [x for x in allv if abs(x[1] - ch) <= 2]
        nb = max(near) if near else (0,)
        if nb[0] >= 3: return nb[1], nb[2], nb[0], "near"
    # 3. anywhere in the book, if clear
    if best[0] >= 4: return best[1], best[2], best[0], "book"
    return ch, (vs[0] if vs else None), 0, "allusion"


def article(vol, item_id, chapter=None, quiet=False):
    global cur_book, cur_ch
    q = json.load(open(os.path.join(ROOT, "sources", vol, "queue.json")))
    item = next(i for i in q["items"] if i["id"] == item_id)
    cur_book, cur_ch = item["book"], int(chapter or item.get("chapter_guess") or 0)
    raw, missing = [], []
    article.missing = missing
    for p in range(item["pages"][0], item["pages"][1] + 1):
        f = os.path.join(ROOT, "sources", vol, "margins", f"p{p}.json")
        if not os.path.exists(f):
            missing.append(p)
            if not quiet: print(f"(margins of PDF {p} not read yet)")
            continue
        raw += json.load(open(f))
    # group margin lines into references: join continuations, split at ";"
    out = []
    for side in ("L", "R"):
        for p in sorted(set(r["page"] for r in raw)):
            lines = [r for r in raw if r["page"] == p and r["side"] == side]
            items = []
            for l in lines:
                t = l["text"] if "text" in l else l["raw"]
                prevt = items[-1]["raw"].rstrip() if items else ""
                if items and l["y"] - items[-1]["y"] < 140 and (prevt.endswith((",", "-")) or re.fullmatch(r"[^a-z]*[A-Za-z]+\.?", prevt)) \
                        and re.match(r"^[\divxlcnut1\s,.\-;:]+$", t.strip().lower()):
                    items[-1]["raw"] += " " + t
                else:
                    items.append(dict(l, raw=t))
            for it in items:
                for k, piece in enumerate(it["raw"].split(";")):
                    if piece.strip(): out.append(dict(it, raw=piece.strip(), cont=k > 0))
    out.sort(key=lambda r: (r["page"], r["side"], r["y"]))

    rows = []          # what is printed, also returned for tools/recheck.py
    if not quiet:
        print(f"Marginal references, {item_id} (PDF {item['pages'][0]}-{item['pages'][1]}; column L then R on each page)")
    prev, page = None, None
    for it_ in out:
        raw_ = it_["raw"].strip(" .")
        if it_["page"] != page:
            page = it_["page"]
            if not quiet: print(f"-- PDF {page}")
        row = dict(page=it_["page"], side=it_["side"], beside=it_["beside"], ctx=it_.get("ctx", ""), printed=raw_)
        if re.fullmatch(r"\d{1,2}", raw_):
            rows.append(dict(row, kind="verse", verse=int(raw_)))
            if not quiet: print(f"   {it_['side']}  verse {raw_} begins: {it_['beside'][:60]}")
            continue
        if re.search(r"sec\.?\s*Hebr", raw_, re.I) or len(raw_) < 4: continue
        pr = parse(raw_, prev, cur_ch)
        if not pr or not pr[0]:
            rows.append(dict(row, kind="unread"))
            if not quiet: print(f"   {it_['side']}  [unread: {raw_!r}] beside: {it_['beside'][:60]}")
            continue
        book, ch, vs = pr
        c, v, s, how = resolve(book, ch, vs, it_["ctx"])
        if how == "allusion" and book in ("i-john", "ii-john", "iii-john"):
            # a stray mark before "Joann." is read as "I": try the Gospel when the Epistle does not fit
            c2, v2, s2, how2 = resolve("john", ch, vs, it_["ctx"])
            if how2 != "allusion" or (ch and ch > 5):
                book, c, v, s, how = "john", c2, v2, s2, how2
        prev = (book, c)
        kind = {"printed": "printed", "near": "corrected", "book": "corrected", "allusion": "allusion?"}[how]
        more = f"-{vs[-1]}" if how == "printed" and len(vs) > 1 and vs[-1] > v else ""
        ref = f"{REV[book]} {c}:{v}{more}" if v else f"{REV[book]} {c}"
        rows.append(dict(row, kind=kind, ref=ref, book=book, ch=c, v=v))
        if not quiet: print(f"   {it_['side']}  {ref:<16} {kind:<10} (printed: {raw_})  beside: {it_['beside'][:60]}")
    return rows

if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "read":
        read(a[1], a[2], int(a[3]), int(a[4]))
    elif len(a) >= 2:
        article(a[0], a[1], a[2] if len(a) > 2 else None)
    else:
        print(__doc__)
