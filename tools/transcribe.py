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
    return {"model": model, "max_tokens": 12000, "messages": [{"role": "user", "content": content}]}

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

def cmd_cut(vol):
    """Cut articles at their ### ARTICULUS headings; book and chapter from the running heads."""
    import map_volume
    d = os.path.join(ROOT, "sources", vol, "transcribed")
    pages = sorted(int(f[1:-4]) for f in os.listdir(d) if f.startswith("p"))
    seq = []          # (page, kind, text)
    for p in pages:
        t = open(os.path.join(d, f"p{p}.txt")).read()
        hm = re.search(r"^HEAD:(.*)$", t, re.M)
        seq.append((p, "head", hm.group(1).strip() if hm else ""))
        for line in t.splitlines():
            if line.startswith("HEAD:") or line.startswith("==="): continue
            seq.append((p, "line", line))
    arts, cur = [], None
    for p, kind, text in seq:
        if kind == "head":
            r = map_volume.parse(text.upper().replace("Æ", "AE").replace("Œ", "OE"))
            if r and cur is not None and r[2] == cur["art"]:
                cur["book"] = cur["book"] or r[0]; cur["chapter_guess"] = cur["chapter_guess"] or r[1]
            continue
        m = re.match(r"^###\s*ARTICULUS\s+([IVXLC]+|PRIMUS)\b(.*)", text.strip(), re.I)
        if m:
            n = 1 if m.group(1).upper() == "PRIMUS" else roman(m.group(1))
            cur = {"art": n, "first": p, "lines": [text.lstrip("# ")], "book": None, "chapter_guess": None}
            arts.append(cur); continue
        if cur is not None: cur["lines"].append(text); cur["last"] = p
    # books: a head naming the book after the article started; carry forward when missing
    book = None
    for a in arts:
        book = a["book"] = a["book"] or book
    q = {"volume": vol, "items": []}
    os.makedirs(os.path.join(ROOT, "sources", vol, "articles"), exist_ok=True)
    seen = {}
    for a in arts:
        if not a["book"]: continue
        k = seen[a["book"], a["art"]] = seen.get((a["book"], a["art"]), 0) + 1
        iid = f"{a['book']}-{a['art']:03d}" + (f"-{k}" if k > 1 else "")      # psalm volumes can restart numbering
        open(os.path.join(ROOT, "sources", vol, "articles", iid + ".txt"), "w").write("\n".join(a["lines"]))
        q["items"].append({"id": iid, "book": a["book"], "art": a["art"], "chapter_guess": a["chapter_guess"],
                           "pages": [a["first"], a.get("last", a["first"])], "status": "todo", "source": "transcribed"})
    json.dump(q, open(os.path.join(ROOT, "sources", vol, "queue.json"), "w"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(vol, len(q["items"]), "articles:", dict(Counter(i["book"] for i in q["items"])))

if __name__ == "__main__":
    a = sys.argv[1:]
    model = MODELS[a[a.index("--model") + 1]] if "--model" in a else MODELS["haiku"]
    if a[0] == "test": cmd_test(a[1], int(a[2]), model)
    elif a[0] == "submit": cmd_submit(a[1], int(a[2]), int(a[3]), model)
    elif a[0] == "collect": cmd_collect()
    elif a[0] == "cut": cmd_cut(a[1])
    else: print(__doc__)
