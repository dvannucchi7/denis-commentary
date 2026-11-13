"""Translate queued articles with the Anthropic Message Batches API (half price; results within 24 hours).

Each article is one self-contained request: the rules (tools/batch_prompt.md), the article's OCR text,
the images of its printed pages, its margin references (tools/margins.py), word-for-word matches against
the Vulgate (tools/recheck.py), and the Douay-Rheims + Vulgate text of the chapters it may cover. Every
answer is checked exactly like a translation run's work: shorthand markers expanded against the
Douay-Rheims (tools/expand_quotes.py), tools/check_quotes.py, and tools/recheck.py against the margins.
An answer that fails goes back to the model with its list of problems (up to MAX_ATTEMPTS times); only
answers that pass are published. State (batch ids, raw answers, costs) is kept in $BATCH_DIR
(default /home/claude/batch), outside the repository. The API key is read from $ANTHROPIC_API_KEY or
$BATCH_DIR/api_key.

  python3 tools/batch.py pilot t12 luke-38         one article now, at the normal price, to inspect
  python3 tools/batch.py submit t12 [N]            send the next N (default all) "todo" articles of a queue
  python3 tools/batch.py tick                      collect finished batches, check, publish, send repairs
  python3 tools/batch.py status                    what is where, and what it has cost
  python3 tools/batch.py show luke-38              the request text for one article (no API call)
"""
import base64, contextlib, io, json, os, re, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from check_quotes import ABBR
import check_quotes, margins, recheck

BATCH_DIR = os.environ.get("BATCH_DIR", "/home/claude/batch")
MODEL = "claude-opus-5-5"
MAX_TOKENS = 128000
MAX_ATTEMPTS = 3
EFFORT = os.environ.get("BATCH_EFFORT", "low")        # how much the model thinks: low / medium (default) / high
PRICE = {"in": 2.0, "out": 10.0, "cache_read": 0.10, "cache_write": 2.5}   # batch, $ per million tokens (Opus 5.5)
PRICE_LIVE = {"in": 4.0, "out": 20.0, "cache_read": 0.20, "cache_write": 5.0}
VOLS = {   # per volume: scan PDF here, printed page = PDF page - offset, tome number
    "t11": {"pdf": "/home/claude/scan11/vol.pdf", "offset": 20, "tome": "XI"},
    "t12": {"pdf": "/home/claude/scan12/vol.pdf", "offset": 10, "tome": "XII"},
    "t13": {"pdf": "/home/claude/scans/t13.pdf", "offset": 22, "tome": "XIII"},   # Romans – 2 Peter
    "t6":  {"pdf": "/home/claude/scans/t6.pdf", "offset": 10, "tome": "VI"},      # Psalms
    "t7":  {"pdf": "/home/claude/scans/t7.pdf", "offset": 22, "tome": "VII"},     # Proverbs, Ecclesiastes, Canticle, Wisdom
    "t10": {"pdf": "/home/claude/scans/t10.pdf", "offset": 10, "tome": "X"},      # Daniel, minor prophets
    "t1":  {"pdf": "/home/claude/scans/t1.pdf", "offset": 106, "tome": "I"},      # Genesis (offset to confirm)
}
ORDER = ["t12", "t13", "t6", "t7", "t10", "t1"]      # Dave's order
WORKS = {"matthew": "Enarratio in Evangelium secundum Matthæum", "mark": "Enarratio in Evangelium secundum Marcum",
         "luke": "Enarratio in Evangelium secundum Lucam", "john": "Enarratio in Evangelium secundum Joannem"}
REV = {v: k for k, v in ABBR.items()}
Q = re.compile(r"\[\[([^|\]]+)\|([^|\]]*)\|([^\]]*)\]\]")

# ------------------------------------------------------------------ state
def state():
    p = os.path.join(BATCH_DIR, "state.json")
    return json.load(open(p)) if os.path.exists(p) else {"batches": [], "items": {}, "cost": 0.0}
def save(st):
    os.makedirs(BATCH_DIR, exist_ok=True)
    json.dump(st, open(os.path.join(BATCH_DIR, "state.json") + ".tmp", "w"), indent=1)
    os.replace(os.path.join(BATCH_DIR, "state.json") + ".tmp", os.path.join(BATCH_DIR, "state.json"))
def client():
    import anthropic
    key = os.environ.get("ANTHROPIC_API_KEY") or open(os.path.join(BATCH_DIR, "api_key")).read().strip()
    return anthropic.Anthropic(api_key=key, max_retries=4, timeout=3600)
def git(*a, check=True):
    return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True, check=check).stdout
def queue(vol):
    return json.load(open(os.path.join(ROOT, "sources", vol, "queue.json")))
def item_of(item_id):
    for vol in ORDER:
        if not os.path.exists(os.path.join(ROOT, "sources", vol, "queue.json")): continue
        for it in queue(vol)["items"]:
            if it["id"] == item_id: return vol, it
    raise KeyError(item_id)

# ------------------------------------------------------------------ the request
def page_images(pdf, p):
    """The two columns of a page (each with its outer margin), as JPEGs at most 1568 px tall."""
    import numpy as np
    from PIL import Image
    tmp = os.path.join(BATCH_DIR, f"_p{os.getpid()}")
    subprocess.run(["pdftoppm", "-f", str(p), "-l", str(p), "-r", "200", "-gray", "-png", "-singlefile", pdf, tmp], check=True)
    im = Image.open(tmp + ".png").convert("L"); g = np.array(im); h, w = g.shape
    os.remove(tmp + ".png")
    rows = (g < 128).sum(axis=1); ys = np.where(rows > w * .003)[0]
    if len(ys) == 0: return []
    top, bottom = max(0, ys[0] - 10), min(h, ys[-1] + 10)
    ink = (g[int(h * .08):int(h * .95)] < 128).sum(axis=0).astype(float)
    lo, hi = int(w * .40), int(w * .60); k = max(3, w // 200)
    gx = lo + int(np.argmin(np.convolve(ink, np.ones(k) / k, mode="same")[lo:hi]))
    out = []
    for side, box in (("left", (0, top, gx + 8, bottom)), ("right", (gx - 8, top, w, bottom))):
        c = im.crop(box); s = min(1.0, 1568 / max(c.size))
        if s < 1: c = c.resize((round(c.width * s), round(c.height * s)), Image.LANCZOS)
        b = io.BytesIO(); c.save(b, "JPEG", quality=80)
        out.append((side, base64.b64encode(b.getvalue()).decode()))
    return out

def latin_of(vol, it):
    f = os.path.join(ROOT, "sources", vol, "articles", it["id"] + ".txt")
    if os.path.exists(f): return open(f).read(), True
    parts = []
    for p in range(it["pages"][0], it["pages"][1] + 1):
        pf = os.path.join(ROOT, "sources", vol, "pages", f"p{p}.txt")
        if os.path.exists(pf): parts.append(f"--- PDF {p} ---\n" + open(pf).read())
    return "\n".join(parts), False

def chapter_text(book, c):
    d = json.load(open(os.path.join(ROOT, "data/bible/drc", book + ".json")))
    v = json.load(open(os.path.join(ROOT, "sources/vulgate", book + ".json")))
    if not (1 <= c <= len(d)): return ""
    lines = [f"Chapter {c} ({len(d[c-1])} verses)"]
    for i, (a, b) in enumerate(zip(d[c - 1], v[c - 1]), 1):
        lines.append(f"{c}:{i}  DR: {a}\n      V: {b}")
    return "\n".join(lines)

def user_content(vol, it, with_images=True):
    cfg = VOLS[vol]; book = it["book"]; g = int(it.get("chapter_guess") or 1)
    latin, cut = latin_of(vol, it)
    buf = io.StringIO()
    if os.path.isdir(os.path.join(ROOT, "sources", vol, "margins")):
        with contextlib.redirect_stdout(buf):
            margins.article(vol, it["id"], str(g))
    else:
        buf.write("(none read separately: the transcription gives each margin note in ⟦…⟧ at the line it stands "
                  "beside; check them against the images)")
    obv = recheck.obvious(latin, book, g)
    obv_txt = "\n".join(f"- {('%s %d:%d' % (REV.get(b, b), c, v)) if (b, c) != (book, g) else '%d:%d (chapter treated)' % (c, v)}: '{w} …'"
                        for b, c, v, w in obv[:80]) or "(none)"
    a, b = it["pages"]
    head = (f"Book: {book} (Douay-Rheims name: {REV.get(book, book)}). Article {margins_roman(it['art'])} of the "
            f"{WORKS.get(book, 'commentary')}, in t. {cfg['tome']} of the Opera Omnia. Its text lies on PDF pages "
            f"{a}–{b} = printed pages {a - cfg['offset']}–{b - cfg['offset']} (the first and last may be shared with "
            f"the neighbouring articles). It is thought to treat chapter {g} (from the running heads; check the title; "
            f"it may run on into chapter {g + 1}).")
    blocks = [{"type": "text", "text": head},
              {"type": "text", "text": (("Transcription of the article (made from the page images by another model; "
                                        "margin notes in ⟦…⟧, italics as _…_), already cut at its heading:\n\n"
                                        if it.get("source") == "transcribed" else
                                        "OCR text of the article, already cut at its heading:\n\n") if cut else
                                        "OCR pages (the article is not yet cut out: find its heading):\n\n") + latin},
              {"type": "text", "text": "References read from the printed margins by a program, in reading order "
                                       "(check each against the images and the verse text):\n\n" + buf.getvalue()},
              {"type": "text", "text": "Word-for-word matches of the OCR text against the Vulgate (6+ words from "
                                       "other books, 4+ from the chapter treated; candidates only):\n" + obv_txt},
              {"type": "text", "text": "\n\n".join(t for t in (chapter_text(book, c) for c in (g - 1, g, g + 1)) if t)}]
    if with_images:
        for p in range(a, b + 1):
            for side, data in page_images(cfg["pdf"], p):
                blocks.append({"type": "text", "text": f"Page image: PDF {p} (printed p. {p - cfg['offset']}), {side} column:"})
                blocks.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}})
    blocks.append({"type": "text", "text": "Translate the article as instructed, and end with the JSON."})
    return blocks

def margins_roman(n): return recheck.roman(int(n))

def system_prompt():
    t = open(os.path.join(ROOT, "tools", "batch_prompt.md")).read()
    return t.replace("ABBREVIATIONS", ", ".join(f"{k} ({v})" for k, v in ABBR.items()))

def params(vol, it, messages=None):
    extra = {"output_config": {"effort": EFFORT}} if EFFORT != "medium" else {}
    return {"model": MODEL, "max_tokens": MAX_TOKENS, **extra,
            "system": [{"type": "text", "text": system_prompt(), "cache_control": {"type": "ephemeral"}}],
            "messages": messages or [{"role": "user", "content": user_content(vol, it)}]}

# ------------------------------------------------------------------ checking and publishing an answer
def answer_json(text):
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.S)
    raw = blocks[-1] if blocks else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(raw)

def apply_changes(prev, new):
    """A repair answer may give only the changed paragraphs: {"changes": [{"i": 3, "para": {...}}, ...]}."""
    if "paras" in new: return new
    out = json.loads(json.dumps(prev))
    for c in sorted(new.get("changes", []), key=lambda c: -c.get("i", 0)):
        i = c["i"]
        if c.get("delete"): out["paras"].pop(i)
        elif c.get("insert"): out["paras"].insert(i, c["para"])
        else: out["paras"][i] = c["para"]
    for k in ("num", "title", "title_en", "pages", "unreadable", "note"):
        if k in new: out[k] = new[k]
    return out

def publish_try(vol, it, ans):
    """Merge the answer into the data, run the checks. Returns (problems, soft_report). Leaves the merge in
    place only if there are no hard problems."""
    book = it["book"]; hard = []
    for k in ("num", "title", "title_en", "paras"):
        if k not in ans: hard.append(f"the JSON has no '{k}'")
    if hard: return hard, ""
    data_path = os.path.join(ROOT, "data", "commentary", book + ".json")
    meta = json.load(open(data_path)) if os.path.exists(data_path) else {}
    work = meta.get("work") or WORKS.get(book, "Enarratio")
    source = meta.get("source") or f"Dionysii Cartusiani Opera Omnia, t. {VOLS[vol]['tome']} (Montreuil)"
    bych = {}
    for i, p in enumerate(ans["paras"]):
        if not isinstance(p.get("v"), list) or len(p["v"]) != 2 or not p.get("t") or not p.get("en"):
            hard.append(f"paragraph {i}: needs ch, v [first, last], t and en"); continue
        bych.setdefault(int(p.get("ch") or it.get("chapter_guess") or 1), []).append(
            {k: p[k] for k in ("v", "t", "en", "gap_ok") if k in p})
    if hard: return hard, ""
    os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
    note = ans.get("note") or ""
    files = []
    for ch, paras in sorted(bych.items()):
        wf = os.path.join(ROOT, "work", f"{it['id']}-ch{ch}.json")
        art = dict(book=book, chapter=ch, work=work, source=source, num=ans["num"], title=ans["title"],
                   title_en=ans["title_en"], pages=ans.get("pages", ""), paras=paras)
        if note: art["note"] = note
        json.dump(art, open(wf, "w"), ensure_ascii=False, indent=1); files.append((ch, wf))
    for ch, wf in files:
        r = subprocess.run(["python3", os.path.join(ROOT, "tools", "add_article.py"), wf], capture_output=True, text=True)
        if r.returncode:
            hard.append(f"chapter {ch}: quotation markers that could not be filled in from the Douay-Rheims "
                        f"(the anchors must be the verse's own words, in order, and unambiguous):\n" + (r.stdout + r.stderr).strip())
    if not hard:
        n, probs = check_quotes.check(book)
        mine = [p for p in probs if any(f"{book} {ch}, Art. {ans['num']} " in p for ch in bych)]
        hard += mine
    if not hard and it.get("source") == "transcribed":
        hard += coverage(vol, it, ans)
    soft = ""
    if not hard and os.path.isdir(os.path.join(ROOT, "sources", vol, "margins")):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try: recheck.main(vol, it["id"])
            except SystemExit as e: print(e)
        soft = buf.getvalue()
    for _, wf in files:
        if os.path.exists(wf): os.remove(wf)
    if hard:
        git("checkout", "--", "data/commentary", "index.html", check=False)
        if not os.path.exists(data_path) or not git("ls-files", data_path).strip():
            if os.path.exists(data_path) and not git("ls-files", data_path).strip(): os.remove(data_path)
    return hard, soft

def _letters(s):
    """Letters only (no spaces, hyphens, line breaks, margin notes, italics marks), æ/œ, j/v normalized."""
    s = re.sub(r"⟦[^⟧]*⟧|^###.*$|^HEAD:.*$|^===.*$", " ", s, flags=re.M).lower()
    s = s.replace("æ", "ae").replace("œ", "oe").replace("j", "i").replace("v", "u")
    return re.sub(r"[^a-z]", "", s)

def coverage(vol, it, ans, n=30):
    """Every stretch of the transcription must be in the translator's Latin (it catches dropped or altered
    passages; hyphenation, line breaks and spacing do not matter). Returns problems, or []."""
    raw = open(os.path.join(ROOT, "sources", vol, "articles", it["id"] + ".txt")).read()
    src, mine = _letters(raw), _letters(" ".join(p.get("t", "") for p in ans["paras"]))
    have = {mine[i:i + n] for i in range(len(mine) - n + 1)}
    probe = list(range(0, max(0, len(src) - n + 1), 10))
    miss = [i for i in probe if src[i:i + n] not in have]
    if len(miss) <= max(2, 0.03 * len(probe)): return []
    # show the missing stretches as words, from the transcription
    words = re.findall(r"\S+", re.sub(r"⟦[^⟧]*⟧", " ", raw)); spans = []
    pos, acc = [], 0
    for w in words: pos.append(acc); acc += len(_letters(w))
    for i in miss:
        k = max(0, min(range(len(pos)), key=lambda j: abs(pos[j] - i)))
        sp = " ".join(words[max(0, k - 2):k + 10])
        if not spans or sp[:20] not in spans[-1]: spans.append(sp)
    return ["your Latin does not contain these passages of the transcription (dropped, or changed beyond "
            "OCR-level corrections); restore them from the images unless the transcription is wrong there:\n"
            + "\n".join(f"- …{sp[:200]}…" for sp in spans[:12])]

def soft_count(report):
    m = re.search(r"summary: (.*)", report)
    if not m: return 0
    c = dict((k, int(v)) for k, v in re.findall(r"([a-z?\-]+) (\d+)", m.group(1)))
    return sum(c.get(k, 0) for k in ("untagged", "differs", "obvious", "lemma?"))

def usage_cost(u, live=False):
    pr = PRICE_LIVE if live else PRICE
    g = lambda k: (u.get(k) or 0)
    return (g("input_tokens") * pr["in"] + g("output_tokens") * pr["out"] + g("cache_read_input_tokens") * pr["cache_read"]
            + g("cache_creation_input_tokens") * pr["cache_write"]) / 1e6

def handle(st, item_id, text, usage, live=False):
    """Check one answer. Returns 'published', 'repair' or 'failed'."""
    vol, it = item_of(item_id)
    rec = st["items"].setdefault(item_id, {"vol": vol, "attempts": 0})
    rec["attempts"] += 1; rec["cost"] = rec.get("cost", 0) + usage_cost(usage, live); st["cost"] += usage_cost(usage, live)
    os.makedirs(os.path.join(BATCH_DIR, "answers"), exist_ok=True)
    open(os.path.join(BATCH_DIR, "answers", f"{item_id}.{rec['attempts']}.txt"), "w").write(text)
    try:
        new = answer_json(text)
        ans = apply_changes(rec["answer"], new) if rec.get("answer") and "paras" not in new else new
    except Exception as e:
        hard, soft, ans = [f"the answer's JSON could not be read ({e}); it may have been cut off"], "", rec.get("answer")
    else:
        hard, soft = publish_try(vol, it, ans)
    rec["answer"] = ans
    sc = soft_count(soft)
    if not hard and (sc == 0 or rec["attempts"] >= 2):
        q = queue(vol)
        for x in q["items"]:
            if x["id"] == item_id:
                unread = [u for u in (ans.get("unreadable") or []) if u and u.strip()]
                x["status"] = "needs-scan" if unread else "done"
                notes = [f"translated by batch ({rec['attempts']} attempt(s), ${rec['cost']:.2f})"]
                if unread: notes.append("unreadable: " + "; ".join(unread))
                if sc: notes.append(f"recheck leftovers: {re.search(r'summary: (.*)', soft).group(1)}")
                x["note"] = " | ".join(notes); x.pop("claimed", None)
        json.dump(q, open(os.path.join(ROOT, "sources", vol, "queue.json"), "w"), ensure_ascii=False, indent=1)
        chs = sorted({int(p.get("ch") or it.get("chapter_guess")) for p in ans["paras"]})
        git("add", "-A", "data/commentary", "index.html", f"sources/{vol}/queue.json")
        msg = f"Add {it['book'].title()} {'/'.join(map(str, chs))}, Art. {ans['num']} (batch)"
        git("commit", "-q", "-m", msg + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
            "Claude-Session: https://claude.ai/code/session_01P42bsAZ8MRwT4QtVUC2W2R", check=False)
        rec["status"] = "published"; rec["published"] = msg
        return "published"
    rec["problems"] = hard if hard else [f"tools/recheck.py still reports these against the printed margins:\n{soft}"]
    rec["status"] = "repair" if rec["attempts"] < MAX_ATTEMPTS else "failed"
    return rec["status"]

def repair_messages(vol, it, rec):
    prev = json.dumps(rec.get("answer"), ensure_ascii=False) if rec.get("answer") else "(unreadable answer)"
    probs = "\n\n".join(rec["problems"])
    return [{"role": "user", "content": user_content(vol, it)},
            {"role": "assistant", "content": [{"type": "text", "text": "```json\n" + prev + "\n```"}]},
            {"role": "user", "content": [{"type": "text", "text":
                "The automatic checks found these problems in your answer:\n\n" + probs + "\n\n"
                "Fix them. For `recheck` lines: tag what is a real quotation or margin reference (or add a "
                "reference-only marker), and leave what you judge deliberate (say why in a bracketed note only "
                "if a reader needs it). Answer with JSON in a ```json block: either the whole article again, "
                "or only the paragraphs that change, as {\"changes\": [{\"i\": <index from 0>, \"para\": {…the full "
                "corrected paragraph…}}]} (add \"insert\": true to insert a new paragraph at that index, or "
                "\"delete\": true to remove one). Keep everything else exactly as it was."}]}]

# ------------------------------------------------------------------ commands
def cmd_show(item_id):
    vol, it = item_of(item_id)
    for b in user_content(vol, it, with_images=False): print(b.get("text", "[image]"), "\n")
    imgs = sum(len(page_images(VOLS[vol]["pdf"], p)) for p in range(it["pages"][0], it["pages"][1] + 1))
    print(f"[{imgs} page images]")

def cmd_pilot(vol, item_id):
    st = state(); c = client(); _, it = item_of(item_id)
    text, usage = "", {}
    with c.messages.stream(**params(vol, it)) as s:
        for ev in s: pass
        m = s.get_final_message()
    text = "".join(b.text for b in m.content if b.type == "text"); usage = m.usage.model_dump()
    res = handle(st, item_id, text, usage, live=True); save(st)
    print(f"{item_id}: {res}; cost ${usage_cost(usage, True):.2f} (normal price; in a batch about half)",
          json.dumps({k: usage.get(k) for k in ('input_tokens', 'output_tokens', 'cache_read_input_tokens')}))
    if res != "published": print("\n".join(st["items"][item_id]["problems"])[:3000])

def submit(st, reqs, kind):
    c = client(); ids = []
    for i in range(0, len(reqs), 20):            # keep each batch well under the 256 MB limit
        chunk = reqs[i:i + 20]
        b = c.messages.batches.create(requests=chunk)
        st["batches"].append({"id": b.id, "kind": kind, "items": [r["custom_id"] for r in chunk],
                              "submitted": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "open": True})
        ids.append(b.id); save(st)
    return ids

def cmd_submit(vol, n=None):
    st = state(); q = queue(vol); reqs = []
    busy = {i for b in st["batches"] if b["open"] for i in b["items"]}
    todo = [it for it in q["items"] if it["status"] == "todo" and it["id"] not in busy]
    for it in todo[: n or len(todo)]:
        rec = st["items"].get(it["id"], {})
        if rec.get("status") == "repair" and rec.get("answer"):      # already answered once: send the repair
            reqs.append({"custom_id": it["id"], "params": params(vol, it, repair_messages(vol, it, rec))})
        else:
            reqs.append({"custom_id": it["id"], "params": params(vol, it)})
        it["status"] = "batch"; it["claimed"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        print("prepared", it["id"], flush=True)
    if not reqs: return print("nothing to send")
    ids = submit(st, reqs, "translate")
    json.dump(q, open(os.path.join(ROOT, "sources", vol, "queue.json"), "w"), ensure_ascii=False, indent=1)
    git("add", f"sources/{vol}/queue.json")
    git("commit", "-q", "-m", f"Batch: {len(reqs)} articles of {vol} sent ({', '.join(ids)})\n\n"
        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01P42bsAZ8MRwT4QtVUC2W2R", check=False)
    push(); print(f"sent {len(reqs)} articles in batch(es) {', '.join(ids)}")

def push():
    git("pull", "-q", "--rebase", "origin", "main", check=False); git("push", "-q", "origin", "main", check=False)

def cmd_tick():
    st = state(); c = client(); done, repairs = [], []
    for b in [b for b in st["batches"] if b["open"]]:
        info = c.messages.batches.retrieve(b["id"])
        if info.processing_status != "ended":
            print(f"batch {b['id']} ({b['kind']}, {len(b['items'])}): {info.processing_status} "
                  f"{info.request_counts.model_dump()}"); continue
        git("pull", "-q", "--rebase", "origin", "main", check=False)
        for r in c.messages.batches.results(b["id"]):
            if r.result.type != "succeeded":
                rec = st["items"].setdefault(r.custom_id, {"vol": item_of(r.custom_id)[0], "attempts": 0})
                rec["problems"] = [f"the request {r.result.type}"]; rec["status"] = "retry"; repairs.append(r.custom_id); continue
            m = r.result.message
            text = "".join(x.text for x in m.content if x.type == "text")
            res = handle(st, r.custom_id, text, m.usage.model_dump())
            (done if res == "published" else repairs if res == "repair" else []).append(r.custom_id)
            print(f"  {r.custom_id}: {res}", flush=True); save(st)
        b["open"] = False; save(st); push()
    if repairs:
        reqs = []
        for i in repairs:
            vol, it = item_of(i); rec = st["items"][i]
            msgs = None if rec.get("status") == "retry" or not rec.get("answer") else repair_messages(vol, it, rec)
            reqs.append({"custom_id": i, "params": params(vol, it, msgs)})
        print("sending repairs:", ", ".join(repairs)); submit(st, reqs, "repair")
    save(st)
    for i in done: print("published:", st["items"][i]["published"])
    print(f"spent so far: ${st['cost']:.2f}")

def cmd_status():
    st = state()
    for b in st["batches"]: print(b["id"], b["kind"], len(b["items"]), "open" if b["open"] else "done", b["submitted"])
    from collections import Counter
    print(Counter(r.get("status") for r in st["items"].values()))
    for i, r in st["items"].items():
        if r.get("status") == "failed": print("FAILED", i, r["problems"][:1])
    print(f"spent so far: ${st['cost']:.2f}")

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    {"show": lambda: cmd_show(a[1]), "pilot": lambda: cmd_pilot(a[1], a[2]),
     "submit": lambda: cmd_submit(a[1], int(a[2]) if len(a) > 2 else None),
     "tick": cmd_tick, "status": cmd_status}[a[0]]()
