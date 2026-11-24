#!/usr/bin/env python3
"""Queues in one command (test prototype). Keeps each queue file's own layout.
  python3 tools/queue.py next                 the first claimable item in TRANSLATING.md's order (or "none")
  python3 tools/queue.py claim <vol> <id>     claim it: set in-progress + claimed time, commit, pull --rebase, push
                                              (prints "claimed" or "taken" if someone else got it first)
  python3 tools/queue.py done <vol> <id> [note]   status done (+ note), for the publish commit
  python3 tools/queue.py set <vol> <id> <status> [note]"""
import json, os, sys, subprocess, time
ROOT = os.getcwd() if os.path.isdir(os.path.join(os.getcwd(), "data")) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDER = [("retag", "sources/retag.json"), ("t11r", "sources/t11/recheck.json")] + \
        [(v, f"sources/{v}/queue.json") for v in ("t11", "t12", "t13", "t6", "t7", "t10", "t1", "t4", "t5", "t8", "t9", "t2", "t3", "t14")]

def path(vol): return os.path.join(ROOT, dict(ORDER).get(vol, f"sources/{vol}/queue.json"))
def load(vol):
    raw = open(path(vol)).read(); return json.loads(raw), raw.endswith("\n")
def save(vol, q, nl):
    s = json.dumps(q, ensure_ascii=False, indent=1); open(path(vol), "w").write(s + ("\n" if nl else ""))
def items(q): return q["items"] if isinstance(q, dict) else q
def git(*a): return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)

def claimable(i):
    if i.get("status") == "todo": return True
    if i.get("status") == "in-progress" and i.get("claimed"):
        t = time.mktime(time.strptime(i["claimed"][:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
        return time.time() - t > 7200
    return False

def setstatus(vol, iid, status, note=None, claim=False):
    q, nl = load(vol); it = next(i for i in items(q) if i["id"] == iid)
    it["status"] = status
    if claim: it["claimed"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if note: it["note"] = note
    save(vol, q, nl); return it

def main(a):
    if a[0] == "next":
        # items with "order" (Dave's order across volumes, set by tools/cut_ocr.py) go by that number; the rest by
        # queue file, then position, after the re-tag and re-check queues
        git("pull", "-q", "--rebase", "origin", "main")
        best = None
        for rank, (vol, p) in enumerate(ORDER):
            if not os.path.exists(os.path.join(ROOT, p)): continue
            for k, i in enumerate(items(json.load(open(os.path.join(ROOT, p))))):
                if not claimable(i): continue
                key = (0, 0, rank, k) if vol in ("retag", "t11r") else ((1, i["order"], 0, 0) if "order" in i else (2, 0, rank, k))
                if best is None or key < best[0]: best = (key, vol, i)
        if not best: return print("none")
        _, vol, i = best
        return print(vol, i["id"], json.dumps({k: i[k] for k in i if k not in ("status",)}, ensure_ascii=False))
    if a[0] == "claim":
        vol, iid = a[1], a[2]
        git("pull", "-q", "--rebase", "origin", "main")
        q, _ = load(vol); it = next(i for i in items(q) if i["id"] == iid)
        if not claimable(it): return print("taken")
        setstatus(vol, iid, "in-progress", claim=True)
        git("commit", "-qam", f"Claim {iid}")
        r = git("pull", "-q", "--rebase", "origin", "main"); p = git("push", "-q", "origin", "HEAD:main")
        if r.returncode or p.returncode:
            git("rebase", "--abort"); git("reset", "-q", "--hard", "origin/main"); return print("taken")
        return print("claimed")
    if a[0] in ("done", "set"):
        status = "done" if a[0] == "done" else a[3]
        note = a[3] if a[0] == "done" and len(a) > 3 else (a[4] if a[0] == "set" and len(a) > 4 else None)
        setstatus(a[1], a[2], status, note); return print(status)

if __name__ == "__main__":
    main(sys.argv[1:])
