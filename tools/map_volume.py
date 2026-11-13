"""Map a scanned volume's articles from the running heads in the PDF's own text layer (no OCR, no AI).

usage: python3 tools/map_volume.py VOL PDF [--write]

Every page's running head names the book, the chapter (CAP. …, or PSALMUM … for the Psalms) and the
article (ART. …). An article starts on the page before the first page whose head carries its number (or on
that page) and ends on the page where the next one starts; pages are given as [start, end] like the other
queues. Heads misread by the scan's text layer are dropped where they break the sequence. With --write the
queue goes to sources/VOL/queue.json (items already published in data/commentary are marked done).
"""
import json, os, re, subprocess, sys
from collections import Counter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# words in a running head -> book id (Douay/Vulgate canon, as in data/bible/drc); I/II/III prefixes handled below
BOOKS = [
    (r"GENES", "genesis"), (r"EXOD", "exodus"), (r"LEVIT", "leviticus"), (r"NUMER", "numbers"), (r"DEUTER", "deuteronomy"),
    (r"JOSUE", "joshua"), (r"JUDIC", "judges"), (r"RUTH", "ruth"), (r"REGUM", "kings"), (r"PARALIP", "chronicles"),
    (r"ESDR", "ezra"), (r"NEHEM", "nehemiah"), (r"TOBI", "tobit"), (r"JUDITH", "judith"), (r"ESTHER", "esther"),
    (r"\bJOB\b", "job"), (r"PSALM", "psalms"), (r"PROVERB", "proverbs"), (r"ECCLESIAST[EÆA]", "ecclesiastes"),
    (r"CANTIC", "song-of-solomon"), (r"SAPIENT", "wisdom"), (r"ECCLESIASTIC", "sirach"), (r"ISAI", "isaiah"),
    (r"JEREMI", "jeremiah"), (r"THREN|LAMENT", "lamentations"), (r"BARUCH", "baruch"), (r"EZECHIEL", "ezekiel"),
    (r"DANIEL", "daniel"), (r"OSEE", "hosea"), (r"JOEL", "joel"), (r"\bAMOS", "amos"), (r"ABDI", "obadiah"),
    (r"JON[AÆ]", "jonah"), (r"MICH[AÆ]", "micah"), (r"NAHUM", "nahum"), (r"HABAC", "habakkuk"), (r"SOPHONI", "zephaniah"),
    (r"AGG[AÆ]", "haggai"), (r"ZACHARI", "zechariah"), (r"MALACHI", "malachi"), (r"MACHAB", "maccabees"),
    (r"MATTH", "matthew"), (r"MARC", "mark"), (r"LUC[AÆ]", "luke"), (r"JOANN.*APOCAL|APOCALYP", "revelation-of-john"),
    (r"ACTUUM|ACTUS", "acts"), (r"ROMAN", "romans"), (r"CORINTH", "corinthians"), (r"GALAT", "galatians"),
    (r"EPHES", "ephesians"), (r"PHILIPP", "philippians"), (r"COLOSS", "colossians"), (r"THESSALON", "thessalonians"),
    (r"TIMOTH", "timothy"), (r"\bTITUM", "titus"), (r"PHILEMON", "philemon"), (r"HEBR[AÆ]", "hebrews"),
    (r"JACOB", "james"), (r"PETR", "peter"), (r"JUD[AÆ]", "jude"), (r"JOANN", "john"),
]
NUMBERED = {"kings": ["i-samuel", "ii-samuel", "i-kings", "ii-kings"], "chronicles": ["i-chronicles", "ii-chronicles"],
            "ezra": ["ezra", "nehemiah"], "maccabees": ["i-maccabees", "ii-maccabees"],
            "corinthians": ["i-corinthians", "ii-corinthians"], "thessalonians": ["i-thessalonians", "ii-thessalonians"],
            "timothy": ["i-timothy", "ii-timothy"], "peter": ["i-peter", "ii-peter"]}
R = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
def roman(s):
    s = s.upper().replace("L", "L").replace("1", "I").replace("|", "I")
    if not s or any(c not in R for c in s): return None
    n = 0
    for i, c in enumerate(s):
        v = R[c]; n += -v if i + 1 < len(s) and R[s[i + 1]] > v else v
    return n

def head(pdf, p):
    t = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), "-layout", pdf, "-"], capture_output=True, text=True).stdout
    for l in [l for l in t.splitlines() if l.strip()][:3]:      # the running head line only
        u = l.upper().replace("Æ", "AE").replace("Œ", "OE")
        if re.search(r"ENARR|COMMENT|EXPOS|A[RH]T\.", u): return u
    return ""

def parse(h):
    book = None
    for pat, b in BOOKS:
        if re.search(pat.replace("Æ", "AE"), h): book = b; break
    if book is None: return None
    if book in NUMBERED:
        m = re.search(r"\b(II|I|2|1|11|IL|LI)\s*\.?\s*(?:[BR]\.\s*)?(?:PAULI|PETRI|REG|PARALIP|MACHAB|ESDR)", h) or \
            re.search(r"EPISTOL\S*\s+(II|I)\b", h) or re.search(r"\b(IV|III|II|I)\s+(?:LIB|REG)", h)
        k = {"I": 0, "1": 0, "II": 1, "2": 1, "IL": 1, "LI": 1, "11": 1, "III": 2, "IV": 3}.get(m.group(1), 0) if m else 0
        book = NUMBERED[book][min(k, len(NUMBERED[book]) - 1)]
    art = re.search(r"A[RH]T\.?\s*([IVXLC1l|]+)\b", h.replace("ARTICULUS", ""))
    cap = re.search(r"(?:CAP\.?|PSALM\w*)\s*([IVXLC1l|]+)\b", h)
    return book, roman(cap.group(1)) if cap else None, roman(art.group(1)) if art else None

def build(vol, pdf):
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
    seen = []                      # (page, book, cap, art)
    for p in range(1, n + 1):
        r = parse(head(pdf, p))
        if r and r[2]: seen.append((p, *r))
    # per book, keep heads whose article number fits a rising sequence (drops misreads)
    items = []
    for book in dict.fromkeys(s[1] for s in seen):
        hs = [s for s in seen if s[1] == book]
        # the book's articles, in page order: an art is accepted when 2+ pages carry it or it follows the last one
        cnt = Counter(s[3] for s in hs); arts, last = [], 0
        for p, _, cap, art in hs:
            if art in [a for a, _ in arts]: continue
            if art == last + 1 or (art > last and cnt[art] >= 2 and art - last <= 3) or (not arts and cnt[art] >= 2):
                arts.append((art, p)); last = art
        caps = {}
        for p, _, cap, art in hs:
            if cap: caps.setdefault(art, Counter())[cap] += 1
        for k, (art, first) in enumerate(arts):
            nxt = arts[k + 1][1] if k + 1 < len(arts) else None
            end = nxt if nxt else max(p for p, b, _, a in hs if a == art)
            ch = caps.get(art, Counter()).most_common(1)[0][0] if caps.get(art) else None
            items.append({"id": f"{book}-{art:03d}", "book": book, "art": art, "chapter_guess": ch,
                          "pages": [max(1, first - 1), end], "status": "todo"})
    return items, n

if __name__ == "__main__":
    vol, pdf = sys.argv[1], sys.argv[2]
    items, n = build(vol, pdf)
    by = Counter(i["book"] for i in items)
    print(f"{vol}: {n} pages, {len(items)} articles:", dict(by))
    for b in by:
        bi = [i for i in items if i["book"] == b]
        chs = [i["chapter_guess"] for i in bi]
        gaps = [f"{bi[k]['art']}->{bi[k+1]['art']}" for k in range(len(bi) - 1) if bi[k + 1]["art"] != bi[k]["art"] + 1]
        print(f"  {b}: Art. {bi[0]['art']}-{bi[-1]['art']}, chapters {min(c for c in chs if c) if any(chs) else '?'}-"
              f"{max(c for c in chs if c) if any(chs) else '?'}, PDF {bi[0]['pages'][0]}-{bi[-1]['pages'][1]}"
              + (f", gaps in numbering: {gaps[:8]}" if gaps else ""))
    if "--write" in sys.argv:
        os.makedirs(os.path.join(ROOT, "sources", vol), exist_ok=True)
        json.dump({"volume": vol, "pdf_pages": n, "items": items},
                  open(os.path.join(ROOT, "sources", vol, "queue.json"), "w"), ensure_ascii=False, indent=1)
        print("wrote", f"sources/{vol}/queue.json")
