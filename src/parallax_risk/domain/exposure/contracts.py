"""Immutable credit scenario configuration linked to explicit portfolio counterparties."""

from dataclasses import dataclass
from enum import StrEnum

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import CounterpartyId
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_token
from parallax_risk.domain.credit.dependence import StochasticCreditSpread
from parallax_risk.domain.credit.hazard import PiecewiseHazardCurve, RecoveryAssumption
from parallax_risk.domain.simulation.random import StreamKey


class DependenceKind(StrEnum):
    INDEPENDENT = "independent"
    STATIC_RANK = "static_rank_copula"
    DYNAMIC_SPREAD = "dynamic_correlated_spread"


@dataclass(frozen=True, slots=True)
class CreditScenario:
    """One name's declared deterministic baseline and optional dependence scenario.

    Static scores use path-average positive exposure (non-adapted). Dynamic spread
    shares a simulated component with explicitly correlated market factors. Neither
    model is recalibrated to keep dynamic survival equal to the baseline.
    """

    counterparty_id: CounterpartyId
    baseline: PiecewiseHazardCurve
    recovery: RecoveryAssumption
    threshold_key: StreamKey
    kind: DependenceKind = DependenceKind.INDEPENDENT
    rho: float = 0.0
    rank_key: StreamKey | None = None
    spread_component: str | None = None
    spread_policy: StochasticCreditSpread | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.counterparty_id, CounterpartyId)
            or not isinstance(self.baseline, PiecewiseHazardCurve)
            or not isinstance(self.recovery, RecoveryAssumption)
            or not isinstance(self.threshold_key, StreamKey)
            or not isinstance(self.kind, DependenceKind)
        ):
            raise DomainValidationError(
                "Credit scenario requires typed name, curve, recovery and addresses"
            )
        rho = require_finite(self.rho, name="static rho")
        if not -1 <= rho <= 1:
            raise DomainValidationError("Static rho must lie in [-1,1]")
        if self.kind == DependenceKind.STATIC_RANK:
            if not isinstance(self.rank_key, StreamKey) or self.rank_key == self.threshold_key:
                raise DomainValidationError(
                    "Static ranks require a distinct explicit random address"
                )
        elif rho != 0 or self.rank_key is not None:
            raise DomainValidationError("Static parameters only apply to static dependence")
        if self.kind == DependenceKind.DYNAMIC_SPREAD:
            if self.spread_component is None or not isinstance(
                self.spread_policy, StochasticCreditSpread
            ):
                raise DomainValidationError(
                    "Dynamic credit requires explicit component and spread policy"
                )
            require_token(self.spread_component)
            if self.spread_policy.recovery != self.recovery:
                raise DomainValidationError("Credit triangle and scenario recovery must agree")
            digest = self.spread_policy.hash
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)
            ):
                raise DomainValidationError("Spread policy requires a stable SHA-256 fingerprint")
        elif self.spread_component is not None or self.spread_policy is not None:
            raise DomainValidationError("Spread inputs only apply to dynamic credit")

    @property
    def hash(self) -> str:
        return content_hash(
            {
                "counterparty": self.counterparty_id,
                "baseline": self.baseline,
                "recovery": self.recovery,
                "threshold_key": self.threshold_key,
                "kind": self.kind,
                "rho": self.rho,
                "rank_key": self.rank_key,
                "spread_component": self.spread_component,
                "spread_policy_hash": self.spread_policy.hash if self.spread_policy else None,
            }
        )
