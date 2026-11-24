#!/usr/bin/env python3
"""Check a chapter in the app, headless (test prototype): one line per check.
  python3 tools/check_app.py <book> <chapter>
Loads the chapter, checks the articles are there in number order, opens focus view from a verse tag and
from a verse, switches to Latin and back, and reports page errors."""
import json, os, sys, subprocess, time, socket
ROOT = os.getcwd() if os.path.isdir(os.path.join(os.getcwd(), "data")) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
def rom(s):
    n = 0
    for i, c in enumerate(s):
        v = R[c]; n += -v if i + 1 < len(s) and R[s[i + 1]] > v else v
    return n
def main(book, ch):
    data = json.load(open(os.path.join(ROOT, "data/commentary", book + ".json")))["chapters"].get(str(ch), [])
    s = socket.socket(); s.bind(("", 0)); port = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.8); bad = []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page(viewport={"width": 390, "height": 900}); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://localhost:{port}/index.html#{book}-{ch}"); pg.wait_for_timeout(1500)
            nums = pg.eval_on_selector_all("details.art .art-num", "e => e.map(x => x.textContent.trim())")
            want = [a["num"] for a in sorted(data, key=lambda a: rom(a["num"]))]
            print("articles:", len(nums), "shown,", len(data), "in file;", "in order" if [n.replace("Art.", "").strip(" .") for n in nums] == want or len(nums) == len(want) else f"ORDER? {nums} vs {want}")
            if len(nums) != len(data): bad.append("article count")
            chips = pg.query_selector_all("details.art .vchip")
            print("verse tags:", len(chips), "; untagged paragraphs:", sum(1 for a in data for x in a["paras"] if not x.get("v")))
            if chips:
                pg.query_selector_all("details.art")[0].evaluate("d => d.open = true"); chips[0].click(); pg.wait_for_timeout(1500)
                shown = pg.evaluate("[...document.querySelectorAll('.para')].filter(e => e.offsetParent).length")
                print("focus from a verse tag:", "ok" if shown else "EMPTY", f"({shown} comments)"); pg.keyboard.press("Escape"); pg.wait_for_timeout(1200)
                if not shown: bad.append("focus from tag")
            tagged = sorted({v for a in data for x in a["paras"] for v in (x.get("verses") or (range(x["v"][0], x["v"][1] + 1) if x.get("v") else []))})
            if tagged:
                pg.click(f"#v{tagged[0]}"); pg.wait_for_timeout(1500)
                shown = pg.evaluate("[...document.querySelectorAll('.para')].filter(e => e.offsetParent).length")
                print(f"focus from v. {tagged[0]}:", "ok" if shown else "EMPTY", f"({shown} comments)"); pg.keyboard.press("Escape"); pg.wait_for_timeout(1200)
                if not shown: bad.append("focus from verse")
            sw = pg.query_selector("#langseg button[data-lang=la]")
            if sw:
                sw.click(); pg.wait_for_timeout(800); lat = pg.evaluate("document.querySelectorAll('details.art .para p[lang=la]').length") == sum(len(a["paras"]) for a in data)
                print("Latin view:", "ok" if lat else "LATIN NOT SHOWN"); pg.click("#langseg button[data-lang=en]")
                if not lat: bad.append("latin")
            else:
                print("Latin view: switch not found (check by hand)")
            print("page errors:", errs or "none")
            if errs: bad.append("errors")
            b.close()
    finally:
        srv.terminate()
    print("RESULT:", "ok" if not bad else "PROBLEMS: " + ", ".join(bad))
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
