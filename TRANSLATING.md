# How a translation run works

A run (usually a scheduled task, starting fresh) translates the next article(s) in the queue and
publishes them. Everything needed is in this repository: the OCR'd Latin pages, the Douay-Rheims,
the Vulgate, and the tools. Follow `CLAUDE.md` for every rule of format and style; this file is only
the procedure.

## Steps

1. **Pick the work, and keep going.** Note the time when the run starts (`date -u`). Work through the
   queues in order: first the re-checks in `sources/t11/recheck.json` (see "Re-checking a published
   article" below), then `sources/t11/queue.json`, then `sources/t12/queue.json`. Take the first item
   whose status is `"todo"`, or `"in-progress"` with a `claimed` time more than 2 hours old (an
   abandoned run). Skip `"needs-margins"` items until their margins have been read (see step 5). **Claim it before starting:** set `"status": "in-progress"` and
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
5. **References come from the margins only (Dave's rule).** The printed edition gives the source of
   each quotation in the margin; that is the only place a run takes references from.
   - `python3 tools/margins.py <vol> <id> <chapter>` lists the margin references of the article's
     pages, in reading order, each beside the Latin line it belongs to. Ignore notes on the first and
     last pages that belong to the neighbouring articles. Bare verse numbers in the margin show where
     each verse of the chapter treated begins (use them for the verse tags).
   - **References come from the margin, but obvious quotations must not be missed** (Dave). Take
     every reference the margin gives. Then also tag any *obvious* quotation the margin reader did not
     catch: one Denis introduces with its source ("as the Apostle says", "in the Psalm", "Isaias:"),
     or one that is word for word at length. To make sure none is missed, run
     `python3 tools/recheck.py <vol> <id>` on the merged article (step 7): it lists `obvious` runs of 6
     or more words matching a verse anywhere in the Vulgate, and `lemma?` runs of 4 or more words of
     the chapter treated, that are not yet tagged. Tag each one that is a real quotation (pick the
     verse Denis names where the words occur in several places). Do not go fishing for short or loose
     phrases (the old whole-Bible part of `find_quotes.py` is not used): anything that is neither in the
     margin nor obvious stays plain text. A margin note citing only a chapter (Gen. xlix) is given as
     verse 1 of that chapter.
   - **For each margin reference, work out the verse.** The book is almost always read right, the
     small numerals often not. Look the verse up with `python3 tools/verses.py "Ps 26:13" …` and
     confirm it against the Latin beside the note; if the numerals were misread, find the verse within
     the book the margin names. The tool's `corrected` entries are only suggestions: check them (they
     can be wrong where the printed reference was right). `allusion?` means the Latin beside it does not
     match the verse word for word: usually an allusion or a story told in Denis's own words (a
     reference-only marker, below), sometimes a misread reference (find the right verse in that book).
   - **Where Denis quotes the words, tag the quotation; where he does not** (he retells a story, names
     a person or event, or alludes), put a reference-only marker after the clause the margin note
     stands beside: `…went out to the king of Babylon[[4 Kings 24:12||]]`. Every margin reference that
     belongs to the article ends up as one or the other.
   - **If there is any confusion, add a note in the article** at that place, as a translator's note
     in square brackets, saying what the margin prints and what is uncertain, e.g. "[the margin gives
     Ecclus. xx, 32; Denis's wording is closer to Ecclus 41:17]" or "[the margin reference is
     unreadable; the words are those of Is 66:1]". Tag the verse that best fits, or leave the
     quotation untagged if none does.
   - Lemmata (Denis quoting the chapter he is treating) are still marked as before, as `C:V`. Find
     them by reading the article alongside the chapter (`python3 tools/verses.py --chapter …`) and the
     margin's verse numbers, not by matching the article against the Vulgate.
   - **If the margins of the article's pages have not been read yet** (`margins.py` prints "margins
     of PDF … not read yet"), do not translate it: set its status to `"needs-margins"` with a note
     giving the PDF pages, push, and take the next item. Reading margins needs the scan PDF, which
     runs do not have; Dave reads them (`python3 tools/margins.py read <vol> <pdf> <first> <last>`).
   Translate each paragraph into the `en` field, in the agreed style, marking the quotations as above.
   **Write the markers in shorthand; do not copy out the wording:**
   `[[Ps 44:8|hath anointed … fellows|Unxit te … tuis]]`: the reference, then two or three words from
   the start and end of the quoted part in the Douay-Rheims, then the same in Denis's Latin. `*` means
   the whole verse (`[[5:3|*|*]]`). `tools/add_article.py` fills in the exact Douay-Rheims and the Latin
   (Denis's own wording where he quotes a variant) and stops with a message if an anchor is not found
   or is ambiguous; then add a word or two, or write that side out in full (always allowed). A quotation
   running over two verses gets one marker per verse. In a Gospel, a quotation from the chapter being
   treated is `C:V`; from another Gospel it is `Matt`/`Mark`/`Luke`/`John C:V` (shown red); from the Old
   Testament, blue.
6. **Write the article** as a work file (`work/<id>.json`, format at the top of `tools/add_article.py`)
   and merge it: `python3 tools/add_article.py work/<id>.json`. It first expands the shorthand markers
   (if it stops on an anchor, fix that marker and run it again); it also switches the book on in the app.
7. **Check.** `python3 tools/check_quotes.py` must report 0 problems. Fix any quotation that does not
   match the Douay-Rheims, and any gap in the verse tags (or mark a real skip with `"gap_ok": true`).
   Run `python3 tools/recheck.py <vol> <id>` and deal with every `obvious`, `lemma?`, `untagged` and
   `differs` line (step 5); re-run until only deliberate leftovers remain. Then serve the app (`python3 -m http.server`) and confirm the chapter opens and the article shows.
8. **Publish.** Set the item's status to `"done"` in the queue (add `"note"` if something needs Dave's
   attention, e.g. unreadable text), delete the work file, commit with a message naming the article
   (e.g. "Add Matthew 5, Art. IX"), then `git pull --rebase origin main` (someone else may have pushed
   meanwhile) and push to `main`. The site updates within a few minutes.

## Re-checking a published article

Articles published before the margin rule (step 5) are brought into line with it, in the order of
`sources/t11/recheck.json` (Matthew from Art. I, then Mark). Claim, time limits and publishing are as in
steps 1 and 8 (commit "Re-check Matthew 1, Art. I"). Skip `"needs-margins"` items.

1. `python3 tools/recheck.py t11 <id>` compares each paragraph's references from outside the chapter
   treated with the margin references beside it. If it says margins are not read for some pages, set
   the item to `"needs-margins"` (note the PDF pages) and take the next one.
2. `python3 tools/recheck.py --export t11 <id>` writes the article to `work/<id>-ch<N>.json` (two files if
   it runs over two chapters). Edit the `en` fields there:
   - `ok`: nothing to do.
   - `differs`: the margin names the same book but another verse. Work out which is right from the
     Latin (the margin's numerals are often misread; the tool's reading of them can be wrong too) and
     fix the reference; if it stays unclear, add a bracketed note.
   - `no-margin`: tagged, but no margin reference for that book beside it. First look at the `unread`
     and oddly read notes beside the same paragraph (a misread book name, e.g. "1 Mach" for
     *Malach.*); if one of them is its reference, keep the tag. The margin reader misses some notes,
     so (Dave's decision) **keep a tag whose words are quoted word for word** and list it in the item's
     `"note"` as unconfirmed ("no margin note read: Gen 15:1, …"), to be checked against the scan. Untag
     it (keep the words as plain text) only where the margin gives a different reference for that spot,
     or where the words are not the verse's own.
   - `untagged`: a margin reference with no tag. Find the place from the Latin beside it. If Denis quotes
     the words, tag them; if not, add a reference-only marker `[[ref||]]` after that clause. If no verse
     of that book fits, add a bracketed note giving the margin's reading.
   - `unread`: an unreadable margin note: see what Denis quotes or tells there and treat it as above if
     the verse can be found with confidence; otherwise leave it.
   - `obvious` / `lemma?`: an untagged word-for-word quotation (6+ words from elsewhere, 4+ from the
     chapter treated). Tag it if Denis is quoting (choose the verse he names where the words occur in
     several books); leave it if the words only happen to coincide (a name, a stock phrase).
   Leave lemmata (quotations of the chapter treated) and the translation itself as they are.
3. Merge each work file with `python3 tools/add_article.py work/<id>-ch<N>.json` (it replaces the
   article), run `tools/recheck.py` again (what is left should be only what you decided to leave), then
   `python3 tools/check_quotes.py` (0 problems) and check the chapter in the app.
4. Set the item to `"done"` in `recheck.json` (with a `"note"` for anything Dave should see), delete the
   work files, commit, pull, push.

If a page's OCR is too damaged to read with confidence, translate what is clear, put `[…]` where text
is missing, set the item's status to `"needs-scan"` with a note giving the PDF page, and move on.
