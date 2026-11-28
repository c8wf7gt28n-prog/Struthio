"""Graphite 1.1 N1duo · Night: Duo, her tube: her column seen through amber.

The owner, 28 Nov 2026: "both the orange and green working together with grey (like screen burns)". In Night: Duo green is
the computer and amber is Kas and the owner's word (design_tokens._duo_colours). Her column draws itself from boss_theme's
roles (TEXT, QUIET, READY, ...), which are the computer's green in Duo. Here her column is handed a view of boss_theme in
which the roles of words and of her state are amber, so her panel reads as a second, amber tube beside the green one. The
grey of the past (FAINT, the lines) and every other role are boss_theme's own, read at the moment they are asked for. In any
other look her column gets boss_theme itself. Sections built from boss_theme directly are put in amber when her column
comes into her panel (amber_words).
"""
from __future__ import annotations

from . import design_tokens as tokens

# role -> the token it is in her tube (Night: Duo only)
HER_ROLES = dict(TEXT='kas_text', QUIET='kas_quiet', READY='kas_text', TEAL='kas_text', TEAL_EDGE='kas_text', TEAL_TEXT='kas_text',
                 TEAL_SOFT='waiting_tint', CUE='waiting_tint', CUE_EDGE='kas_text', CUE_TEXT='kas_text', ROYAL='kas_text',
                 ROYAL_INK='kas_text', ROYAL_TEXT='kas_text', ROYAL_SOFT='waiting_tint', PANEL='kas_ground', VIOLET='kas_quiet',
                 VIOLET_PALE='kas_text', ERASED='kas_text', ERASED_QUIET='kas_quiet')


class HerTube:
    """boss_theme as her column sees it in Night: Duo: the roles in HER_ROLES amber, every other name boss_theme's own."""

    def __init__(self, theme, colours):
        self.__dict__['_theme'] = theme
        self.__dict__['_over'] = {role: colours[key] for role, key in HER_ROLES.items()}

    def __getattr__(self, name):
        over = self.__dict__['_over']
        return over[name] if name in over else getattr(self.__dict__['_theme'], name)

    def __setattr__(self, name, value):
        setattr(self.__dict__['_theme'], name, value)


def her_theme(theme):
    """Her column's boss_theme: HerTube in Night: Duo, else the theme itself."""
    if not getattr(theme, 'PHOSPHOR', ''):return theme
    c = tokens.colours('night')
    return HerTube(theme, c) if tokens.is_duo(c) else theme


def amber_words(panel, c=None):
    """Night: Duo: what her panel holds that was styled in the computer's green (a section built from boss_theme itself) is
    put in her amber: each style sheet's green words become her words, its green tint her tint. Called when her column comes
    into the panel and each time the panel opens. Returns how many widgets changed; nothing outside Duo."""
    c = c or tokens.colours('night')
    if not tokens.is_duo(c):return 0
    from PySide6.QtWidgets import QWidget
    swaps = ((c['text'], c['kas_text']), (c['secondary'], c['kas_quiet']), (c['live_tint'], c['waiting_tint']))
    changed = 0
    for widget in [panel] + panel.findChildren(QWidget):
        sheet = widget.styleSheet()
        if not sheet:continue
        new = sheet
        for green, amber in swaps:new = new.replace(green, amber).replace(green.upper(), amber)
        if new != sheet and widget is not panel:
            widget.setStyleSheet(new);changed += 1
            ink = widget.property('herInk')
            if ink:
                for green, amber in swaps:ink = str(ink).replace(green, amber).replace(green.upper(), amber)
                widget.setProperty('herInk', ink)
    return changed
