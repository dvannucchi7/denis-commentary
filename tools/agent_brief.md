# Brief for a worker translating an article or part of one

You translate an article, or one part of an article, of Bl. Denis the Carthusian's scripture commentary (Latin, *Opera Omnia*,
Montreuil) for Dave's Douay-Rheims reader app. Do not edit repository files, run git or `tools/add_article.py`.
The message that sent you here names: the article (book, chapter, number, Latin title), your Latin file ("your part" below, even if it is the whole article),
its margin notes file (only your part's notes), your output file and your test file.
This brief holds every rule you need (it condenses `CLAUDE.md` and `TRANSLATING.md`; do not read those).

## Tools (run from /home/claude/denis-commentary or the repo root)
- `python3 tools/verses.py --chapter john 11` prints a chapter (Douay-Rheims `DR:` and Vulgate `V:`);
  `python3 tools/verses.py "Ps 26:13" "Rom 8:32"` prints single verses. Look up every reference you use.
- Book abbreviations (use exactly these): Gen Ex Lev Num Deut Jos Judg Ruth, 1 Kings 2 Kings (= 1–2 Samuel),
  3 Kings 4 Kings (= 1–2 Kings), 1 Par 2 Par, 1 Esd 2 Esd, Tob Jdt Esth Job Ps Prov Eccles Cant Wis Ecclus
  Is Jer Lam Bar Ezech Dan Osee Joel Amos Abd Jon Mich Nah Hab Soph Agg Zach Mal 1 Mach 2 Mach; Matt Mark
  Luke John Acts Rom 1 Cor 2 Cor Gal Eph Phil Col 1 Thess 2 Thess 1 Tim 2 Tim Tit Philem Heb Jas 1 Pet
  2 Pet 1 John 2 John 3 John Jude Apoc. Vulgate numbering throughout (Psalms as in the Vulgate).

## 1. The Latin (`t`)
- Put the text in reading order (left column, then right; where the OCR has put lines out of order, e.g.
  around a heading or at a page break, restore the order by the sense). Rejoin words broken across lines.
- Correct obvious OCR slips (eum→cum, seript→script, hoe→hoc, prae→præ, commas read as full stops, stray
  `?`/`!` for `t`). Drop gutter letters A–D, stray `)` `(` `|`, page numbers, running heads, and digits that
  are misread margin verse numbers (`— 45`). Keep Denis's own Latin, spelling and punctuation (æ, œ, j, quum,
  his variant readings of Scripture): do not normalize or rewrite it. When unsure, keep what is printed.
- Never put the article heading (ARTICULUS …, its title) in a paragraph. Where a word is lost, write `[…]`
  in both `t` and `en` and say so in your final message; never invent missing text.
- **Transcribed volumes** (t13, t6, t7, t10, t1: the Latin was transcribed from page images, not OCR'd):
  italics are `_…_` (Scripture is printed in italics: a help in spotting lemmata), headings `### …`,
  `[…]` marks what the transcriber could not read, and each margin note stands in `⟦…⟧` at the start of the
  line it is beside (`⟦Rom. xii, 1.⟧` a reference, `⟦5⟧` the start of verse 5). Those `⟦…⟧` notes are your
  margin notes. Remove the `_`, `###` and `⟦…⟧` from `t`.

## 2. Paragraphs and verse tags (`v`)
- Start a new paragraph where Denis takes a new lemma or a new section (*Mystice*, *Moraliter*, a question).
- Tag a paragraph only with the verses of the chapter treated that it quotes, cites, or plainly discusses
  (explains its words or sense, paraphrases it, answers a question it raises, reads it mystically or morally,
  digresses on it). Never add a verse because it comes next or to fill a gap; a passing mention does not count.
- `"v": [first, last]` for one run; for a broken run add `"verses": [4, 8]` beside `"v": [4, 8]`.
- No `v` at all for a paragraph tied to no verse (introduction, general question or doctrine, summary of the
  chapter); never v. 1 by default. Gaps, repeats and overlaps between paragraphs are fine.
- Margin lines "verse N begins: …" show where each verse of the chapter treated begins. The numerals are
  often misread (94 = 24), and some come from verse numbers of other books printed in the margin: judge by
  the text.

## 3. The English (`en`)
- Faithful but readable English. Keep Denis's structure: the lemma, then his gloss ("that is, …"). Keep
  "etc." where he abbreviates a quotation. Keep his spellings of names and of Hebrew/Greek/Syriac forms.
  Biblical names as in the Douay-Rheims (Isaias, Jeremias, Elias, Osee, Pharao…); Fathers and Doctors in
  plain English (Augustine, Jerome, Chrysostom, Bede, Gregory, Thomas, Lyra, the Gloss…).
- Translator's notes in square brackets, sparingly, where they help: technical theological terms ("officious
  lie [that is, a lie told to avert harm, not a malicious one]"), wordplay or a point of the Latin lost in
  English, an uncertain reference. Dave likes them. At least four characters inside the brackets; never use
  square brackets for anything else (except `[…]`).

## 4. Quotation markers (in `en`)
Form: `[[REF|Douay-Rheims words|Denis's Latin words]]`. The marker *replaces* your English for those words
(the reader sees the Douay-Rheims there), so the sentence around it must read naturally.
- REF: `C:V` for the book treated (e.g. `11:25`); `Abbr C:V` for anything else (`Ps 44:8`, `John 9:6` from
  another chapter of the same book, `Matt 14:25` from another Gospel). One verse per marker: a quotation over
  two verses gets two markers; never a range.
- **Shorthand**: give two or three words from the start and the end of the quoted part, joined by " … ":
  `[[Ps 44:8|hath anointed … fellows|Unxit te … tuis]]`. The Douay-Rheims side must be the verse's own words
  in its own order, and each anchor must occur only once (add words if not). The Latin side is taken from
  your paragraph's `t`, so it keeps Denis's wording. `*` = the whole verse (`[[11:35|*|*]]`). A short quotation
  can be written out in full instead. Quote only the part Denis quotes. Where he breaks into a quotation
  with his own words (*inquit*, *id est …*), use two markers, one on each side of them.
- Where the same words stand in several books (the Gospels, Psalms quoted in the Epistles), use the verse
  the margin or Denis names.
- **Lemmata** (Denis quoting the chapter treated) are always marked.
- **Quotations from elsewhere**: mark every one for which the margin gives a reference, and also every
  *obvious* one the margin misses: Denis names the source ("as the Apostle says", "in the Psalm", "Isaias:"),
  or the words are word for word at length. Do not hunt for short or loose phrases with no margin note.
- **Reference-only marker** `[[REF||]]` (both fields empty), written straight after the clause it belongs to,
  no space: where the margin gives a reference but Denis does not quote the words (he retells a story, names a
  person or event, alludes, paraphrases loosely): `…went out to the king of Babylon[[4 Kings 24:12||]]`.
- **Every margin reference in your part ends up as a quotation marker or a reference-only marker**, or, if no
  verse fits, as a bracketed note at that place giving the margin's reading.
- **Check every margin reference.** The book is almost always read right; the small numerals often are not.
  Look the verse up and compare it with the Latin beside the note; if it does not fit, find the right verse in
  the book the margin names. `corrected` is only the tool's suggestion (it can be wrong where the print was
  right); `allusion?` means no word-for-word match (usually an allusion, sometimes a misread number);
  `[unread: …]` notes still count. A note citing only a chapter (Gen. xlix) is verse 1 of that chapter.
  "Ibid." refers to the book of the note before it.
- Where anything is uncertain (the margin's verse does not fit, Denis is closer to another verse, his wording
  differs from the Douay-Rheims), add a bracketed note there: "[the margin gives Ecclus. xx, 32; Denis's wording
  is closer to Ecclus 41:17]", and mark the verse that fits best (or none).
- A note beside a line shared with the next part belongs to the part in which its clause ends; take it if
  your text holds that clause, and say so in your final message.

## 5. Example
Latin: Ut cognoscas eorum verborum, id est evangelicorum sermonum, de quibus eruditus es per Christi
discipulos, … veritatem, ut scilicet certius pleniusque instruaris. Frequenter autem in Scripturis verbum pro
facto accipitur, ut dum in libris Regum loquitur Ezechias: Non fuit verbum in domo mea, quod non ostenderim eis.

English: [[1:4|That thou mayest … those words|Ut cognoscas eorum verborum]], that is, of the gospel discourses,
[[1:4|in which thou … instructed|de quibus eruditus es]] by the disciples of Christ, … [[1:4|the verity|veritatem]]:
that is, so that thou mayest be more surely and more fully instructed. Now in the Scriptures *word* is often
taken for the deed, as when Ezechias says in the books of Kings: There was not a *word* [that is, a thing] in my
house which I have not shewn them[[Is 39:4||]] [the margin gives Is. xxxix, 2, 4; in the books of Kings the
passage is 4 Kings 20:15].

## 6. Check and hand in
1. Write the test file named in your message: `{"book": "<book>", "chapter": N, "work": "x", "source": "x",
   "num": "<art>", "title": "x", "title_en": "x", "pages": "x", "paras": [ … ]}` and run
   `python3 -c "import sys;sys.path.insert(0,'tools');from expand_quotes import expand_work;expand_work('<test file>')"`.
   It rewrites the file with every marker expanded from the Douay-Rheims and the Latin, or stops naming a
   marker whose anchor is missing or ambiguous: fix it and run again until it succeeds. Then glance at the
   expanded Latin sides: each should be the words Denis quotes, not a longer or wrong stretch of `t`.
2. Write the expanded paragraphs, in order, as a JSON array (`[{"v": …, "t": …, "en": …}, …]`) to your output
   file.
   Write it with `json.dump(..., ensure_ascii=False)` so quotation marks are escaped.
3. Final message: at most 8 short lines on anything uncertain (references that did not fit, readings you
   chose, text lost, a slip you noticed in the Douay-Rheims text). Nothing else.
