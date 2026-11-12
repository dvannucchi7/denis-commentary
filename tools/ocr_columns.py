"""OCR two-column pages of the Montreuil Opera Omnia, one column at a time, and read their margins.

usage: python3 tools/ocr_columns.py vol.pdf FIRST LAST sources/<vol>/pages [--no-margins]
Writes OUTDIR/p<pdfpage>.txt (left column, then right column) and the column images.

The column text leaves out the outer margins, where the printed edition gives its scripture references.
Those are read in the same run (tools/margins.py read) into sources/<vol>/margins/p<pdfpage>.json, which
the translation runs need: an article whose margins are not read cannot be translated. Pages whose
margins are already read are skipped. The volume is taken from OUTDIR (sources/<vol>/pages); give
--vol <vol> if OUTDIR is elsewhere, or --no-margins to skip this step.
"""
import sys, os, re, subprocess
import numpy as np
from PIL import Image

args = [a for a in sys.argv[1:]]
no_margins = "--no-margins" in args
if no_margins: args.remove("--no-margins")
vol = None
if "--vol" in args:
    i = args.index("--vol"); vol = args[i + 1]; del args[i:i + 2]
pdf, first, last, outdir = args[0], int(args[1]), int(args[2]), args[3]
os.makedirs(outdir, exist_ok=True)
if not vol:
    m = re.search(r"sources/([^/]+)/pages/?$", os.path.abspath(outdir))
    vol = m.group(1) if m else None
if not no_margins and not vol:
    sys.exit("give --vol <vol> (or write into sources/<vol>/pages), so the margins can be read too; or --no-margins")
# Needs the Latin model: tessdata_best lat.traineddata (github.com/tesseract-ocr/tessdata_best).
env = dict(os.environ, TESSDATA_PREFIX=os.environ.get("TESSDATA_PREFIX", "/home/claude/tessdata"))

def find_gutter(gray):
    """x of the blank vertical band between the columns (search the middle 40-60% of the width)."""
    h, w = gray.shape
    body = gray[int(h * .08):int(h * .95)] < 128          # ink pixels in the text body
    ink = body.sum(axis=0).astype(float)
    lo, hi = int(w * .40), int(w * .60)
    k = max(3, w // 200)                                   # smooth over a few pixels
    sm = np.convolve(ink, np.ones(k) / k, mode="same")
    return lo + int(np.argmin(sm[lo:hi]))

def text_box(gray):
    """top/bottom of the text body: skip the running head (first inked band) and the gap after it."""
    h, w = gray.shape
    rows = (gray < 128).sum(axis=1)
    inked = rows > w * .003
    ys = np.where(inked)[0]
    top, bottom = ys[0], ys[-1]
    y = top
    while y < h and inked[y]: y += 1                      # end of the running-head line
    blank = 0
    while y < h and not inked[y]: y += 1; blank += 1      # the gap after it
    if blank > h * .006 and y < h * .2:                    # a real running head: text starts here
        top = y
    return max(0, top - 6), bottom

def heading_rows(g, top, bottom, gx, la, rb):
    """Rows (y0, y1) of full-width headings: text that runs across the gutter (an article heading
    in the middle of a page). The gutter letters A-D are single small marks and are ignored."""
    h, w = g.shape
    mid = g[:, gx - w // 12: gx + w // 12] < 128        # a band either side of the gutter
    gut = g[:, gx - w // 120: gx + w // 120] < 128       # the gutter itself
    edge = int(w * .07)
    left_edge = g[:, la: la + edge] < 128                 # ordinary lines always reach the outer edges;
    right_edge = g[:, rb - edge: rb] < 128                # a centred heading leaves both blank
    rows = [y for y in range(top, bottom)
            if gut[y].any() and mid[y].sum() > w * .02 and not left_edge[y].any() and not right_edge[y].any()]
    blocks, start, prev = [], None, None
    for y in rows:
        if start is None: start = prev = y; continue
        if y - prev > h * .012: blocks.append((start, prev)); start = y
        prev = y
    if start is not None: blocks.append((start, prev))
    # a heading block is a few lines tall; merge blocks that are close (title of two lines)
    merged = []
    for b in blocks:
        if merged and b[0] - merged[-1][1] < h * .03: merged[-1] = (merged[-1][0], b[1])
        else: merged.append(b)
    return [(max(top, a - 12), min(bottom, b + 12)) for a, b in merged if b - a > h * .006]

for p in range(first, last + 1):
    base = os.path.join(outdir, f"p{p}")
    subprocess.run(["pdftoppm", "-f", str(p), "-l", str(p), "-r", "300", "-gray", "-png", "-singlefile", pdf, base], check=True)
    im = Image.open(base + ".png").convert("L")
    g = np.array(im)
    top, bottom = text_box(g)
    gx = find_gutter(g)
    h, w = g.shape
    band = int(w * .018)                                   # gutter letters A-D live here: cut them out
    def outer_edge(x0, x1, from_left):
        """trim only the outer margin (where marginal references sit), never the gutter side."""
        ink = (g[top:bottom, x0:x1] < 128).sum(axis=0).astype(float)
        k = max(5, w // 150); sm = np.convolve(ink, np.ones(k) / k, mode="same")
        dense = np.where(sm > sm.max() * .30)[0]
        return x0 + max(0, dense[0] - 10) if from_left else x0 + min(x1 - x0, dense[-1] + 10)
    la = outer_edge(0, gx - band, True)
    rb = outer_edge(gx + band, w, False)
    cols = [im.crop((la, top, gx - band // 3, bottom + 5)), im.crop((gx + band // 3, top, rb, bottom + 5))]
    def ocr(img, tag, psm="4"):
        cp = f"{base}_{tag}.png"; img.save(cp)
        return subprocess.run(["tesseract", cp, "-", "-l", "lat", "--psm", psm], capture_output=True, text=True, env=env).stdout
    # split the page into bands at any full-width heading: columns above, the heading, columns below
    cuts = heading_rows(g, top, bottom, gx, la, rb)
    bands, y = [], top
    for a_, b_ in cuts:
        if a_ - y > 20: bands.append(("cols", y, a_))
        bands.append(("head", a_, b_)); y = b_
    if bottom - y > 20: bands.append(("cols", y, bottom + 5))
    parts = []
    for k, (kind, y0, y1) in enumerate(bands):
        if kind == "head":
            t = ocr(im.crop((la, y0, rb, y1)), f"H{k}", "6")
            letters = [c for c in t if c.isalpha()]
            lower_words = re.findall(r"[a-zæœ]{3,}", t)
            if len(lower_words) >= 4 and sum(c.isupper() for c in letters) < .6 * len(letters):
                # not a heading after all: ordinary lines of both columns side by side; read them as columns
                parts.append("=====LEFT=====\n" + ocr(im.crop((la, y0, gx - band // 3, y1)), f"L{k}"))
                parts.append("=====RIGHT=====\n" + ocr(im.crop((gx + band // 3, y0, rb, y1)), f"R{k}"))
            else:
                parts.append("=====HEADING=====\n" + t)
        else:
            parts.append("=====LEFT=====\n" + ocr(im.crop((la, y0, gx - band // 3, y1)), f"L{k}"))
            parts.append("=====RIGHT=====\n" + ocr(im.crop((gx + band // 3, y0, rb, y1)), f"R{k}"))
    with open(base + ".txt", "w") as f:
        f.write("\n".join(parts))
    print(p, "gutter at", gx, "of", w, "text rows", top, bottom)

# the outer margins (scripture references), into sources/<vol>/margins/
if not no_margins:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import margins
    print("reading the margins of PDF", first, "to", last, "into sources/%s/margins" % vol, flush=True)
    margins.read(vol, pdf, first, last)
