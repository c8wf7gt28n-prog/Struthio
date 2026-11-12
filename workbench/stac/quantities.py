"""staC 0.1 pure dimensional checking and evidence-scoped threshold reasoning.

The caller is responsible for obtaining requirements and observations from
trusted Ledger sources. Constructing these Python objects proves no provenance.
No amount of modeled evidence is automatically physical qualification.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from .evidence import EvidenceSupport, Applicability, assessment


class DimensionError(ValueError):
    pass


# Base SI units. Temperature conversion is deliberately not included here;
# temperature grades/conditions must be matched as metadata, not inferred.
UNITS = {
    's': ('time', Decimal('1')),
    'ms': ('time', Decimal('0.001')),
    'us': ('time', Decimal('0.000001')),
    'ns': ('time', Decimal('0.000000001')),
    'Hz': ('frequency', Decimal('1')),
    'kHz': ('frequency', Decimal('1000')),
    'MHz': ('frequency', Decimal('1000000')),
    'V': ('voltage', Decimal('1')),
    'mV': ('voltage', Decimal('0.001')),
    '1': ('dimensionless', Decimal('1')),
    'A': ('current', Decimal('1')),
    'mA': ('current', Decimal('0.001')),
    'uA': ('current', Decimal('0.000001')),
    'W': ('power', Decimal('1')),
    'mW': ('power', Decimal('0.001')),
    'B': ('memory', Decimal('1')),
    'kB': ('memory', Decimal('1000')),
    'MB': ('memory', Decimal('1000000')),
    'GB': ('memory', Decimal('1000000000')),
    'KiB': ('memory', Decimal('1024')),
    'MiB': ('memory', Decimal('1048576')),
    'GiB': ('memory', Decimal('1073741824')),
}


@dataclass(frozen=True)
class Quantity:
    value: Decimal
    unit: str

    def __post_init__(self):
        if isinstance(self.value, float):
            raise DimensionError('Do not construct engineering quantities from floating point; use Decimal/string')
        try:exact = Decimal(self.value)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise DimensionError('Invalid exact decimal') from exc
        if not exact.is_finite():raise DimensionError('NaN and infinity not allowed')
        from ..math_units import unit_spec
        try:unit_spec(self.unit)
        except ValueError as exc:raise DimensionError(str(exc)) from exc
        object.__setattr__(self,'value',exact)

    @property
    def dimension(self):
        from ..math_units import unit_spec, dimension_name
        return dimension_name(unit_spec(self.unit)[0])

    def as_base(self):
        from fractions import Fraction
        from decimal import localcontext
        from ..math_units import unit_spec
        exact = Fraction(self.value) * unit_spec(self.unit)[1]
        with localcontext() as context:
            context.prec = max(32, len(str(abs(exact.numerator))) + len(str(exact.denominator)) + 8)
            return Decimal(exact.numerator) / Decimal(exact.denominator)

    def converted(self, unit):
        from decimal import localcontext
        from fractions import Fraction
        from ..math_units import unit_spec
        dimension, factor = unit_spec(unit)
        if dimension != unit_spec(self.unit)[0]:raise DimensionError('Cannot convert incompatible dimensions')
        value = Fraction(self.value) * unit_spec(self.unit)[1] / factor
        with localcontext() as context:
            context.prec = max(32, len(str(abs(value.numerator))) + len(str(value.denominator)) + 8)
            return Quantity(Decimal(value.numerator) / Decimal(value.denominator), unit)

    def compare(self, other: 'Quantity') -> int:
        if not isinstance(other,Quantity) or self.dimension!=other.dimension:
            raise DimensionError('Cannot compare incompatible dimensions')
        a,b=self.as_base(),other.as_base()
        return (a>b)-(a<b)


@dataclass(frozen=True)
class Requirement:
    parameter: str
    upper_limit: Quantity
    grade: str
    source_ref: str
    review_state: str  # supplied by reviewed, source-verified Ledger evidence
    conditions: str  # explicit operating domain; no approximate similarity match


@dataclass(frozen=True)
class Observation:
    parameter: str
    value: Quantity
    grade: str
    conditions: str
    source_revision: str
    evidence_class: str  # SIMULATION or PHYSICAL, from registered Kernel evidence
    source_ref: str


def assess_upper_bound(requirement: Requirement, observation: Observation | None,
                       *, selected_revision: str, requested_class: str = 'SIMULATION') -> dict:
    """Check an exact upper bound, returning a *scoped* evidentiary assessment.

    This does not promote a claim to approved design truth or verify the
    instrument itself. The requirement and observation must be established
    upstream from reviewed Ledger sources/Kernel jobs; this function only
    checks their compatibility and the specified arithmetic.
    """
    if requested_class not in ('SIMULATION','PHYSICAL'):
        raise ValueError('Unknown qualification class')
    if not isinstance(requirement,Requirement):raise TypeError('Expected Requirement')
    problems=[]
    if requirement.review_state!='REVIEWED_FACT':
        problems.append('UNREVIEWED_REQUIREMENT')
    if not requirement.source_ref:problems.append('MISSING_REQUIREMENT_SOURCE')
    if observation is None:
        problems.append('NO_OBSERVATION')
        base=assessment(EvidenceSupport(),applicability=Applicability.NOT_ASSESSED,citations=[])
        return {'schema':'arc.stac.assessment/0.1',**base,'claim_scope':requested_class,
                'parameter':requirement.parameter,'problems':problems,
                'physical_qualification_granted':False}
    if not isinstance(observation, Observation):raise TypeError('Expected Observation')
    if observation.parameter!=requirement.parameter:problems.append('PARAMETER_MISMATCH')
    if observation.grade!=requirement.grade:problems.append('GRADE_MISMATCH')
    if observation.conditions!=requirement.conditions:problems.append('OPERATING_CONDITIONS_MISMATCH')
    if not observation.source_ref:problems.append('MISSING_OBSERVATION_SOURCE')
    if observation.evidence_class!=requested_class:problems.append('EVIDENCE_CLASS_MISMATCH')
    stale=observation.source_revision!=selected_revision
    if stale:problems.append('SOURCE_REVISION_STALE')
    if requirement.upper_limit.dimension!=observation.value.dimension:
        problems.append('DIMENSION_MISMATCH')
    if problems:
        applicability=Applicability.STALE if stale else Applicability.NOT_ASSESSED
        result=assessment(EvidenceSupport(),applicability=applicability,citations=[])
    else:
        in_limit=observation.value.compare(requirement.upper_limit)<=0
        support=EvidenceSupport(positive=in_limit,negative=not in_limit)
        result=assessment(support,applicability=Applicability.CURRENT,
                          citations=[requirement.source_ref, observation.source_ref])
    return {'schema':'arc.stac.assessment/0.1',**result,
            'claim_scope':requested_class,'parameter':requirement.parameter,
            'problems':problems,
            # Even an externally submitted 'PHYSICAL' observation must be validated
            # by Kernel provenance/review before any physical release gate changes.
            'physical_qualification_granted':False}
