"""Research effective EE/EPE from an actual empirical exposure profile, by legal unit."""

from dataclasses import dataclass

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.enums import Currency
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.money import Money
from parallax_risk.domain._validation import require_currency, require_text
from parallax_risk.domain.ccr.contracts import scalar
from parallax_risk.domain.exposure.statistics import ExposureProfile, validate_times
from parallax_risk.domain.pricing._numbers import priced_money, product, total


@dataclass(frozen=True, slots=True)
class ChallengerResult:
    scope: str
    currency: Currency
    profile_hash: str
    times: tuple[float, ...]
    expected_exposure: tuple[float, ...]
    effective_expected_exposure: tuple[float, ...]
    epe: Money
    effective_epe: Money
    alpha: float
    ead: Money
    paths: int
    methodology: str = "right_endpoint_average_first_year_or_final_maturity_v0.8.0"


def challenger(
    scope: str, profile: ExposureProfile, maturity: float, alpha: float
) -> ChallengerResult:
    """Require an exact horizon node; no interpolation, extrapolation or stressed calibration."""
    require_text(scope)
    if not isinstance(profile, ExposureProfile):
        raise DomainValidationError("Challenger requires an empirical ExposureProfile")
    require_currency(profile.currency)
    validate_times(profile.times)
    horizon = min(1.0, scalar(maturity, "scope final maturity", positive=True))
    scalar(alpha, "challenger alpha", positive=True)
    if horizon not in profile.times:
        raise DomainValidationError(
            "Challenger grid must contain min(1 year, final maturity) exactly"
        )
    values = profile.expected_exposure
    if not isinstance(values, tuple) or len(values) != len(profile.times):
        raise DomainValidationError("Empirical EE must align with the time grid")
    for value in values:
        scalar(value, "empirical expected exposure")
    if type(profile.paths) is not int or profile.paths < 1:
        raise DomainValidationError("Empirical profile must identify a positive path count")
    end = profile.times.index(horizon) + 1
    times, ee = profile.times[:end], values[:end]
    effective: list[float] = []
    running = 0.0
    for value in ee:
        running = max(running, value)
        effective.append(running)
    weights = tuple((b - a) / horizon for a, b in zip(times, times[1:], strict=False))
    epe = total(tuple(product(v, w) for v, w in zip(ee[1:], weights, strict=True)))
    effective_epe = total(tuple(product(v, w) for v, w in zip(effective[1:], weights, strict=True)))
    digest = content_hash((profile.currency, profile.times, values, profile.paths))
    return ChallengerResult(
        scope,
        profile.currency,
        digest,
        times,
        ee,
        tuple(effective),
        priced_money(epe, profile.currency),
        priced_money(effective_epe, profile.currency),
        alpha,
        priced_money(product(alpha, effective_epe), profile.currency),
        profile.paths,
    )
