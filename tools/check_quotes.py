"""Check every scripture quotation in the commentary against the Douay-Rheims text.

Usage:  python3 tools/check_quotes.py            (checks every file in data/commentary/)
        python3 tools/check_quotes.py genesis    (checks one book)

Every [[ref|Douay-Rheims wording|Vulgate wording]] marker in an "en" field must
quote the Douay-Rheims verse exactly (case and punctuation ignored). The script
also checks the verse tags: each paragraph's range must be inside the chapter,
and inside an article the tags should run on without gaps.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIBLE = os.path.join(ROOT, "data", "bible", "drc")
COMM = os.path.join(ROOT, "data", "commentary")

# Douay abbreviations used in refs -> data file id. Keep in step with NT_ABBR in index.html.
ABBR = {
    "Gen": "genesis", "Ex": "exodus", "Lev": "leviticus", "Num": "numbers", "Deut": "deuteronomy",
    "Jos": "joshua", "Judg": "judges", "Ruth": "ruth", "1 Kings": "i-samuel", "2 Kings": "ii-samuel",
    "3 Kings": "i-kings", "4 Kings": "ii-kings", "1 Par": "i-chronicles", "2 Par": "ii-chronicles",
    "1 Esd": "ezra", "2 Esd": "nehemiah", "Tob": "tobit", "Jdt": "judith", "Esth": "esther", "Job": "job",
    "Ps": "psalms", "Prov": "proverbs", "Eccles": "ecclesiastes", "Cant": "song-of-solomon", "Wis": "wisdom",
    "Ecclus": "sirach", "Is": "isaiah", "Jer": "jeremiah", "Lam": "lamentations", "Bar": "baruch",
    "Ezech": "ezekiel", "Dan": "daniel", "Osee": "hosea", "Joel": "joel", "Amos": "amos", "Abd": "obadiah",
    "Jon": "jonah", "Mich": "micah", "Nah": "nahum", "Hab": "habakkuk", "Soph": "zephaniah", "Agg": "haggai",
    "Zach": "zechariah", "Mal": "malachi", "1 Mach": "i-maccabees", "2 Mach": "ii-maccabees",
    "Matt": "matthew", "Mark": "mark", "Luke": "luke", "John": "john", "Acts": "acts", "Rom": "romans",
    "1 Cor": "i-corinthians", "2 Cor": "ii-corinthians", "Gal": "galatians", "Eph": "ephesians",
    "Phil": "philippians", "Col": "colossians", "1 Thess": "i-thessalonians", "2 Thess": "ii-thessalonians",
    "1 Tim": "i-timothy", "2 Tim": "ii-timothy", "Tit": "titus", "Philem": "philemon", "Heb": "hebrews",
    "Jas": "james", "1 Pet": "i-peter", "2 Pet": "ii-peter", "1 John": "i-john", "2 John": "ii-john",
    "3 John": "iii-john", "Jude": "jude", "Apoc": "revelation-of-john",
}
Q = re.compile(r"\[\[([^|\]]+)\|([^|\]]*)\|([^\]]*)\]\]")
_cache = {}

def verses(book):
    if book not in _cache:
        _cache[book] = json.load(open(os.path.join(BIBLE, book + ".json")))
    return _cache[book]

def words(s):
    return re.sub(r"[^a-z ]", "", s.lower().replace("-", " ")).split()

def check(book):
    data = json.load(open(os.path.join(COMM, book + ".json")))
    problems, n = [], 0
    for ch, arts in data["chapters"].items():
        nverses = len(verses(book)[int(ch) - 1])
        for art in arts:
            where = f"{book} {ch}, Art. {art['num']}"
            prev_end = None
            for i, p in enumerate(art["paras"]):
                a, b = p["v"]
                if not (1 <= a <= b <= nverses):
                    problems.append(f"{where} para {i+1}: verse tag {a}-{b} is outside the chapter (1-{nverses})")
                if prev_end is not None and a > prev_end + 1 and not p.get("gap_ok"):
                    problems.append(f"{where} para {i+1}: gap in verse tags ({prev_end} -> {a}); fine only if Denis skips on purpose")
                prev_end = max(prev_end or 0, b)
                for ref, dr, _vul in Q.findall(p.get("en", "")):
                    n += 1
                    m = re.match(r"^(.*?)\s*(\d+):(\d+)$", ref)
                    if not m:
                        problems.append(f"{where} para {i+1}: bad ref '{ref}'"); continue
                    abbr, c, v = m.group(1), int(m.group(2)), int(m.group(3))
                    target = book if not abbr else ABBR.get(abbr)
                    if not target:
                        problems.append(f"{where} para {i+1}: unknown book abbreviation '{abbr}'"); continue
                    try:
                        verse = verses(target)[c - 1][v - 1]
                    except IndexError:
                        problems.append(f"{where} para {i+1}: {ref} does not exist"); continue
                    if " ".join(words(dr)) not in " ".join(words(verse)):
                        problems.append(f"{where} para {i+1}: quote does not match {ref}\n    quote: {dr}\n    verse: {verse}")
    return n, problems

if __name__ == "__main__":
    books = sys.argv[1:] or [f[:-5] for f in sorted(os.listdir(COMM)) if f.endswith(".json")]
    total, bad = 0, 0
    for b in books:
        n, probs = check(b)
        total += n; bad += len(probs)
        for p in probs: print(p)
    print(f"{total} quotations checked, {bad} problem(s).")
    sys.exit(1 if bad else 0)
