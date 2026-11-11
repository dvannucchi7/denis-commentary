"""OCR two-column pages of the Montreuil Opera Omnia, one column at a time.

usage: python3 ocr_columns.py vol.pdf FIRST LAST OUTDIR
Writes OUTDIR/p<pdfpage>.txt (left column, then right column) and the column images.
"""
import sys, os, subprocess
import numpy as np
from PIL import Image

pdf, first, last, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
os.makedirs(out, exist_ok=True)
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

for p in range(first, last + 1):
    base = os.path.join(out, f"p{p}")
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
    texts = []
    for i, c in enumerate(cols):
        cp = f"{base}_{'LR'[i]}.png"
        c.save(cp)
        r = subprocess.run(["tesseract", cp, "-", "-l", "lat", "--psm", "4"], capture_output=True, text=True, env=env)
        texts.append(r.stdout)
    with open(base + ".txt", "w") as f:
        f.write("=====LEFT=====\n" + texts[0] + "\n=====RIGHT=====\n" + texts[1])
    print(p, "gutter at", gx, "of", w, "text rows", top, bottom)
