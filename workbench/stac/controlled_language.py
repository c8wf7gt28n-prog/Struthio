"""staC 0.4: *controlled English* -> typed staC IR, not neural translation.

This intentionally tiny, exact template recognizer demonstrates equivalent
human phrasings becoming the same IR. Unrecognized requests are rejected, not
'understood' by guessing. The model-independent IR is compiled but not run.
"""
from __future__ import annotations

import re
from .language import compile_text, intent_hash, CompileError

LANGUAGE = 'en-arc-controlled/0.1'
SCHEMA = 'arc.stac.controlled/0.4'
BASE = 'use ARC1@R10 | part {ref} | fact {property}'
# English surface forms are deliberately finite and reviewable.
# Full matches; no partial search, shell escaping, arbitrary parameters or file IO.
AT = r'(?:in|on)\s+ARC(?:-|\s*)1\s+R10'
REF = r'(?P<ref>[A-Za-z][A-Za-z0-9_]{0,39})'
PROP = r'(?P<property>[A-Za-z][A-Za-z0-9_]{0,63})'
NUM = r'(?P<number>\+?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?(?:us|µs|μs|ns|ms|s))'
TEMPLATES = (
    ('SPEC_SOURCE', 'why', re.compile(rf'(?i)what\s+is\s+the\s+{PROP}\s+specification\s+for\s+{REF}\s+{AT}\??')),
    ('SPEC_SOURCE', 'why', re.compile(rf'(?i)show\s+(?:me\s+)?sources\s+for\s+{REF}\s+{PROP}\s+{AT}\.?')),
    ('PROOF_OBLIGATIONS', 'question | obligations', re.compile(rf'(?i)what\s+evidence\s+is\s+missing\s+(?:to\s+assess\s+|for\s+){REF}\s+{PROP}\s+{AT}\??')),
    ('PROOF_OBLIGATIONS', 'question | obligations', re.compile(rf'(?i)what\s+remains\s+to\s+prove\s+{REF}\s+{PROP}\s+{AT}\??')),
    ('HYPOTHETICAL', 'suppose {number}', re.compile(rf'(?i)what\s+if\s+{REF}\s+{PROP}\s+were\s+{NUM}\s+{AT}\??')),
)


class TranslationError(ValueError):
    pass


def translate(text: str) -> dict:
    if not isinstance(text, str) or not 1 <= len(text) <= 256 or any(ch in text for ch in '\r\n\x00'):
        raise TranslationError('CONTROLLED_LANGUAGE_REQUIRES_ONE_SHORT_LINE')
    source = text.strip()
    for purpose, suffix, pattern in TEMPLATES:
        m = pattern.fullmatch(source)
        if m is None:
            continue
        params=m.groupdict()
        part=params['ref'].upper()
        # Preserve the canonical known engineering property. Other property
        # names remain exact so the Kernel can explicitly report unknowns.
        property_name='tCEM' if params['property'].casefold()=='tcem' else params['property']
        try:
            expression=BASE.format(ref=part, property=property_name)+' | '+suffix.format(**params)
            ir=compile_text(expression)
        except (CompileError,KeyError,ValueError) as exc:
            raise TranslationError('CONTROLLED_INPUT_FAILED_STATIC_CHECK') from exc
        return {'schema':SCHEMA,'language':LANGUAGE,
                'interpretation':'EXACT_CONTROLLED_TEMPLATE',
                'purpose':purpose,'program':expression,'ir':ir,
                'intent_digest':intent_hash(ir),
                'effects':ir['effects'],
                'executed':False,'model_invoked':False,
                'source_binding':'SYMBOLIC_UNPINNED',
                'notice':'Deterministic recognized form only. No general natural language understanding or source verification.'}
    raise TranslationError('AMBIGUOUS_OR_UNSUPPORTED_ENGLISH: use strict staC or an explicitly listed controlled-English form')
