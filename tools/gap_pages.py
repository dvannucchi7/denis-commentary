#!/usr/bin/env python3
"""Gaps in a volume's transcription, ready to be read from the page images (Dave, 24 Nov 2026).

The transcriber writes […] where it could not read; a stronger model reading the column images fills most
of them (tested: 7 of 10 with high confidence). Do this before a volume is cut into articles and queued, so
no article is translated twice. Needs the scan PDF, so it runs where the scans are, not in scheduled runs.

  python3 tools/gap_pages.py <vol> OUTDIR [first last]

writes OUTDIR/gaps.txt (one line per gap: page, column, the line before, the gap line, the line after) and
OUTDIR/<vol>-p<N>-L.jpg / -R.jpg (each column with its margin) for every page with a gap. Give both to a
worker: for each gap, the printed words (with confidence), or "not on this page" / "print damaged"; it must
not guess. Then put each filled reading in place of its […] in sources/<vol>/transcribed/p<N>.txt (leave
the ones it could not read), and only then run `tools/transcribe.py cut <vol>`.
"""
import base64, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import batch

def main(vol, out, first=None, last=None):
    os.makedirs(out, exist_ok=True)
    d = os.path.join(ROOT, "sources", vol, "transcribed")
    pages = sorted(int(f[1:-4]) for f in os.listdir(d) if f.startswith("p"))
    if first: pages = [p for p in pages if int(first) <= p <= int(last)]
    lines, n = [], 0
    for p in pages:
        t = open(os.path.join(d, f"p{p}.txt")).read().splitlines()
        if not any("[…]" in l for l in t): continue
        col = "?"
        for k, l in enumerate(t):
            if l.startswith("=== LEFT"): col = "L"
            if l.startswith("=== RIGHT"): col = "R"
            if "[…]" in l:
                n += 1
                lines.append(f"{n}. p{p} column {col}: «{t[k - 1][-90:] if k else ''}» / «{l[:300]}» / «{t[k + 1][:90] if k + 1 < len(t) else ''}»")
        for side, (_, data) in zip("LR", batch.page_images(batch.VOLS[vol]["pdf"], p)):
            open(os.path.join(out, f"{vol}-p{p}-{side}.jpg"), "wb").write(base64.b64decode(data))
    open(os.path.join(out, "gaps.txt"), "w").write("\n".join(lines) + "\n")
    print(f"{n} gaps on {len({l.split()[1] for l in lines})} pages; images and gaps.txt in {out}")

if __name__ == "__main__":
    main(*sys.argv[1:])
