# Live page trial (HATCH AGENT-02)

November 6, 2026 · UTC · the build container, CPU runtime b11669, not the owner host.

`tools/model_trial_page.py` (integrator tool, not shipped) registered each GGUF file through `brain.model.add` and `brain.model.use`, created a three-paragraph page through `documents.create`, asked `brain.ask` in plan mode with the words an open page gives the model (`document_qt.slate_context`, with AGENT-02's hint line), and applied what came back exactly as the desktop does: `model_turn.decide` against the page, then `documents.edit` with origin `SLATE_MODEL`. The reports are in `build/agent02_ui/model_trial/`, and the two earlier stages are under `history/`.

## What the trial found

Before the fix, both small models filled every optional key of the change under schema-constrained decoding. A "make it bold" proposal arrived as bold plus "replace with nothing" plus an empty new paragraph. The page applied it by itself and deleted the selected words; with the 0.5B model "lazy" became "Normal". It was undoable, but a model turn must never destroy words by itself. The canned offscreen check could not have found this.

| Model | Request | Proposed change | What the page did | Seconds |
| --- | --- | --- | --- | --- |
| Qwen2.5-0.5B | bold selected words | `knowledge.page` | not applied: only an edit of the open page (documents.edit) applies by itself; knowledge.page waits for Run | 13.6 |
| Qwen2.5-0.5B | heading on the caret paragraph | `{"bold": true, "italic": true, "underline": true, "style": "Normal", "replace": "Normal", "append": "Normal"}` | not applied: it changes words but its selection holds none; select the words first | 12.1 |
| Qwen2.5-0.5B | replace a word | `{"bold": true, "italic": true, "underline": true, "style": "Normal", "replace": "Normal", "append": "Normal"}` | applied: made “lazy” bold and made “lazy” italic and made “lazy” underline and made the paragraph body text and replaced “lazy” with “Normal” and added the paragraph “Normal” after paragraph 1 | 12.0 |
| Qwen2.5-1.5B | bold selected words | `{"bold": true, "italic": false, "underline": false, "style": "Normal", "replace": "", "append": "", "append_style": "Normal"}` | applied: made “quick brown” bold and removed italic from “quick brown” and removed underline from “quick brown” and made the paragraph body text and replaced “quick brown” with “” and added the paragraph “” after paragra | 21.1 |
| Qwen2.5-1.5B | heading on the caret paragraph | `{"append": "", "append_style": "Normal"}` | not applied: the words it quotes (“quick brown”) are not at that place on the page | 21.1 |
| Qwen2.5-1.5B | replace a word | `{"append": "", "append_style": "Normal"}` | not applied: its selection reaches past paragraph 1 | 21.1 |

## The fix, and what its independent review found

The first fix narrowed the model's form of `documents.edit` to one kind of change and made `decide` set aside filled-in no-ops and refuse mixed kinds. Two read-only reviewers then measured it live and found more. With one optional marks object, the 1.5B model answered everything with a body-text style and the 0.5B model switched every mark on. The deletion guard checked only that something was selected, not which words. A paragraph change could land one paragraph off. At the default 2,048-token context, every page request failed before the model answered, because the plan prompt was too large.

| Model | Request | Proposed change | What the page did | Seconds |
| --- | --- | --- | --- | --- |
| Qwen2.5-0.5B | bold selected words | `{"bold": true, "italic": false, "underline": false}` | applied: made “quick brown” bold | 12.1 |
| Qwen2.5-0.5B | heading on the caret paragraph | `{"bold": true, "italic": false, "underline": false}` | not applied: it names paragraph 4 and the page has 3 | 18.1 |
| Qwen2.5-0.5B | replace a word | `{"bold": true, "italic": false, "underline": false}` | applied: made “lazy” bold | 13.6 |
| Qwen2.5-1.5B | bold selected words | `{"style": "Normal"}` | applied: made the paragraph body text | 18.1 |
| Qwen2.5-1.5B | heading on the caret paragraph | `{"style": "Normal"}` | not applied: its selection reaches past paragraph 3 | 19.6 |
| Qwen2.5-1.5B | replace a word | `{"style": "Normal"}` | applied: made the paragraph body text | 22.6 |

The final rules:
- The model is offered one alternative per kind: bold, italic, underline, a paragraph style, replace, append or clear, with that key required, and no empty replacement or paragraph.
- `decide` sets aside what rides along, and applies one kind and one mark at a time.
- Words are replaced or deleted by themselves only when they are the owner's own selection.
- A style or added paragraph applies by itself only on the owner's paragraph, and a style the paragraph already has is no change.
- Anything else waits for Run, and the card says why.
- A request about an open page is offered only the page's operations and at most two small chosen ones, so it fits the default context.

## Final run, at the default 2,048-token context

| Model | Request | Proposed change | What the page did | Seconds |
| --- | --- | --- | --- | --- |
| Qwen2.5-0.5B | bold selected words | `{"bold": true}` | applied: made “quick brown” bold | 7.5 |
| Qwen2.5-0.5B | italic selected words | `{"bold": true}` | applied: made “lazy” bold | 9.1 |
| Qwen2.5-0.5B | remove the bold | `documents.interpret` | not applied: only an edit of the open page (documents.edit) applies by itself; documents.interpret waits for Run | 7.5 |
| Qwen2.5-0.5B | heading on the caret paragraph | `{"bold": true}` | not applied: it changes words but its selection holds none; select the words first | 9.0 |
| Qwen2.5-0.5B | replace a word | `{"bold": true}` | applied: made “lazy” bold | 9.1 |
| Qwen2.5-0.5B | words the rules do not know | `{"bold": true}` | applied: made “quick brown” bold | 9.0 |
| Qwen2.5-1.5B | bold selected words | `{"bold": true}` | applied: made “quick brown” bold | 13.6 |
| Qwen2.5-1.5B | italic selected words | `{"style": "Normal"}` | not applied: once what changes nothing is set aside (paragraph 1 is already body text), it changes nothing | 15.1 |
| Qwen2.5-1.5B | remove the bold | `{"bold": false}` | applied: removed bold from “quick brown” | 15.1 |
| Qwen2.5-1.5B | heading on the caret paragraph | `documents.interpret, documents.save` | not applied: only an edit of the open page (documents.edit) applies by itself; documents.save waits for Run | 16.6 |
| Qwen2.5-1.5B | replace a word | `{"replace": "sleepy"}` | applied: replaced “lazy” with “sleepy” | 15.1 |
| Qwen2.5-1.5B | words the rules do not know | `{"bold": false}` | applied: removed bold from “quick brown” | 15.1 |

- Qwen2.5-0.5B: 4 of 6 requests applied by themselves; every word of the page is as it was (marks aside).
- Qwen2.5-1.5B: 4 of 6 requests applied by themselves; the words changed only here: paragraph 1 “The quick brown fox jumps over the lazy dog.” → “The quick brown fox jumps over the sleepy dog.”.

## What this means for the owner

Nothing a small model proposes can now delete or add words on the page by itself, and everything that does apply is visible, glows, and goes back with one undo. The small models still pick the wrong kind of change for some requests. The direct rules handle bold, italic, underline, headings, body text and "replace x with y" without any model, so the model path matters for requests the rules do not know. On the ThinkPad, the 1.5B file stays the default to qualify.
