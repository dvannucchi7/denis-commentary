#!/usr/bin/env python3
"""Cut an OCR'd volume (local Tesseract, sources/<vol>/pages) into articles and a queue (Dave, 24 Nov 2026).

  python3 tools/cut_ocr.py <vol> [--force]

Builds a reading view of the OCR pages (running head from the scan's text layer, the column text, article
and chapter headings marked), then cuts it with the same cutter as the API transcriptions
(tools/transcribe.py cut): articles go to sources/<vol>/articles/, the queue to sources/<vol>/queue.json
with "source": "ocr" (margins in sources/<vol>/margins/, read by tools/margins.py). Items already claimed
or done keep their status. Each item gets "order" (Dave's order of translation, below), which
tools/queue.py follows across volumes. Refuses while pages planned for the volume are still missing
(/home/claude/ocr/plan.txt), unless --force.
"""
import json, os, re, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import map_volume, transcribe

# Dave, 24 Nov 2026: Job, Macc, Isaiah, Jeremiah, Exodus, Joshua, Kings, Apocalypse; each file's other
# books after its named one
SEQ = [("t4", ["job"]),
       ("t5", ["job", "i-maccabees", "ii-maccabees", "tobit", "judith", "esther", "ezra", "nehemiah", "psalms"]),
       ("t8", ["isaiah", "sirach"]),
       ("t9", ["jeremiah", "lamentations", "baruch", "ezekiel"]),
       ("t2", ["exodus", "leviticus", "numbers", "deuteronomy"]),
       ("t3", ["joshua", "judges", "ruth", "i-samuel", "ii-samuel", "i-kings"]),
       ("t4", ["ii-kings", "i-chronicles", "ii-chronicles"]),
       ("t14", ["revelation-of-john", "acts", "i-john", "ii-john", "iii-john", "jude"])]
PDF = "/home/claude/scans/{}.pdf"
HEADING = re.compile(r"^\s*[A-Z]{0,2}RT[I1l][CG][UV]?L?[UV]?S?\s+([IVXLCl1]+|PRIMUS)\b\.?")
SECTION = re.compile(r"^\s*(EXPOSITIO|EXPLANATIO|ELUCIDATIO|ENARRATIO|DECLARATIO|COMMENTARI\w*|PRO[OŒ]E?MIUM|PROLOGUS|PR[ÆA]FATIO)\b")

def order(vol, book, k):
    for n, (v, books) in enumerate(SEQ):
        if v == vol and book in books: return (n * 100 + books.index(book)) * 1000 + k
    last = max(n for n, (v, _) in enumerate(SEQ) if v == vol) if any(v == vol for v, _ in SEQ) else len(SEQ)
    return (last * 100 + 99) * 1000 + k

def view(vol, out):
    d = os.path.join(ROOT, "sources", vol, "pages")
    for f in sorted((f for f in os.listdir(d) if re.fullmatch(r"p\d+\.txt", f)), key=lambda f: int(f[1:-4])):
        p = int(f[1:-4]); lines = []
        for l in open(os.path.join(d, f)).read().splitlines():
            if l.startswith("====="): lines.append("=== " + l.strip("= ") + " ==="); continue
            m = HEADING.match(l)
            if m:
                n = m.group(1).replace("1", "I").replace("l", "I")
                lines.append(f"### ARTICULUS {n}"); continue
            letters = [c for c in l if c.isalpha()]
            if SECTION.match(l) and letters and sum(c.isupper() for c in letters) / len(letters) > .7:
                lines.append("### " + l.strip()); continue
            lines.append(l)
        head = map_volume.head(PDF.format(vol), p).strip()
        open(os.path.join(out, f), "w").write("HEAD: " + head + "\n" + "\n".join(lines) + "\n")

def main(vol, force=False):
    plan = [l.split() for l in open("/home/claude/ocr/plan.txt") if l.strip()]
    missing = [(v, p) for v, a, b in plan if v == vol for p in range(int(a), int(b) + 1)
               if not os.path.exists(os.path.join(ROOT, "sources", vol, "pages", f"p{p}.txt"))]
    if missing and not force: sys.exit(f"{vol}: {len(missing)} planned pages not OCR'd yet (first: PDF {missing[0][1]})")
    with tempfile.TemporaryDirectory() as tmp:
        view(vol, tmp)
        q, report = transcribe.cmd_cut(vol, True, src=tmp, label="ocr")
    qp = os.path.join(ROOT, "sources", vol, "queue.json"); q = json.load(open(qp))
    for k, it in enumerate(q["items"]): it["order"] = order(vol, it["book"], k)
    json.dump(q, open(qp, "w"), ensure_ascii=False, indent=1)
    print(f"{vol}: {len(q['items'])} items queued")

if __name__ == "__main__":
    main(sys.argv[1], "--force" in sys.argv)
