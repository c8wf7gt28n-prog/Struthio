# What's new in Graphite 0.4.3

November 13, 2026. Guide → What's New opens this page. The 0.4.2, 0.4.1, 0.4, 0.3.1 and 0.3 notes beside it describe what
came before.

0.4.2 taught Stacy to doubt a result. This release is four things built on that: the desk looks ahead before you change a
number, it catches more of the traps in the owner's 35 situations, it writes itself up as a page, and it takes your own
words for the staC lines you use. No model is asked for any of it.

**What if, followed along the wires.** Select a sheet or a calculation in the Field and ask in the writing line: "what if
B4 were 100?", or by the row's own words, "what if the pulse duration were 100?". Stacy sets that cell to that value
without changing anything, follows the wires, and says for everything downstream what it says now and what it would say:

- every calculation that reads the cell, worked again exactly with its own recipe;
- every finding and page whose words carry a number that would move: the cell's own value, a calculation's result, or a
  number made from two of the desk's values ("30 ms is 110 ms less 80 ms; it would be 10 ms");
- a cell on the same sheet whose words repeat the old value and that nothing rewrites;
- every check that reads the sheet: its own program is run on the sheet as it would be and its own expectation applied,
  so "would fail" and "would go on passing without noticing" are what the check itself would say;
- the other calculations of the sheet, whose result would not move but which a saved change sends to recheck.

The Field marks each thing that would move with a broken amber edge and the words of what it would say. The marks stay
while you move among the sheets; **Esc** clears them. In staC:
`field.ripple {"id":"office:…","set":{"B4":"100"}} | pick rows | select way,title,says_now,would_be,why`.

**More traps caught.** The doubt (X, and the desk check on C) has new exact questions:

- **Counted twice** (situation 07): a total that adds a subtotal together with the rows the subtotal already adds, found by
  arithmetic on the numbers as they stand, for typed values and for an imported spreadsheet's kept formula results alike.
  "B6 (Total) adds B2 to B5, and B4 (Parts subtotal) is already B2 to B3 added up. Without B4 the total is 70, not 135."
  When the inner row does not call itself a total, it is named as something Stacy cannot tell, not as a doubt.
- **The same digits under another unit** (situations 15 and 18): quantities are now compared in their base units, so
  "3360 mW" is the same as a 3.36 W result and holds, and "3.36 mW" beside a 3.36 W result is a doubt.
- **A number made from two others**: "30 ms" on no sheet is said to be 110 ms less 80 ms, with the cells; the working is
  still not recorded, and that is said too.
- **Another sheet differs** (situation 16): the same parameter by name on another sheet with another value is a note on
  both: whatever uses it has to say which sheet it means.
- **A page** can now be doubted: every quantity in its words against the desk.
- **A check on a page that was replaced**: a check that reads a calculation's page goes on reading the old page after the
  calculation is worked again. That is now a doubt on the finding.

**B: the brief.** Press **B** in the Field. Stacy reads the whole desk and shows it written up as one page: what stands
and on what, what waits for you, what she doubts, what she cannot tell, the numbers with their cells, and where it all
comes from. Every line is read from a record. Keeping it as a page is a change, so it waits for **G**; the go keeps what
you were shown, and if the desk changed in between nothing is kept. The kept brief is a page like any other, to edit,
export or print, and it sits on the Field. When the desk changes it shows as waiting, and writing it again (D, or
settling the desk on C) puts a new page in its place; the earlier one stays in Documents. If you edit a brief, X says some
of its lines are now yours.

**Your own staC words.** Keep a line under a word of your own and the word is the line from then on:

    word waits = field.read | pick waiting | select kind,title,state
    waits
    waits | where kind=finding | count
    explain waits
    word waits        shows what it stands for
    words             lists them
    forget waits

A word is written out before it runs, so the answer and the history always say the whole line. It can only be a staC read
(the language's parser decides), so a word can never do what a line could not. A word may be built on another word and may
start with `this`. Words are records of the workspace: `words.list`, `words.keep`, `words.forget`. The Field's menu lists
them under "This face in staC".

**Backspace: where I was.** In the Field, Backspace goes back to the sheet you were on before this one, and the one
before that.

**The right-click menu cascades into all of it.** Right-click a sheet in the Field (or press the Menu key):

- **What if ›** lists its numbers, each with its cell, its words and its value, and under each the values worth trying:
  10 % more, 10 % less, twice, half, or another value to finish in the line. Two moves, and the Field shows what would
  move.
- **Doubt it ›** shows what Stacy finds right in the menu, worst first. A row's reason is its tooltip; choosing a row shows
  the read that is its evidence. The first row is the whole of it in Talk, as X gives it.
- **Trace it ›** lists where the sheet comes from and what rests on it; choosing one goes there.
- **What can be done ›** lists the steps D offers. A read runs; a change is put up in Talk and waits for **G**. Choosing in
  a menu never approves anything.
- **Your words ›** runs one of your own words here; a word whose line starts with `this` reads this sheet.

On an empty place of the Field the menu has The brief and Your words, where a word can also go to the line, be forgotten,
or a new one be started.

**Put right from 0.4.2 and 0.4.1.** A second set of readers went through the code while this was built, and these were
theirs:

- "What if" on a calculation whose recipe reads one cell under two symbols set only one of them. Naming the cell now sets
  both.
- "Check it against" a calculation bound a check that no wire showed and no look at the sources could see. It is now bound
  to the page by its address, so the finding is wired to the calculation.
- A sheet brought in from a file that has not changed was doubted as if its source had. It holds now; a file that cannot
  be reached is named as something Stacy cannot tell.
- "It says 3.36 W" was a match of letters, so "13.36 W" matched. It is now a match of the whole number.
- Two small numbers in base units (1 nA and 2 nA) could be taken for the same number. The allowance is now relative.

**Not done, said plainly.** Nothing here has run on the ThinkPad; all of it was checked offscreen in a build container.
The ripple follows what the records tie together and no more: a finding that compares in words ("allows 6 W") is not
worked again, totals bound to a page's words and Agenda watches are not followed, and its match of a finding's number to a
cell is a match of the quantity, so words that say the same number for another reason are listed too. The counted-twice
rule reads one column of the first sheet and takes an imported file's kept numbers as they are; Graphite does not work
formulas again. The brief leaves out lines past 24 in each part and says how many. A kept brief is not wired to the things
it cites. Words are expanded where a line is typed (the writing strip and Talk), not inside a line kept elsewhere.
Still nothing about a footnote on a page, or any situation that reaches outside the computer.
