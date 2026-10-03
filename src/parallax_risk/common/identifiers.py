"""Nominal immutable identifiers: equal text does not equate different ID types."""

import re
from dataclasses import dataclass

from parallax_risk.common.errors import DomainValidationError

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


@dataclass(frozen=True, slots=True)
class Identifier:
    """Case-sensitive ASCII token, 1–128 characters; no whitespace normalization."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not _IDENTIFIER.fullmatch(self.value):
            raise DomainValidationError("Identifier must be a 1–128 character ASCII token")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class TradeId(Identifier):
    """Trade identity."""


@dataclass(frozen=True, slots=True)
class CounterpartyId(Identifier):
    """Counterparty identity."""


@dataclass(frozen=True, slots=True)
class NettingSetId(Identifier):
    """Legally scoped netting-set identity."""


@dataclass(frozen=True, slots=True)
class CsaId(Identifier):
    """Credit support agreement identity."""


@dataclass(frozen=True, slots=True)
class ModelId(Identifier):
    """Model identity."""


@dataclass(frozen=True, slots=True)
class ModelVersion(Identifier):
    """Opaque version token; no ordering or semantic-version assumption."""


@dataclass(frozen=True, slots=True)
class RiskRunId(Identifier):
    """Run identity supplied independently of its random seed."""


@dataclass(frozen=True, slots=True)
class MarketSnapshotId(Identifier):
    """Market-data snapshot identity."""


@dataclass(frozen=True, slots=True)
class MarketSnapshotVersion(Identifier):
    """Opaque, immutable market-data version token."""


@dataclass(frozen=True, slots=True)
class QuoteId(Identifier):
    """Observation identity, unique within a snapshot."""


@dataclass(frozen=True, slots=True)
class CurveId(Identifier):
    """Curve identity; content hash also identifies its effective parameters."""


@dataclass(frozen=True, slots=True)
class CalibrationRunId(Identifier):
    """Caller-supplied calibration identity, independent of fitted parameters."""
