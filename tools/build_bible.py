import json, sys, re
src = sys.argv[1]; out = sys.argv[2]
d = json.load(open(f"{src}/DRC.json")); v = json.load(open(f"{src}/VulgClementine.json"))
books = []
for a, b in zip(d["books"], v["books"]):
    if a["name"] in ("Prayer of Manasses","I Esdras","II Esdras","Additional Psalm","Laodiceans"): continue
    bid = re.sub(r"[^a-z0-9]+", "-", a["name"].lower()).strip("-")
    for tr, bk in (("drc", a), ("vul", b)):
        chs = [[x["text"].strip() for x in c["verses"]] for c in bk["chapters"]]
        json.dump(chs, open(f"{out}/{tr}/{bid}.json", "w"), ensure_ascii=False, separators=(",", ":"))
    books.append([bid, a["name"], len(a["chapters"])])
print(len(books)); print(json.dumps(books))
