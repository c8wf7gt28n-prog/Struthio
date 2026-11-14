"""One invitation for writing; retain each field's purpose as supporting help."""
PROMPT = 'prompt'      # 0.8.1, the owner: "Let's lose the term poem. Come up with something a little bit more Lain, hacker, old school. Maybe just prompt."


def writing_prompt(widget, hint=''):
    """Set a placeholder, never document content or a field's semantic label."""
    if widget.isReadOnly():
        widget.setPlaceholderText(hint)
        return
    previous=widget.property('poemHint')
    widget.setProperty('poemHint',hint)
    for read,write in ((widget.toolTip,widget.setToolTip),
                       (widget.accessibleDescription,widget.setAccessibleDescription),
                       (widget.accessibleName,widget.setAccessibleName)):
        if not read() or read()==previous:write(hint)
    widget.setPlaceholderText(PROMPT)
