"""Small, explicitly scoped engineering evidence calculus (not a proof assistant).

Positive/negative support are booleans for *reviewed support*, not truth or
confidence probabilities. Applicability to a source revision is orthogonal.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class EvidenceState(str, Enum):
    UNKNOWN = 'UNKNOWN'
    SUPPORTED = 'SUPPORTED'
    REFUTED = 'REFUTED'
    CONFLICT = 'CONFLICT'


class Applicability(str, Enum):
    NOT_ASSESSED = 'NOT_ASSESSED'
    CURRENT = 'CURRENT'
    STALE = 'STALE'
    MISSING_SOURCE = 'MISSING_SOURCE'


@dataclass(frozen=True)
class EvidenceSupport:
    positive: bool = False
    negative: bool = False

    @property
    def state(self) -> EvidenceState:
        return {
            (False, False): EvidenceState.UNKNOWN,
            (True, False): EvidenceState.SUPPORTED,
            (False, True): EvidenceState.REFUTED,
            (True, True): EvidenceState.CONFLICT,
        }[(self.positive, self.negative)]

    def merge(self, other: 'EvidenceSupport') -> 'EvidenceSupport':
        """Join independent reviewed support; preserve disagreement.

        Caller must establish source identity, review state and applicability.
        Mere presence of a quotation is not a warrant to set either bit.
        """
        if not isinstance(other, EvidenceSupport):
            raise TypeError('EvidenceSupport expected')
        return EvidenceSupport(self.positive or other.positive,
                               self.negative or other.negative)


def assessment(support: EvidenceSupport, *, applicability: Applicability, citations: list[str]) -> dict:
    """Encode support without silently converting stale evidence to current truth."""
    if not isinstance(applicability, Applicability):
        raise TypeError('Applicability expected')
    return {'state': support.state.value,
            'support': {'positive': support.positive, 'negative': support.negative},
            'applicability': applicability.value,
            'citations': sorted(set(citations))}


# Pass 004: the actual four-valued truth and knowledge lattice operations.
# Applicability (source revision/grade) and review status are orthogonal axes.
# These pure operators NEVER create admissible evidence or prove real facts.
class ReviewState(str, Enum):
    UNREVIEWED = 'UNREVIEWED'
    CANDIDATE = 'CANDIDATE'
    REVIEWED = 'REVIEWED'
    REJECTED = 'REJECTED'


def negate(e: EvidenceSupport) -> EvidenceSupport:
    """Four-valued negation: exchange positive/negative support."""
    if not isinstance(e, EvidenceSupport):
        raise TypeError('EvidenceSupport expected')
    return EvidenceSupport(e.negative, e.positive)


def truth_and(a: EvidenceSupport, b: EvidenceSupport) -> EvidenceSupport:
    """Belnap truth order conjunction, not a merge of independent evidence."""
    if not isinstance(a, EvidenceSupport) or not isinstance(b, EvidenceSupport):
        raise TypeError('EvidenceSupport expected')
    return EvidenceSupport(a.positive and b.positive, a.negative or b.negative)


def truth_or(a: EvidenceSupport, b: EvidenceSupport) -> EvidenceSupport:
    """Belnap truth order disjunction; T or F gives T, *not* CONFLICT."""
    if not isinstance(a, EvidenceSupport) or not isinstance(b, EvidenceSupport):
        raise TypeError('EvidenceSupport expected')
    return EvidenceSupport(a.positive or b.positive, a.negative and b.negative)


def knowledge_join(a: EvidenceSupport, b: EvidenceSupport) -> EvidenceSupport:
    """Accumulate qualified independent support, retaining disagreements."""
    return a.merge(b)


def knowledge_meet(a: EvidenceSupport, b: EvidenceSupport) -> EvidenceSupport:
    """Belnap information-order meet: only support common to both."""
    if not isinstance(a, EvidenceSupport) or not isinstance(b, EvidenceSupport):
        raise TypeError('EvidenceSupport expected')
    return EvidenceSupport(a.positive and b.positive, a.negative and b.negative)


@dataclass(frozen=True)
class ScopedJudgement:
    """Typed context gate for already-vetted evidence, never a source verifier.

    The *calling trusted Ledger component* must validate actual citations and
    review before constructing this object. A model cannot instantiate it as an
    authorization; a Python object is not a cryptographic witness.
    """
    predicate: str
    revision: str
    variant: str
    support: EvidenceSupport
    applicability: Applicability
    review: ReviewState
    citations: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.predicate or not self.revision or not self.variant:
            raise ValueError('Evidence must pin predicate, revision and variant')
        if not isinstance(self.support, EvidenceSupport) or not isinstance(self.applicability, Applicability) or not isinstance(self.review, ReviewState):
            raise TypeError('Invalid evidence types')
        if not isinstance(self.citations, tuple) or any(not isinstance(c,str) or not c for c in self.citations):
            raise TypeError('Citations must be nonempty strings in a tuple')

    @property
    def admissible(self) -> bool:
        return (self.applicability is Applicability.CURRENT and
                self.review is ReviewState.REVIEWED and bool(self.citations))

    @property
    def qualified_support(self) -> EvidenceSupport:
        return self.support if self.admissible else EvidenceSupport()

    def join(self, other: 'ScopedJudgement') -> 'ScopedJudgement':
        if not isinstance(other, ScopedJudgement) or (
            self.predicate, self.revision, self.variant) != (
            other.predicate, other.revision, other.variant):
            raise ValueError('Cannot merge different propositions, revisions or fitted grades')
        if not self.admissible or not other.admissible:
            raise ValueError('Cannot promote unreviewed, stale or uncited support')
        return ScopedJudgement(self.predicate, self.revision, self.variant,
                               knowledge_join(self.support, other.support),
                               Applicability.CURRENT, ReviewState.REVIEWED,
                               tuple(sorted(set(self.citations + other.citations))))
