You are translating, for Dave's app, one article of the scripture commentary of Bl. Denis the Carthusian
(Dionysius Cartusianus, 1402–1471), from the Latin of the *Opera Omnia* (Montreuil, 1896–), into English.
The app shows the Douay-Rheims Bible chapter by chapter with Denis's commentary beneath it, verse by verse,
in English or Latin. You are given: the article's OCR text (already cut at its heading), the images of its
printed pages (two columns per page, scripture references in the outer margins), the references read from
those margins by a program, word-for-word matches found against the Vulgate, and the Douay-Rheims and
Vulgate text of the chapters it may cover. Produce the whole article in one answer, as JSON (format at the end).

## 1. The Latin (`t`)
- The page images are the authority; the OCR text is a convenience. Read every line against the images.
- Put the text in reading order (left column, then right, page by page), rejoin words broken across lines,
  and correct OCR slips (e.g. eum→cum, seript→script, prae→præ, commas read as full stops). Restore any
  line the OCR dropped or garbled from the image. Keep Denis's own Latin, spelling and punctuation as
  printed (æ, œ, j, quum…); do not normalize or rewrite it.
- The article starts at its heading (ARTICULUS …, with its Latin title) and ends where the next
  article's heading begins. The first and last pages are shared with the neighbouring articles: leave
  their text out. Leave out running heads, page numbers, the gutter letters A–D and marginal notes.
- Only where a word truly cannot be read in the image either, put […] and say so in `unreadable`.

## 2. Paragraphs and verse tags (`v`, `ch`)
- Split the article where Denis moves to a new lemma (a new piece of the verse he expounds) or a new
  section (e.g. *Mystice*, *Moraliter*). Each paragraph gets `ch` (the chapter it treats) and
  `v: [first, last]` (the verses it covers). The article's title says which chapter it treats
  (*Enarratio capituli decimi* …); an article may run on into the next chapter.
- If Denis reads straight through, the tags must be continuous with no gaps, even where a verse is not
  explicitly discussed (4–8, 9–13, not 4, 9). Repeat or overlap only where he really does (a verse split
  across paragraphs, a digression on one verse, going back to a verse). A gap is allowed only where he
  himself skips or jumps out of order: mark that paragraph `"gap_ok": true`.
- The bare numbers in the outer margin (e.g. "15") mark where each verse of the chapter treated begins;
  use them.

## 3. The English (`en`): style
- Faithful but readable English. Keep Denis's structure: the lemma, then his gloss ("that is, …").
  Keep "etc." where he abbreviates a quotation. Keep his spellings of names and of the Hebrew, Greek or
  Syriac forms he gives. Biblical names as in the Douay-Rheims (Isaias, Jeremias, Elias, Osee…).
  Translate the Church Fathers and Doctors he cites in plain English (Augustine, Jerome, Chrysostom, Bede,
  Gregory, Ambrose, Remigius, Thomas, Lyra, the Gloss, Damascene…).
- Translator's notes go in square brackets, sparingly, only where they help: technical theological terms
  ("officious lie [that is, a lie told to avert harm, not a malicious one]"), and wordplay or a point of
  the Latin lost in English. Dave likes these notes. Write each note as at least four characters inside
  the brackets. Never use square brackets for anything else (except […] for unreadable text).
- `title_en`: the English of the article's Latin title.

## 4. Quotations of Scripture: markers
Every direct quotation of Scripture is wrapped in a marker, in the `en` text, in **shorthand**:

    [[REF|first words … last words|first words … last words]]

- REF is `C:V` for the book treated (e.g. `10:3`), or `Abbr C:V` for any other book, with the abbreviations
  below and Vulgate numbering (Psalms as in the Vulgate; 1–4 Kings = 1–2 Samuel and 1–2 Kings).
- The second field: two or three words from the start and the end of the quoted words *as they stand in
  the Douay-Rheims verse* (given below for the chapters treated), joined by " … ". The third field: the same
  from Denis's Latin. A program fills in the exact wording from the Douay-Rheims and from Denis's Latin,
  and checks it, so the anchors must be the Douay-Rheims's own words, in its order, and must pick out one
  place in the verse (if a word occurs twice, give more words). `*` means the whole verse
  (`[[10:5|*|*]]`). Short quotations can be written out in full instead (`[[10:5|Peace be to this house|Pax huic domui]]`).
- The English around a marker must read naturally: the marker *replaces* your translation of those words;
  the reader sees the Douay-Rheims wording there.
- One marker per verse: a quotation running over two verses gets two markers.
- **Lemmata** (Denis quoting the chapter he treats, before glossing it) are always marked, as `C:V`.
- **Quotations from elsewhere**: mark every one for which the printed margin gives a reference (see
  the margin list and the images: the book is almost always read right by the program, the small
  numerals often not, so confirm the verse against the Latin beside the note and the verse text). Also
  mark any *obvious* quotation the margin does not give: one Denis introduces with its source ("as the
  Apostle says", "in the Psalm", "Isaias:"), or one that is word for word at length (the word-for-word
  match list helps). Do not hunt for short or loose phrases with no margin note; leave them plain.
- Where the margin gives a reference but Denis does not quote the words (he retells a story, names an
  event, alludes), put a **reference-only marker** with both fields empty straight after the clause it
  belongs to, with no space: `…went out to the king of Babylon[[4 Kings 24:12||]]`. Every margin reference
  that belongs to the article ends up as either a quotation marker or a reference-only marker.
- If something is uncertain (the margin reference does not fit, is unreadable, or Denis's words are closer
  to another verse), add a bracketed note at that place saying so, e.g. "[the margin gives Ecclus. xx, 32;
  Denis's wording is closer to Ecclus 41:17]", and mark the verse that fits best (or none).
- In a Gospel commentary, a quotation of the Gospel treated is `C:V`; of another Gospel `Matt`/`Mark`/
  `Luke`/`John C:V` (where the same words are in several Gospels, use the one the margin names).
- A margin note citing only a chapter (Gen. xlix) is given as verse 1 of that chapter.

Abbreviations (use exactly these): ABBREVIATIONS

## 5. Example (from Luke 1, Art. II; shorthand as you should write it)
Latin: Ut cognoscas eorum verborum, id est evangelicorum sermonum, de quibus eruditus es per Christi
discipulos, vel sola instructione vocali, vel etiam per evangelia Matthæi et Marci jam scripta (quæ
forsitan vidit, quamvis hoc certum non sit), veritatem, ut scilicet certius pleniusque instruaris de
Christi verbis et factis atque mysteriis. Frequenter autem in Scripturis verbum pro facto seu re
significata per verbum accipitur, ut dum in libris Regum loquitur Ezechias: Non fuit verbum in domo mea,
quod non ostenderim eis.

English: [[1:4|That thou mayest … those words|Ut cognoscas eorum verborum]], that is, of the gospel
discourses, [[1:4|in which thou … instructed|de quibus eruditus es]] by the disciples of Christ, either by
spoken instruction alone, or also through the gospels of Matthew and Mark already written (which perhaps
he had seen, though this is not certain), [[1:4|the verity|veritatem]]: that is, so that thou mayest be
more surely and more fully instructed about the words, deeds and mysteries of Christ. Now in the
Scriptures *word* is often taken for the deed, or the thing signified by the word, as when Ezechias says
in the books of Kings: There was not a *word* [that is, a thing] in my house which I have not shewn
them[[Is 39:4||]] [the margin gives Is. xxxix, 2, 4, where Isaias has *verbum* in this sense at 39:2; in
the books of Kings the passage is 4 Kings 20:15].

## 6. Answer format
Think it through as much as you need, then end your answer with one JSON object in a ```json block, and
nothing after it:

```json
{
  "num": "XXVI",
  "title": "Latin title as printed (after ARTICULUS XXVI)",
  "title_en": "English title",
  "pages": "pp. 2–9",
  "unreadable": ["describe any text you could not read even in the image, with its page; else empty"],
  "paras": [
    {"ch": 10, "v": [1, 1], "t": "Latin of the paragraph", "en": "English with shorthand markers"},
    {"ch": 10, "v": [2, 4], "t": "…", "en": "…"}
  ]
}
```
`pages` are the printed page numbers (shown in the page images' running heads; also given below).
Use `"gap_ok": true` on a paragraph only for a deliberate skip. Escape quotation marks inside strings
properly (or use “curly” quotes in the English). The JSON must be complete and valid.
