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
- A margin reference that points to a passage without Denis quoting its words (a story he retells, an
  allusion) gets a reference-only marker with both wordings empty, `[[4 Kings 24:12||]]`, written straight
  after the clause it belongs to (no space). It shows as a small tappable reference, "(4 Kings 24:12)"; a
  reference to the chapter treated shows as "(v. 16)".
- Lemmata (the bits of the chapter treated that Denis quotes before glossing them) get a marker.
- A quotation from anywhere else gets a marker where the printed margin gives a reference for it
  (Dave's rule; see `TRANSLATING.md` step 5), and also wherever Denis is obviously quoting Scripture
  though the margin gives no reference (Dave, 12 Nov 2026: these must be tagged too) (Denis names the source, or quotes word for word at length; `tools/recheck.py` lists these
  so none is missed). Short or loose phrases with no margin note are not hunted for. Where the margin reference is
  unclear or does not fit, a bracketed translator's note at that place says so. Allusions, paraphrases
  and stories with a margin reference get a reference-only marker (below); without one, nothing.

How they display (do not change without Dave asking):
- quotation from the chapter being treated: *italic*, normal ink, no reference shown
- other Old Testament (including other chapters of the same book): **blue**, with reference
- New Testament: **red**, with reference
- the theme follows the testament (Dave): in a New Testament book the accent colour is red, in an Old
  Testament book blue: verse numbers, the ✠ under the title, verse tags ("vv. 4–7"), article numbers, the
  tapped-verse tint, hover/focus outlines (CSS: `--rubric` is the accent; `body.ot-book` sets it to `--ot`).
  Quotations keep their own colours whatever the theme (OT blue `--ot`, NT red `--nt`), and so does the AI
  notice (red). A reference layer takes the colour of the verse it shows (`.layer.ot-ref` / `.nt-ref`).

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

Scans (Dave supplies the PDFs; the workspace cannot download from archive.org or Google Books).
Scan pages with `python3 tools/ocr_columns.py <pdf> <first> <last> sources/<vol>/pages`, which reads the
margins too. Pages scanned before this (t. XI PDF 87–111 and 282–355, all of t. XII) still need one
catch-up `python3 tools/margins.py read <vol> <pdf> <first> <last>`:
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
- t. XII (Luke 10–24 = Art. XXVI–L, John 1–21 = Art. I–L): archive.org `operaomniainunum12deni`. Clean.
  PDF page = printed page + 10. Commentary on PDF 11–630 (John's PROOEMIUM PDF 275–276, Art. I PDF 277);
  indexes after. OCR'd into `sources/t12/pages/` (all with the heading split); queue
  `sources/t12/queue.json`; pre-cut articles in `sources/t12/articles/`. Done after t. XI.

Translation runs follow `TRANSLATING.md` (procedure) with `tools/verses.py` (Douay-Rheims + Vulgate
lookup; Vulgate text is in `sources/vulgate/`, not shown in the app), `tools/find_quotes.py` (finds
runs of words in an article that match the Vulgate; no longer used for references, which come from the
margins only) and
`tools/add_article.py` (expands shorthand quotation markers with `tools/expand_quotes.py`, merges a
finished article and switches the book on in the app).
`tools/cut_articles.py <vol>` pre-cuts queued articles from the OCR pages. `tools/margins.py` reads the
marginal references (book, chapter, verse of each quotation, and the verse numbers of the chapter
treated) into `sources/<vol>/margins/`, and lists them per article for the runs. `tools/recheck.py` compares a published
article's references with its margins (`sources/t11/recheck.json` is the re-check queue).

Tools: `tools/ocr_columns.py` (cuts each page at the gutter, drops running head and marginal notes,
OCRs each column with Tesseract's Latin model, and in the same run reads the marginal references into
`sources/<vol>/margins/`: scanning a page always brings its margins; `--no-margins` skips that) and `tools/assemble.py` (joins columns, removes running
heads and gutter letters A–D, rejoins hyphenated words). Article titles span both columns, so find them
with a full-page OCR pass. The printed text sets scripture quotations in italics, which helps in
spotting lemmata.

The printed volumes have two columns per page. Plain text extracted from the scans mixes the two
columns line by line; the letters A–D in the gutter mark quarters of the page. Prefer cutting each page
image at the gutter and OCR-ing each column separately, then checking the reading order by the sense.
Strip running heads, page numbers and marginal references from the text (keep Denis's inline references
such as "(Ps. lxxxiv, 9)"); join words hyphenated across lines. The marginal references are kept
separately, by `tools/margins.py`.

## Interface features (for reference when changing index.html)

- Home screen, shown every time the app is opened or refreshed (`#home`, over the reader, which loads the
  last chapter underneath): title "Sacred Scripture / with Commentary by / Blessed Denis the Carthusian", a ✠,
  the portrait (`portrait.jpg`: Petrus Christus, Portrait of a Carthusian, frame cropped off) faded into the page
  with an oval mask and warmed toward the paper colour, Pope Eugene IV's words "Let Mother Church rejoice to have
  such a son!", a red READ button (goes to the chapter last read), and that chapter's name beneath it. (Dave)
- Commentary heading: "Commentary by Bl. Denis the Carthusian" (no subheading), with the English/Latin
  switch beside it (beneath it on phones).
- Above the commentary bubbles (under the Commentary heading): a "References:" key — Current Chapter (italic), Old Testament (blue), New
  Testament (red) — each in its own style; hidden in focus view.
- Icon: Petrus Christus, Portrait of a Carthusian (1446), cropped to the face — apple-touch-icon.png
  (Safari Favorites / Home Screen), favicon-32.png, icon-192/512.png, manifest.webmanifest.
- Footer: the notice "COMMENTARY HAS BEEN TRANSLATED USING ARTIFICIAL INTELLIGENCE AND HAS NOT BEEN REVIEWED BY A
  COMPETENT AUTHORITY" (Dave's wording; keep it; small red capitals), then the source line. No per-chapter draft markers.
- Header: book and chapter menus (✠ marks those with commentary), a sun/moon button and a search button.
  No site title. The sun/moon button switches light/dark and remembers the choice (`localStorage.theme`,
  applied by a small script in <head> before the page is drawn); with no choice saved, the phone's setting
  decides (CSS `:root[data-theme]` and `prefers-color-scheme`).
  The strip around the iPhone Dynamic Island follows the same choice (Dave): the `theme-color` meta is set in
  that <head> script and on every switch, the Home Screen app uses status-bar-style `default` (no `theme_color` in
  the manifest), and the sticky header is opaque `var(--bg)`, since Safari on iOS 26 takes the colour from it.
- Chapter title with ‹ › arrows on either side; swipe left/right on phones to change chapter.
- A floating button at the bottom right (`#jumpBtn`; on wide screens in the margin just right of the column)
  stays in place while scrolling: "Commentary ↓" while the reader is in the chapter text, "↑ Text" once in
  the commentary; it scrolls there. Hidden on chapters without commentary, in focus view, over layers, search
  and the home screen. (Dave: on the right, present while scrolling either section)
- Reading column at most 720px wide (about 72 characters a line on a computer). Commentary paragraphs are
  justified on wide screens, flush-left on phones (≤600px), where the article number sits above its title.
- The app reopens on the last chapter read (stored in the reader's browser).
- Articles start collapsed. Tapping a verse, or a verse tag in the commentary, opens focus view: only
  those verses and the matching comments (each under its article number and title), in two bubbles with a
  small gap; header and title blurred; the background fades out where it stands, then the selected verses glide up
  into place and the commentary rises in beneath them (leaving: the column dips briefly and returns);
  a small × (or Esc, or a tap anywhere outside the bubbles) returns the reader to where they were, with
  articles opened/closed as before.
  When focus view comes from a tapped verse and shows more verses than that one, the tapped verse is tinted
  light red. The comments most specific to it come first (those on one or two verses, e.g. v. 6 or vv. 6–7,
  or failing that the narrowest range shown; narrowest first), then all the others in Denis's own order;
  all of them are still shown, and the page order is restored on leaving.
- Reference layers: tapping a blue or red quotation (or its reference) in the commentary, in the chapter or
  in focus view, opens a layer over the page with that verse and Denis's comments on it (from that book's
  commentary file, when there is one; otherwise the verse alone with "not in the app yet"). References inside
  a layer open further layers; × (or Esc) goes back one layer, and what was underneath is unchanged.
  The layer's heading and "Open <chapter> ›" are blue for an Old Testament reference, red for the New;
  "Open <chapter> ›" leaves the layers and goes to
  that chapter, focused on the verse if it has commentary.
  References are resolved with `ABBR` in `index.html` (keep in step with `tools/check_quotes.py`).
- Search covers all commentary (English, or Latin when the Latin view is on); a result opens that
  comment in focus view.

## Before committing

1. `python3 tools/check_quotes.py`: 0 problems.
2. Open the app (`python3 -m http.server`) and check the changed chapters: chapter text, articles in
   order, focus view from a verse tag and from a verse, English/Latin switch.
