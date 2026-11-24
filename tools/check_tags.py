#!/usr/bin/env python3
"""Verse tags against what each paragraph actually treats (Dave, 17 Nov 2026).

A paragraph's tag must list only verses of the chapter that the paragraph quotes, cites, or plainly
discusses. This lists, for one article (or all), every paragraph whose tag holds verses it neither quotes
([[C:V|…]]) nor cites ([[C:V||]]): read those and either confirm the verse is discussed (paraphrased,
explained, "this verse") or take it out of the tag. A paragraph with no tag is fine (an introduction, a
general question).

  python3 tools/check_tags.py john 3 VIII     # one article, every paragraph shown
  python3 tools/check_tags.py john 3          # every article of a chapter, flagged paragraphs only
  python3 tools/check_tags.py --summary       # counts for the whole app
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMM = os.path.join(ROOT, "data", "commentary")
MARK = re.compile(r"\[\[(\d+):(\d+)(?:-(\d+))?\|([^|\]]*)\|")

def tagged(p):
    if p.get("verses"): return list(p["verses"])
    if p.get("v"): return list(range(p["v"][0], p["v"][1] + 1))
    return []

def evidence(p, ch):
    quoted, cited = set(), set()
    for m in MARK.finditer(p.get("en", "")):
        if m.group(1) != str(ch): continue
        vs = range(int(m.group(2)), int(m.group(3) or m.group(2)) + 1)
        (quoted if m.group(4).strip() else cited).update(vs)
    return quoted, cited

def label(vs):
    if not vs: return "no tag"
    runs = []
    for n in sorted(vs):
        if runs and n == runs[-1][1] + 1: runs[-1][1] = n
        else: runs.append([n, n])
    return ("vv. " if len(vs) > 1 else "v. ") + ", ".join(str(a) if a == b else f"{a}–{b}" for a, b in runs)

def flagged(p, ch):
    q, c = evidence(p, ch)
    return [v for v in tagged(p) if v not in q | c]

def show(book, ch, art, all_paras):
    out = []
    for i, p in enumerate(art["paras"]):
        f = flagged(p, ch); q, c = evidence(p, ch)
        if not (all_paras or f): continue
        head = f"  para {i + 1}: tag {label(tagged(p))}; quotes {label(q) if q else '-'}; cites {label(c) if c else '-'}"
        if f:     # needs a judgment: shown in full (--brief: the start only, for paragraphs you wrote yourself)
            out.append(head + f"\n    NOT QUOTED OR CITED: {label(f)} (confirm each is discussed, or drop it)"
                       + "\n    " + p.get("en", "")[:(300 if BRIEF else 2000)].replace("\n", " ") + (" …" if BRIEF else ""))
        else:     # every tagged verse is quoted or cited: nothing to decide, one line
            out.append(head)
    if out: print(f"== {book} {ch}, Art. {art['num']}\n" + "\n".join(out))
    return len(out)

def main(a):
    if a and a[0] == "--summary":
        tot = fl = 0
        for f in sorted(os.listdir(COMM)):
            d = json.load(open(os.path.join(COMM, f)))
            for ch, arts in d["chapters"].items():
                for art in arts:
                    for p in art["paras"]:
                        tot += 1; fl += bool(flagged(p, ch))
        return print(f"{fl} of {tot} paragraphs have tagged verses they neither quote nor cite")
    book = a[0]; d = json.load(open(os.path.join(COMM, book + ".json")))
    for ch, arts in d["chapters"].items():
        if len(a) > 1 and ch != a[1]: continue
        for art in arts:
            if len(a) > 2 and art["num"] != a[2]: continue
            show(book, ch, art, len(a) > 2)

BRIEF = "--brief" in sys.argv
if __name__ == "__main__":
    main([x for x in sys.argv[1:] if x != "--brief"])
