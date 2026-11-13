"""Transcribe scanned pages with the API (instead of Tesseract), then cut the articles from the transcription.

A cheaper model than the translator copies each page exactly as printed (it does not translate or correct),
so the translator later works from an independent reading, and its Latin can be checked against this one.

  python3 tools/transcribe.py submit VOL FIRST LAST [--model haiku|sonnet]   pages to transcribe (a batch)
  python3 tools/transcribe.py collect                                         save finished pages
  python3 tools/transcribe.py cut VOL                                         articles + queue from the pages
  python3 tools/transcribe.py test VOL PAGE [--model …]                       one page now, printed

Pages go to sources/VOL/transcribed/p<N>.txt in this form:
  HEAD: <running head as printed>
  === LEFT ===            (then === RIGHT ===; a heading across both columns sits between them as ### …)
  text, one printed line per line, hyphenated words rejoined; italics as _…_;
  a margin note as ⟦Coloss. ii, 9⟧ at the start of the line it stands beside; a verse number in the
  margin as ⟦v. 15⟧
"""
import json, os, re, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import batch
MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5"}
PROMPT = """Transcribe this printed page of a Latin book (Dionysius Cartusianus, Opera Omnia, Montreuil, 1896–) exactly
as printed. Do not translate, modernize, correct or complete anything; copy Denis's Latin letter for letter,
with its spelling and punctuation (æ, œ, j, quum, ejus …). You are given the page's left and right columns
(each image includes that column's outer margin). Write:

HEAD: the running head line at the top of the page, as printed (page number, title, ART. number)
=== LEFT ===
the left column, one printed line per line
=== RIGHT ===
the right column, one printed line per line

Rules:
- Rejoin a word hyphenated at the end of a line (write it whole on the first line).
- Mark italic words (the printer sets quotations of Scripture in italics) as _like this_.
- A heading set in capitals or centred (ARTICULUS …, its title, PROOEMIUM, a book title) goes on its own
  line starting with "### ". If such a heading spans both columns in the middle of the page, put it at the
  point where it falls: after the left-column text above it and before the left-column text below it,
  in reading order, and say "=== LEFT (continued) ===" / "=== RIGHT (continued) ===" as needed.
- A marginal note (a Scripture reference such as "Coloss. ii, 9." or "Ibid. 3.", or a verse number such as
  "15") goes at the start of the line it stands beside, in double brackets: ⟦Coloss. ii, 9.⟧ or ⟦v. 15⟧.
  Copy the reference exactly as printed, even its numerals.
- Leave out the letters A B C D printed in the gutter between the columns.
- If something cannot be read, write […] there. Never guess.
Output only the transcription."""

def state():
    p = os.path.join(batch.BATCH_DIR, "transcribe.json")
    return json.load(open(p)) if os.path.exists(p) else {"batches": [], "cost": 0.0}
def save(st):
    os.makedirs(batch.BATCH_DIR, exist_ok=True); json.dump(st, open(os.path.join(batch.BATCH_DIR, "transcribe.json"), "w"), indent=1)

def request(vol, p, model):
    content = []
    for side, data in batch.page_images(batch.VOLS[vol]["pdf"], p):
        content += [{"type": "text", "text": f"{side} column:"},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}}]
    content.append({"type": "text", "text": PROMPT})
    return {"model": model, "max_tokens": 24000, "messages": [{"role": "user", "content": content}]}

PRICE = {"claude-haiku-5-5": (0.05, 0.25), "claude-sonnet-5-5": (1.0, 5.0)}   # batch $/M in, out (Haiku: lowest tier)
def cost(model, u, live=False):
    i, o = PRICE[model]; f = 2 if live else 1
    return f * ((u.get("input_tokens") or 0) * i + (u.get("output_tokens") or 0) * o) / 1e6

def out_path(vol, p):
    d = os.path.join(ROOT, "sources", vol, "transcribed"); os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"p{p}.txt")

def cmd_test(vol, p, model):
    c = batch.client(); m = c.messages.create(**request(vol, p, model))
    t = "".join(b.text for b in m.content if b.type == "text")
    print(t); print(f"\n[{model}: {m.usage.input_tokens} in, {m.usage.output_tokens} out, ${cost(model, m.usage.model_dump(), True):.4f}]")
    return t

def cmd_submit(vol, a, b, model):
    st = state(); c = batch.client()
    sent = {p for bt in st["batches"] if bt["vol"] == vol for p in range(bt["pages"][0], bt["pages"][1] + 1)}
    pages = [p for p in range(a, b + 1) if not os.path.exists(out_path(vol, p)) and p not in sent]
    for i in range(0, len(pages), 300):                # ~0.5 MB of images a page: stay well under 256 MB a batch
        chunk = pages[i:i + 300]
        reqs = [{"custom_id": f"{vol}-p{p}", "params": request(vol, p, model)} for p in chunk]
        bt = c.messages.batches.create(requests=reqs)
        st["batches"].append({"id": bt.id, "vol": vol, "pages": [chunk[0], chunk[-1]], "model": model, "open": True})
        save(st); print("sent", bt.id, f"PDF {chunk[0]}-{chunk[-1]} ({len(chunk)} pages)", flush=True)

def cmd_collect():
    st = state(); c = batch.client(); left = 0
    for b in [b for b in st["batches"] if b["open"]]:
        info = c.messages.batches.retrieve(b["id"])
        if info.processing_status != "ended":
            left += 1; print(b["id"], b["vol"], b["pages"], info.processing_status, info.request_counts.model_dump()); continue
        for r in c.messages.batches.results(b["id"]):
            vol, p = r.custom_id.rsplit("-p", 1)
            if r.result.type == "succeeded":
                m = r.result.message
                open(out_path(vol, int(p)), "w").write("".join(x.text for x in m.content if x.type == "text"))
                st["cost"] += cost(b["model"], m.usage.model_dump())
        b["open"] = False; save(st); print("saved", b["id"], b["vol"], b["pages"])
    print(f"transcription spent so far: ${st['cost']:.2f}; batches still open: {left}")
    return left

R = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
def roman(s):
    s = s.upper()
    if not s or any(ch not in R for ch in s): return None
    n = 0
    for i, ch in enumerate(s):
        v = R[ch]; n += -v if i + 1 < len(s) and R[s[i + 1]] > v else v
    return n

BAD = re.compile(r"can.t see|don.t see|no (page )?image|didn.t come through|not attached|upload", re.I)
def bad_pages(vol):
    """Pages whose transcription failed (empty, or the model said it saw no image)."""
    d = os.path.join(ROOT, "sources", vol, "transcribed"); out = []
    for f in os.listdir(d):
        t = open(os.path.join(d, f)).read()
        if len(t.strip()) < 40 or (BAD.search(t[:400]) and "===" not in t): out.append(int(f[1:-4]))
    return sorted(p for p in out if batch.page_images(batch.VOLS[vol]["pdf"], p))     # blank pages have no columns

def cmd_redo(vol, model):
    """Send the failed pages of a volume again (once each)."""
    st = state(); done = set(st.setdefault("redone", {}).get(vol, []))
    pages = [p for p in bad_pages(vol) if p not in done or "--again" in sys.argv]
    if not pages:
        st["redone"][vol] = sorted(done); save(st); print(vol, "nothing to redo"); return
    for p in pages: os.remove(out_path(vol, p))
    c = batch.client()
    reqs = [{"custom_id": f"{vol}-p{p}", "params": request(vol, p, model)} for p in pages]
    bt = c.messages.batches.create(requests=reqs)
    st["batches"].append({"id": bt.id, "vol": vol, "pages": [pages[0], pages[-1]], "model": model, "open": True, "redo": pages})
    st["redone"][vol] = sorted(done | set(pages)); save(st)
    print(vol, "redo", len(pages), "pages in", bt.id)

ORD = [("CENTESIM", 100), ("NONAGESIM", 90), ("OCTOGESIM", 80), ("SEPTUAGESIM", 70), ("SEXAGESIM", 60),
       ("QUINQUAGESIM", 50), ("QUADRAGESIM", 40), ("TRIGESIM", 30), ("TRICESIM", 30), ("VIGESIM", 20), ("VICESIM", 20),
       ("UNDECIM", 11), ("DUODECIM", 12), ("DECIM", 10), ("PRIM", 1), ("SECUND", 2), ("TERTI", 3), ("QUART", 4),
       ("QUINT", 5), ("SEXT", 6), ("SEPTIM", 7), ("OCTAV", 8), ("NON", 9)]
def ordinal(words):
    """'QUADRAGESIMI SEPTIMI' -> 47, 'TERTIIDECIMI' -> 13, 'DUODEVIGESIMI' -> 18; None if not an ordinal."""
    w = re.sub(r"[^A-Z]", "", words.upper().replace("Æ", "AE"))
    n, i, sub = 0, 0, 0
    while i < len(w):
        if w.startswith("DUODE", i) and not w.startswith("DUODECIM", i): sub = 2; i += 5; continue
        if w.startswith("UNDE", i) and not w.startswith("UNDECIM", i): sub = 1; i += 4; continue
        for stem, v in ORD:
            if w.startswith(stem, i):
                n += v - sub; sub = 0; i += len(stem)
                while i < len(w) and w[i] in "IUSOAEM" and not any(w.startswith(s2, i) for s2, _ in ORD): i += 1
                break
        else:
            if w.startswith("ET", i): i += 2; continue
            break
    return n or None

HEADING = re.compile(r"^[#*\s]*ARTICU(?:LUS|[\[…])?\S*\s*([IVXLC]+|PRIMUS)?\b")      # capitals only
EXPO = re.compile(r"^[#*\s]*(?:EXPOSITIO|EXPLANATIO|ELUCIDATIO|ENARRATIO|DECLARATIO)\s+(?:[A-ZÆ]+\s+){0,3}?(?:([A-ZÆ]+)\s+)?(CAPITULI|PSALMI)\b\s*([A-ZÆ ]*)")
FRONT = re.compile(r"^#+\s*(PRO(?:OE|Œ)MIUM|PRÆFATIO|PRAEFATIO|PROLOGUS|EPISTOLA NUNCUPATORIA|ENARRATIO(?!.*\bCAP)|IN EPISTO|COMMENTARI\w*\s+IN\b(?!.*\bCAP))", re.I)
END = re.compile(r"INDEX|LOCA S\. ?SCRIPTUR|TABULA|ELENCHUS|CATALOGUS", re.I)

PART_MAX = 12      # pages; about 70k output tokens of Latin and English

def cmd_cut(vol, write=True):
    """Cut articles. Starts: ARTICULUS headings (numbered or not), or an EXPOSITIO CAPITULI/PSALMI line that has no
    ARTICULUS heading just before it. A repeated heading of the current article is a continuation. Book prefaces and
    prologues close the article before them. Books: a new book starts where the numbering goes back to I; its name is
    the commonest book in its running heads. Chapter or psalm: from the EXPOSITIO line, else the running heads."""
    import map_volume
    from collections import Counter
    d = os.path.join(ROOT, "sources", vol, "transcribed")
    pages = sorted(int(f[1:-4]) for f in os.listdir(d) if f.startswith("p"))
    arts, cur, recent, after_front = [], None, [], False
    for p in pages:
        t = open(os.path.join(d, f"p{p}.txt")).read()
        hm = re.search(r"^\W*HEAD\W*(.*)$", t, re.M); h = hm.group(1).strip() if hm else ""
        if END.search(h) and arts: break
        r = map_volume.parse(h.upper().replace("Æ", "AE").replace("Œ", "OE")) if h else None
        if cur is not None and r: cur["heads"].append(r)
        body = t.splitlines()
        if re.search(r"ARTICULUS\s+(PRIMUS|[IVXLC]+)\b", h) and not re.search(r"^[#*\s]*ARTICU", t, re.M):      # the article's heading put into the HEAD line
            body = ["### " + x.strip() for x in re.split(r"\s+[—–-]\s+", h)
                    if re.match(r"(ARTICULUS|EXPOSITIO|EXPLANATIO|ELUCIDATIO|DECLARATIO)\b", x.strip())] + body
        for line in body:
            if re.match(r"^\W*HEAD\b", line) or line.startswith("==="): continue
            s = line.strip()
            if cur is None and after_front and re.match(r"^⟦(v\.\s*)?1⟧", s):
                # a book's text begins with no heading in the transcription (or none in print: Philemon)
                cur = {"art": 1, "first": p, "last": p, "lines": [], "heads": [r] if r else [], "chap": 1, "fresh": True}
                arts.append(cur); after_front = False
            m = HEADING.match(s)
            if m and len(s) < 60:
                g = (m.group(1) or "").upper()
                n = 1 if g == "PRIMUS" else (roman(g) if g else None)
                if cur is not None and n is not None and n == cur["art"]: recent.append("ART"); continue
                if n is None and cur is None: n = 1          # an unreadable number straight after a book's preface
                cur = {"art": n, "first": p, "last": p, "lines": [(p, s.lstrip("#* "))], "heads": [r] if r else [], "chap": None,
                       "fresh": after_front}
                arts.append(cur); recent = ["ART"]; after_front = False; continue
            e = EXPO.match(s)
            if e:
                k = ordinal(e.group(1)) if e.group(1) else ordinal(e.group(3))
                if cur is None or not (cur["chap"] is None and len(cur["lines"]) < 30 or cur["chap"] == k):
                    # a chapter heading with no ARTICULUS heading before it (lost in transcription); the same chapter
                    # heading again is the title repeated over the other column
                    cur = {"art": cur["art"] + 1 if cur is not None and cur["art"] else (None if cur is not None else 1), "first": p, "last": p, "lines": [], "heads": [r] if r else [],
                           "chap": None, "fresh": cur is None and after_front}
                    arts.append(cur); after_front = False
                if cur is not None and cur["chap"] is None: cur["chap"] = k
            elif FRONT.match(s) and len(s) < 90:
                cur = None; after_front = True
            if s: recent.append(s)
            if cur is not None: cur["lines"].append((p, line)); cur["last"] = p
    # number the unnumbered; split into books where the numbering restarts
    books, prev = [], None
    for i, a in enumerate(arts):
        if a["art"] is None: a["art"] = (prev or 0) + 1
        nxt = arts[i + 1]["art"] if i + 1 < len(arts) else None
        if prev and a["art"] < prev and nxt == prev + 2: a["art"] = prev + 1     # a misread number (L read as I)
        if prev is None or (a["art"] <= prev and a["art"] <= 2) or (a["fresh"] and a["art"] <= 3 and a["art"] < prev): books.append([])
        books[-1].append(a); prev = a["art"]
    q = {"volume": vol, "items": []}; report = []; seen = Counter()
    ad = os.path.join(ROOT, "sources", vol, "articles")
    if write and os.path.isdir(ad):
        for f in os.listdir(ad): os.remove(os.path.join(ad, f))
    os.makedirs(ad, exist_ok=True)
    for bk in books:
        votes = Counter(r[0] for a in bk for r in a["heads"] if r and r[0])
        name = votes.most_common(1)[0][0] if votes else None
        for a in bk:
            hc = Counter(r[1] for r in a["heads"] if r and r[0] == name and r[1])
            a["chap"] = a["chap"] or (hc.most_common(1)[0][0] if hc else None)
        for x, y in zip(bk, bk[1:]):            # chapters do not go backwards within a book: a misread
            if x["chap"] and y["chap"] and y["chap"] < x["chap"]: y["chap"] = x["chap"]
        nch = len(json.load(open(os.path.join(ROOT, "data/bible/drc", name + ".json")))) if name and os.path.exists(os.path.join(ROOT, "data/bible/drc", (name or "x") + ".json")) else None
        got = {a["chap"] for a in bk if a["chap"]}
        first = min(got) if got else None; last = max(got) if got else None
        missing = [c for c in range(first or 1, (last or 0) + 1) if c not in got]
        long = [f"Art. {a['art']} ({a['first']}-{a['last']})" for a in bk if a["last"] - a["first"] > 40]
        nums = [a["art"] for a in bk]; dup = [n for n, k in Counter(nums).items() if k > 1]
        line = f"{name}: {len(bk)} articles, PDF {bk[0]['first']}-{bk[-1]['last']}, chapters {first}-{last}" + (f" of {nch}" if nch else "")
        probs = []
        if not name: probs.append("book not identified")
        if missing: probs.append(f"no article starts in chapter(s) {missing} (fine if an article covers two chapters)")
        if long: probs.append("very long: " + ", ".join(long))
        if dup: probs.append(f"repeated article numbers {dup}")
        report.append(line + ("; CHECK: " + "; ".join(probs) if probs else ""))
        for a in bk:
            if not name: continue
            seen[a["art"]] += 1; k = seen[a["art"]]
            iid = f"{name}-{a['art']:03d}" + (f"-{k}" if k > 1 else "")
            # an article of more than PART_MAX pages goes out in parts (one answer could not hold it all);
            # the parts are put back together when they are published (tools/add_article.py)
            span = a["last"] - a["first"] + 1
            n = -(-span // PART_MAX) if span > PART_MAX + 2 else 1
            step = -(-span // n)
            for j in range(n):
                lo, hi = a["first"] + j * step, (a["first"] + (j + 1) * step - 1 if j < n - 1 else a["last"])
                lines = [l for pg, l in a["lines"] if lo <= pg <= hi]
                pid = iid + (f"-part{j + 1}" if n > 1 else "")
                if write: open(os.path.join(ROOT, "sources", vol, "articles", pid + ".txt"), "w").write("\n".join(lines))
                heads = Counter(r[1] for r in a["heads"] if r and r[0] == name and r[1])
                item = {"id": pid, "book": name, "art": a["art"], "chapter_guess": a["chap"],
                        "pages": [lo, hi], "status": "todo", "source": "transcribed"}
                if n > 1: item.update(part=j + 1, parts=n)
                q["items"].append(item)
    bad = bad_pages(vol)
    if bad: report.append(f"pages still unreadable: {bad}")
    print("\n".join(report))
    if write:
        json.dump(q, open(os.path.join(ROOT, "sources", vol, "queue.json"), "w"), ensure_ascii=False, indent=1)
        open(os.path.join(ROOT, "sources", vol, "cut_report.txt"), "w").write("\n".join(report) + "\n")
    return q, report

if __name__ == "__main__":
    a = sys.argv[1:]
    model = MODELS[a[a.index("--model") + 1]] if "--model" in a else MODELS["haiku"]
    if a[0] == "test": cmd_test(a[1], int(a[2]), model)
    elif a[0] == "submit": cmd_submit(a[1], int(a[2]), int(a[3]), model)
    elif a[0] == "collect": cmd_collect()
    elif a[0] == "cut": cmd_cut(a[1], "--dry" not in a)
    elif a[0] == "redo": cmd_redo(a[1], model)
    elif a[0] == "bad": print(a[1], bad_pages(a[1]))
    else: print(__doc__)
