# Denis the Carthusian commentary app: project guide

A Bible reader (Douay-Rheims) with the scripture commentary of Bl. Denis the Carthusian
(Dionysius Cartusianus), translated from the Latin *Opera Omnia* (Montreuil, 1896–).
Owner: Dave. Live site: GitHub Pages from the `main` branch root.

## Layout

- `index.html`: the whole interface (HTML, CSS, JS in one file). Look and features only, no content.
- `data/bible/drc/<book-id>.json`: Douay-Rheims (Challoner), Vulgate canon, order and numbering
  (Psalms numbered as in the Vulgate; 1–4 Kings = 1–2 Samuel + 1–2 Kings, etc.).
  Format: array of chapters, each an array of verse strings.
- `data/commentary/<book-id>.json`: Denis's commentary for one book (see format below).
  When a new book gets commentary, add its id to `COMMENTARY_BOOKS` in `index.html`.
- `tools/check_quotes.py`: run after every content change. Must report 0 problems.
- `tools/build_bible.py`: how the Bible files were made (source: scrollmapper/bible_databases, DRC.json).

Interface and content are deliberately separate: interface changes must never require
touching the commentary files, and vice versa.

## Commentary file format

```json
{
  "work": "Enarratio in Genesim",
  "source": "Dionysii Cartusiani Opera Omnia, t. I (Montreuil, 1896), pp. …",
  "chapters": {
    "31": [
      {
        "num": "LXXVII",                       // article number, Roman
        "title": "Elucidatio capituli …",      // Latin title as printed
        "title_en": "Explanation of …",        // English title
        "pages": "pp. 349–353",
        "note": "optional note shown at the top of the article",
        "paras": [
          { "v": [1, 3], "t": "Latin text …", "en": "English text with quote markers …" }
        ]
      }
    ]
  }
}
```

Articles are sorted by number in the app automatically, but keep them in order in the file too.

## Quotation markers (in the `en` field)

`[[ref|Douay-Rheims wording|Vulgate wording]]`

- `ref` is `C:V` for the book being treated (e.g. `31:5`), or `Abbr C:V` for anywhere else,
  using Douay names and Vulgate numbering: `Ps 84:9`, `1 Kings 19:13` (= 1 Samuel), `3 Kings 17:20`,
  `Is 8:13`, `Zach 2:3`, `Matt 2:13`, `Rom 12:1`, `Apoc 1:12`. Allowed abbreviations: see `ABBR`
  in `tools/check_quotes.py`; New Testament ones must also be in `NT_ABBR` in `index.html`.
- The Douay-Rheims wording must be copied exactly from `data/bible/drc` (only the part Denis
  quotes). The Vulgate wording is the matching Clementine Latin; the Latin view uses it to find and
  colour the quotation in Denis's own text.
- Every direct quotation of scripture gets a marker, including the lemmata (the bits of the verse
  Denis quotes before glossing them). Allusions and paraphrases do not.

How they display (do not change without Dave asking):
- quotation from the chapter being treated: *italic*, normal ink, no reference shown
- other Old Testament (including other chapters of the same book): **blue**, with reference
- New Testament: **red**, with reference
- verse tags ("vv. 4–7") and verse numbers: red

## Verse tags (`v` on each paragraph)

- If Denis reads straight through, the tags must be continuous, with no gaps, even if some verses are
  not explicitly discussed (e.g. 4–8, 9–13, not 4, 9).
- Repeat or overlap only where he really does: a verse split across two paragraphs, a digression
  that dwells on one verse (Lyra on *teraphim* at 31:19), or going back to a verse.
- Gaps are fine only where Denis himself jumps out of order or deliberately skips. Mark such a paragraph
  with `"gap_ok": true` so `check_quotes.py` accepts it (e.g. Exodus 20, Art. XLI goes from v. 12 to v. 21).

## Translation style

- Faithful but readable English. Keep Denis's structure (lemma, then gloss: "that is, …").
- Keep "etc." where he abbreviates a quotation. Keep his spellings of names and of the Hebrew/Syriac
  forms he gives (e.g. *Jegarsyntha*).
- Translator's notes go in square brackets, sparingly, and only where they help:
  technical theological terms (e.g. "officious lie [that is, a lie told to avert harm, not a malicious one]")
  and wordplay lost in English (e.g. *virga* = "rod", where the Douay-Rheims has "sceptre").
  Dave likes these notes.
  In the app, a bracketed note shows as a small "i" marker the reader taps to open; "[…]" (missing
  text) and short fragments like "epulan[di]" are not treated as notes. Write notes as at least four
  characters inside the brackets.
- The English article title goes in `title_en`.

## Getting the Latin text

Scans (Dave supplies the PDFs; the workspace cannot download from archive.org or Google Books):
- t. I (Genesis–Exodus 19): archive.org `operaomniainunum01deni`. Text layer is unusable and some
  areas are faded. PDF page = printed page + 106 around Genesis 30 (PDF 451 = p. 345).
- t. II (Exodus 20 onward): Google scan `doctorisecstati00unkngoog`. Clean and dark. PDF 14 = p. 1.
  The scan repeats some pages (PDF 23–31 and 37–39 repeat earlier ones); PDF 31 (p. 10) is garbled,
  use PDF 39. Always map PDF pages to printed pages before assembling.

- t. XI (Matthew 1–28, Mark 1–16, Luke 1–9): archive.org `operaomniainunum11deni`. Yellowed but crisp.
  PDF page = printed page + 20. Already OCR'd page by page into `sources/t11/pages/`; the work queue
  is `sources/t11/queue.json`. Pages OCR'd before the heading-split improvement (roughly PDF 21–215)
  read left column then right column even where a new article starts mid-page, so put the text
  around a mid-page heading back in order by the sense. (The heading pages were later re-read in
  order; `sources/t11/articles/` holds most articles already cut out.)
- t. XII (Luke 10–24 = Art. XXVI–L, John 1–21 = Art. I–L): Google Play scan supplied by Dave. Clean.
  PDF page = printed page + 10. Commentary on PDF 11–630 (John's PROOEMIUM PDF 275–276, Art. I PDF 277);
  indexes after. OCR'd into `sources/t12/pages/` (all with the heading split); queue
  `sources/t12/queue.json`; pre-cut articles in `sources/t12/articles/`. Done after t. XI.

Translation runs follow `TRANSLATING.md` (procedure) with `tools/verses.py` (Douay-Rheims + Vulgate
lookup; Vulgate text is in `sources/vulgate/`, not shown in the app), `tools/find_quotes.py` (finds
runs of words in an article that match the Vulgate chapter, to catch lemmata and quotations) and
`tools/add_article.py` (merges a finished article and switches the book on in the app).
`tools/cut_articles.py <vol>` pre-cuts queued articles from the OCR pages.

Tools: `tools/ocr_columns.py` (cuts each page at the gutter, drops running head and marginal notes,
OCRs each column with Tesseract's Latin model) and `tools/assemble.py` (joins columns, removes running
heads and gutter letters A–D, rejoins hyphenated words). Article titles span both columns, so find them
with a full-page OCR pass. The printed text sets scripture quotations in italics, which helps in
spotting lemmata.

The printed volumes have two columns per page. Plain text extracted from the scans mixes the two
columns line by line; the letters A–D in the gutter mark quarters of the page. Prefer cutting each page
image at the gutter and OCR-ing each column separately, then checking the reading order by the sense.
Strip running heads, page numbers and marginal references (keep Denis's inline references such as
"(Ps. lxxxiv, 9)"); join words hyphenated across lines.

## Interface features (for reference when changing index.html)

- Above the commentary bubbles (under the Commentary heading): a "References:" key — Current Chapter (italic), Old Testament (blue), New
  Testament (red) — each in its own style; hidden in focus view.
- Icon: Petrus Christus, Portrait of a Carthusian (1446), cropped to the face — apple-touch-icon.png
  (Safari Favorites / Home Screen), favicon-32.png, icon-192/512.png, manifest.webmanifest.
- Footer: the notice "COMMENTARY TRANSLATED USING ARTIFICIAL INTELLIGENCE AND HAS NOT BEEN REVIEWED BY A
  COMPETENT AUTHORITY" (Dave's wording; keep it), then the source line. No per-chapter draft markers.
- Header: book and chapter menus (✠ marks those with commentary) and a search button. No site title.
- Chapter title with ‹ › arrows on either side; swipe left/right on phones to change chapter.
- The app reopens on the last chapter read (stored in the reader's browser).
- Articles start collapsed. Tapping a verse, or a verse tag in the commentary, opens focus view: only
  those verses and the matching comments (each under its article number and title), in two bubbles with a
  small gap; header and title blurred; the background fades out where it stands, then the selected verses glide up
  into place and the commentary rises in beneath them (leaving: the column dips briefly and returns);
  a small × (or Esc) returns the reader to where they were, with articles opened/closed as before.
- Search covers all commentary (English, or Latin when the Latin view is on); a result opens that
  comment in focus view.

## Before committing

1. `python3 tools/check_quotes.py`: 0 problems.
2. Open the app (`python3 -m http.server`) and check the changed chapters: chapter text, articles in
   order, focus view from a verse tag and from a verse, English/Latin switch.
