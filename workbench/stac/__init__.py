"""staC: versioned, typed, evidence-first engineering language for ARC Ledger.

The 0.2 typed interpreter and 0.4 semantic-question IDs remain compatible.
Pass 0.5 adds source-checked vendor witnesses; Pass 0.6 adds
read-only Kernel job witnesses and deterministic shorthand.
The opt-in 0.3 CCC history remains separate from engineering execution.
No unrestricted execution, LLM runtime, or engineering-source mutation.
"""
from .language import CompileError, Context, compile_text, intent_hash
from .runtime import RunError, evaluate
from .evidence import EvidenceSupport, EvidenceState, Applicability

__all__ = ['CompileError','Context','compile_text','intent_hash','RunError',
           'evaluate','EvidenceSupport','EvidenceState','Applicability']

from .obligations import question, report as obligation_report
from .semantics import inspect as inspect_semantics
