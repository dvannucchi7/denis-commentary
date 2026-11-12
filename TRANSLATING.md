# How a translation run works

A run (usually a scheduled task, starting fresh) translates the next article(s) in the queue and
publishes them. Everything needed is in this repository: the OCR'd Latin pages, the Douay-Rheims,
the Vulgate, and the tools. Follow `CLAUDE.md` for every rule of format and style; this file is only
the procedure.

## Steps

1. **Pick the work, and keep going.** Note the time when the run starts (`date -u`). Work through the
   queues in order: `sources/t11/queue.json` first, then `sources/t12/queue.json`. Take the first item
   whose status is `"todo"`, or `"in-progress"` with a `claimed` time more than 2 hours old (an
   abandoned run). **Claim it before starting:** set `"status": "in-progress"` and
   `"claimed": "<UTC time>"`, commit ("Claim matthew-10"), `git pull --rebase origin main`, push. If the
   push fails or someone else claimed it meanwhile, pull and take the next item. Then translate it.
   **Publish each article as soon as it is finished** (steps 6–8), then go straight on to the next item.
   Keep going until about **45 minutes** after the run started; do not begin a new article after about
   40 minutes. Never leave an article half done: if you must stop mid-article, set it back to `"todo"`
   and push, so the next run takes it.
2. **Get the Latin.** If `sources/<vol>/articles/<id>.txt` exists, start from it: it is that article's
   OCR text already cut at the article headings and joined in reading order. Otherwise read the OCR
   pages `sources/<vol>/pages/p<NNN>.txt` in the item's `pages` range (sections marked LEFT / RIGHT /
   HEADING, in reading order). The article starts at its heading (`ARTICULUS …` and its title) and ends
   where the next article's heading begins. `tools/assemble.py OUT.txt pages…` joins pages and removes
   running heads, page numbers and the gutter letters A–D.
3. **Clean the Latin.** Put it in reading order (left column, then right, page by page), rejoin words
   broken across lines, and correct obvious OCR slips (e.g. `eum`→`cum`, `seript`→`script`, `prae`→`præ`,
   commas read as full stops). Do not rewrite Denis's Latin; when unsure, keep what is printed.
4. **Find the chapter and the verses.** The article title says which chapter it treats (e.g.
   *Elucidatio capituli quinti*); `chapter_guess` in the queue comes from running heads and can be off by
   one at chapter boundaries. Print the chapter with `python3 tools/verses.py --chapter matthew 5`.
   Split the article into paragraphs where Denis moves to a new lemma or a new section, and tag each
   paragraph with its verse range (continuous, per `CLAUDE.md`).
5. **Translate** each paragraph (before you start, `python3 tools/find_quotes.py <article.txt> <book>
   <chapter>` lists the places where Denis quotes the chapter, with the Douay-Rheims and Vulgate wording
   ready to paste; check them, and look up any other quotations yourself) into the `en` field, in the agreed style. Mark every direct quotation of
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
   (e.g. "Add Matthew 5, Art. IX"), then `git pull --rebase origin main` (someone else may have pushed
   meanwhile) and push to `main`. The site updates within a few minutes.

If a page's OCR is too damaged to read with confidence, translate what is clear, put `[…]` where text
is missing, set the item's status to `"needs-scan"` with a note giving the PDF page, and move on.
