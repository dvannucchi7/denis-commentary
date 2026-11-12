# How a translation run works

A run (usually a scheduled task, starting fresh) translates the next article(s) in the queue and
publishes them. Everything needed is in this repository: the OCR'd Latin pages, the Douay-Rheims,
the Vulgate, and the tools. Follow `CLAUDE.md` for every rule of format and style; this file is only
the procedure.

## Steps

1. **Pick the work.** Open `sources/t11/queue.json` (or whichever volume is in progress) and take the
   first item with `"status": "todo"`. Do one article; if it was short (a page or two, as most of Mark
   is) and the run still has room, do the next one too. Never leave an article half done.
2. **Get the Latin.** The OCR text of each PDF page is in `sources/t11/pages/p<NNN>.txt` (left column,
   then right column). Read the pages listed in the item's `pages` range. The article starts at its
   heading (`ARTICULUS …` followed by its title; the heading spans both columns, so in the column text it
   is split into fragments such as `ARTICU` / `US XII`) and ends where the next article's heading begins.
   Running heads, page numbers and the gutter letters A–D are noise. `tools/assemble.py OUT.txt pages…`
   joins pages and removes most of that noise.
3. **Clean the Latin.** Put it in reading order (left column, then right, page by page), rejoin words
   broken across lines, and correct obvious OCR slips (e.g. `eum`→`cum`, `seript`→`script`, `prae`→`præ`,
   commas read as full stops). Do not rewrite Denis's Latin; when unsure, keep what is printed.
4. **Find the chapter and the verses.** The article title says which chapter it treats (e.g.
   *Elucidatio capituli quinti*); `chapter_guess` in the queue comes from running heads and can be off by
   one at chapter boundaries. Print the chapter with `python3 tools/verses.py --chapter matthew 5`.
   Split the article into paragraphs where Denis moves to a new lemma or a new section, and tag each
   paragraph with its verse range (continuous, per `CLAUDE.md`).
5. **Translate** each paragraph into the `en` field, in the agreed style. Mark every direct quotation of
   Scripture with `[[ref|Douay-Rheims wording|Vulgate wording]]`. Look up every reference with
   `python3 tools/verses.py "Ps 26:13" "Rom 12:1" …` and copy the Douay-Rheims words exactly (only the
   part Denis quotes). In a Gospel, a quotation from the chapter being treated is `C:V`; from another
   Gospel it is `Matt`/`Mark`/`Luke`/`John C:V` (shown red); from the Old Testament, blue.
6. **Write the article** as a work file (`work/<id>.json`, format at the top of `tools/add_article.py`)
   and merge it: `python3 tools/add_article.py work/<id>.json`. This also switches the book on in the app.
7. **Check.** `python3 tools/check_quotes.py` must report 0 problems. Fix any quotation that does not
   match the Douay-Rheims, and any gap in the verse tags (or mark a real skip with `"gap_ok": true`).
   Then serve the app (`python3 -m http.server`) and confirm the chapter opens and the article shows.
8. **Publish.** Set the item's status to `"done"` in the queue (add `"note"` if something needs Dave's
   attention, e.g. unreadable text), delete the work file, commit with a message naming the article
   (e.g. "Add Matthew 5, Art. IX"), and push to `main`. The site updates within a few minutes.

If a page's OCR is too damaged to read with confidence, translate what is clear, put `[…]` where text
is missing, set the item's status to `"needs-scan"` with a note giving the PDF page, and move on.
