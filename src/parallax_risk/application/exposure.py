"""Injected pathwise repricing, explicit research cash settlement and WWR comparisons."""

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Protocol

import numpy as np

from parallax_risk.application.context import RunContext
from parallax_risk.application.portfolio import PortfolioService
from parallax_risk.application.simulation import SimulationEngine
from parallax_risk.common.enums import DayCount
from parallax_risk.common.errors import DomainValidationError, ParallaxError
from parallax_risk.common.identifiers import CollateralMovementId, CounterpartyId, PortfolioVersion
from parallax_risk.common.logging import WorkflowLogger
from parallax_risk.common.money import Money
from parallax_risk.common.time import year_fraction
from parallax_risk.domain._validation import require_tuple
from parallax_risk.domain.credit.dependence import (
    conditional_survival,
    default_thresholds,
    intensity_default_times,
    static_rank_thresholds,
)
from parallax_risk.domain.exposure.contracts import CreditScenario, DependenceKind
from parallax_risk.domain.exposure.markets import ConditionalMarketScenario, component
from parallax_risk.domain.exposure.statistics import (
    DependenceComparison,
    ExposureProfile,
    compare_dependence,
    exposure_at_default,
    profile,
)
from parallax_risk.domain.models.assets import GeometricBrownianMotion
from parallax_risk.domain.portfolio.collateral import CollateralAccount, CollateralMovement
from parallax_risk.domain.portfolio.contracts import PortfolioSnapshot
from parallax_risk.domain.pricing.engine import PricingContext
from parallax_risk.domain.simulation.arrays import FrozenArray, integer
from parallax_risk.domain.simulation.contracts import (
    PathBatch,
    SimulationMetadata,
    SimulationRequest,
)


class ExposureMarkets(Protocol):
    """Validated future-date markets; implementations own path-specific known fixings."""

    @property
    def dates(self) -> tuple[date, ...]: ...

    @property
    def hash(self) -> str: ...

    def path(
        self, book: PortfolioSnapshot, batch: PathBatch, local_path: int
    ) -> Iterator[PricingContext]: ...


@dataclass(frozen=True, slots=True)
class CounterpartyExposure:
    counterparty_id: CounterpartyId
    profile: ExposureProfile
    credit_hash: str | None
    default_comparison: DependenceComparison | None
    baseline_survival: tuple[float, ...] | None
    scenario_survival: tuple[float, ...] | None


@dataclass(frozen=True, slots=True)
class ExposureRunResult:
    context: RunContext
    simulation: SimulationMetadata
    portfolio_hash: str
    initial_account_hashes: tuple[str, ...]
    market_scenario_hash: str
    market_path_digest: str
    dates: tuple[date, ...]
    counterparties: tuple[CounterpartyExposure, ...]
    total_profile: ExposureProfile
    positive_paths: FrozenArray
    negative_paths: FrozenArray
    assumptions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExposureService:
    """Finite-horizon collector with a caller budget; no API/database/global RNG.

    Collateral policy deliberately restricted to same-CSA-currency zero-haircut
    cash: effective instructions equal physical units. Assumes perfect scheduled
    settlement; any preexisting future calls are rejected, not replayed twice.
    """

    engine: SimulationEngine
    portfolio_service: PortfolioService
    logger: WorkflowLogger

    def run(
        self,
        request: SimulationRequest,
        book: PortfolioSnapshot,
        markets: ExposureMarkets,
        run: RunContext,
        *,
        accounts: tuple[CollateralAccount, ...] = (),
        credit: tuple[CreditScenario, ...] = (),
        quantiles: tuple[float, ...] = (0.95, 0.99),
        maximum_output_bytes: int = 256 * 1024 * 1024,
    ) -> ExposureRunResult:
        if not isinstance(run, RunContext):
            raise DomainValidationError("Exposure requires validated run metadata")
        self.logger.event("exposure_started", run_id=str(run.run_id), outcome="started")
        try:
            result = self._run(
                request, book, markets, run, accounts, credit, quantiles, maximum_output_bytes
            )
        except ParallaxError as error:
            self.logger.event(
                "exposure_failed",
                run_id=str(run.run_id),
                outcome="failed",
                error_type=type(error).__name__,
            )
            raise
        self.logger.event("exposure_completed", run_id=str(run.run_id), outcome="completed")
        return result

    def _run(
        self,
        request: SimulationRequest,
        book: PortfolioSnapshot,
        markets: ExposureMarkets,
        run: RunContext,
        accounts: tuple[CollateralAccount, ...],
        credit: tuple[CreditScenario, ...],
        quantiles: tuple[float, ...],
        maximum_output_bytes: int,
    ) -> ExposureRunResult:
        if (
            not isinstance(request, SimulationRequest)
            or not isinstance(book, PortfolioSnapshot)
            or not book.counterparties
        ):
            raise DomainValidationError(
                "Exposure needs validated simulation and nonempty counterparty book"
            )
        dates = markets.dates
        if (
            not isinstance(dates, tuple)
            or len(dates) != len(request.grid.times)
            or dates[0] != book.as_of
        ):
            raise DomainValidationError("Exposure dates must match book origin and simulation grid")
        times = tuple(year_fraction(book.as_of, d, DayCount.ACT_365_FIXED) for d in dates)
        if times != request.grid.times or run.seed != request.sequence.key.seed:
            raise DomainValidationError(
                "Exposure dates use ACT/365F and run seed must match market simulation"
            )
        if isinstance(markets, ConditionalMarketScenario) and markets.request != request:
            raise DomainValidationError(
                "Conditional market factory must use this simulation request"
            )
        require_tuple(accounts, CollateralAccount)
        require_tuple(credit, CreditScenario)
        names = tuple(c.counterparty_id for c in book.counterparties)
        if len({c.counterparty_id for c in credit}) != len(credit) or any(
            c.counterparty_id not in names for c in credit
        ):
            raise DomainValidationError(
                "Credit specifications must uniquely identify portfolio counterparties"
            )
        for c in credit:
            if c.baseline.times[-1] != times[-1]:
                raise DomainValidationError("Credit baseline horizon must equal exposure horizon")
            if (
                c.threshold_key.seed != run.seed
                or c.threshold_key == request.sequence.key
                or c.rank_key == request.sequence.key
            ):
                raise DomainValidationError(
                    "Credit addresses must be distinct from market stream and use the run seed"
                )
            if c.rank_key is not None and (
                c.rank_key.seed != run.seed or c.rank_key in {v.threshold_key for v in credit}
            ):
                raise DomainValidationError(
                    "Static rank address must be separate from all default addresses"
                )
            if c.kind == DependenceKind.DYNAMIC_SPREAD:
                assert c.spread_component is not None
                item, _ = component(request, c.spread_component)
                if (
                    not isinstance(item.process, GeometricBrownianMotion)
                    or item.measure != "Q"
                    or item.state_units != ("decimal_annual_spread",)
                ):
                    raise DomainValidationError(
                        "Dynamic credit requires Q GBM with annual spread units"
                    )
        if len({c.threshold_key for c in credit}) != len(credit):
            raise DomainValidationError("Counterparty thresholds require separate random addresses")
        addresses = tuple(c.threshold_key for c in credit) + tuple(
            c.rank_key for c in credit if c.rank_key is not None
        )
        if len(set(addresses)) != len(addresses):
            raise DomainValidationError("All default and rank addresses must be unique")
        scopes = tuple(n for c in book.counterparties for n in c.netting_sets if n.csa is not None)
        for n in scopes:
            assert n.csa is not None
            if any(b - a != timedelta(days=1) for a, b in zip(dates, dates[1:], strict=False)):
                raise DomainValidationError(
                    "Simulated margin requires a complete daily calendar grid"
                )
            if n.csa.eligible(n.csa.currency).haircut != 0:
                raise DomainValidationError(
                    "Automatic research settlement requires zero-haircut agreement-currency cash"
                )
        if len(accounts) != len(scopes) or {a.netting_set_id for a in accounts} != {
            n.netting_set_id for n in scopes
        }:
            raise DomainValidationError("Supply exactly one initial account per CSA scope")
        for a in accounts:
            if any(m.call_date >= dates[0] or m.settlement_date > dates[0] for m in a.movements):
                raise DomainValidationError(
                    "Initial simulated accounts cannot contain pending/future origin calls"
                )
        integer(maximum_output_bytes, "maximum retained output bytes")
        required = request.path_count * len(times) * len(names) * 8 * 2
        if required > maximum_output_bytes:
            raise DomainValidationError("Retained exposure matrices exceed explicit output budget")
        # Validate statistical settings before any pricing work.
        dummy = np.zeros((1, len(times)), dtype=np.float64)
        profile(dummy, dummy, times, quantiles, book.reporting_currency)
        shape = (request.path_count, len(times), len(names))
        positive = np.empty(shape, dtype=np.float64)
        negative = np.empty(shape, dtype=np.float64)
        dynamic = {
            c.counterparty_id: np.empty((request.path_count, len(times) - 1), dtype=np.float64)
            for c in credit
            if c.kind == DependenceKind.DYNAMIC_SPREAD
        }
        digest = hashlib.sha256()
        consumed = 0
        for batch in self.engine.iter_batches(request):
            if (
                batch.start_path != consumed
                or batch.path_count + consumed > request.path_count
                or batch.values.shape[1:] != (len(times), request.state_dimension)
            ):
                raise DomainValidationError(
                    "Simulation batches must be complete contiguous aligned paths"
                )
            for local in range(batch.path_count):
                path = batch.start_path + local
                ledgers = {a.netting_set_id: a for a in accounts}
                count = 0
                for step, market in enumerate(markets.path(book, batch, local)):
                    if (
                        step >= len(dates)
                        or not isinstance(market, PricingContext)
                        or market.snapshot.valuation_date != dates[step]
                    ):
                        raise DomainValidationError(
                            "Market adapter must supply one correctly dated context per grid point"
                        )
                    digest.update(market.snapshot.snapshot_hash.encode("ascii"))
                    digest.update(market.curves.curve_hash.encode("ascii"))
                    future_book = replace(
                        book, as_of=dates[step], version=PortfolioVersion(f"exposure-{step}")
                    )
                    valuation = self.portfolio_service.value(
                        future_book, market, run, tuple(ledgers.values())
                    )
                    changed = False
                    for cp in valuation.counterparties:
                        for scope in cp.netting_sets:
                            call = scope.margin
                            if call is not None and call.transfer.amount != 0:
                                ledger = ledgers[scope.netting_set_id]
                                cash = Money(call.transfer.amount, call.transfer.currency)
                                movement = CollateralMovement(
                                    CollateralMovementId(f"sim-{step}"),
                                    dates[step],
                                    call.settlement_date,
                                    cash,
                                )
                                ledgers[scope.netting_set_id] = ledger.append(movement)
                                changed = changed or call.settlement_date == dates[step]
                    if changed:
                        valuation = self.portfolio_service.value(
                            future_book, market, run, tuple(ledgers.values())
                        )
                    for cp in valuation.counterparties:
                        index = names.index(cp.counterparty_id)
                        positive[path, step, index] = float(cp.positive_exposure.amount)
                        negative[path, step, index] = float(cp.negative_exposure.amount)
                    count += 1
                if count != len(dates):
                    raise DomainValidationError("Market adapter omitted future grid contexts")
            for c in credit:
                if c.kind == DependenceKind.DYNAMIC_SPREAD:
                    assert c.spread_component is not None and c.spread_policy is not None
                    _, offset = component(request, c.spread_component)
                    for local in range(batch.path_count):
                        for step in range(len(times) - 1):
                            dynamic[c.counterparty_id][batch.start_path + local, step] = (
                                c.spread_policy.intensity(
                                    float(batch.values.array[local, step, offset])
                                )
                            )
            consumed += batch.path_count
        if consumed != request.path_count:
            raise DomainValidationError("Simulation ended before the configured path count")
        counterparties = []
        for index, name in enumerate(names):
            pos, neg = positive[:, :, index], negative[:, :, index]
            summary = profile(pos, neg, times, quantiles, book.reporting_currency)
            specification = next((c for c in credit if c.counterparty_id == name), None)
            comparison = None
            baseline_survival = None
            scenario_survival = None
            if specification is not None:
                baseline_survival = tuple(specification.baseline.survival(t) for t in times)
                scenario_survival = baseline_survival
                thresholds = default_thresholds(specification.threshold_key, request.path_count)
                baseline_defaults = tuple(
                    specification.baseline.default_time(float(e)) for e in thresholds
                )
                scenario_defaults = baseline_defaults
                if specification.kind == DependenceKind.STATIC_RANK:
                    assert specification.rank_key is not None
                    scores = np.asarray(
                        np.trapezoid(pos, np.asarray(times), axis=1) / times[-1], dtype=np.float64
                    )
                    thresholds = static_rank_thresholds(
                        thresholds, scores, specification.rho, specification.rank_key
                    )
                    scenario_defaults = tuple(
                        specification.baseline.default_time(float(e)) for e in thresholds
                    )
                if specification.kind == DependenceKind.DYNAMIC_SPREAD:
                    scenario_defaults = intensity_default_times(times, dynamic[name], thresholds)
                    scenario_survival = tuple(
                        map(float, np.mean(conditional_survival(times, dynamic[name]), axis=0))
                    )
                comparison = compare_dependence(
                    exposure_at_default(pos, times, baseline_defaults),
                    exposure_at_default(pos, times, scenario_defaults),
                )
            counterparties.append(
                CounterpartyExposure(
                    name,
                    summary,
                    specification.hash if specification else None,
                    comparison,
                    baseline_survival,
                    scenario_survival,
                )
            )
        return ExposureRunResult(
            run,
            self.engine.metadata(request),
            book.snapshot_hash,
            tuple(a.account_hash for a in sorted(accounts, key=lambda a: str(a.netting_set_id))),
            markets.hash,
            digest.hexdigest(),
            dates,
            tuple(counterparties),
            profile(
                np.sum(positive, axis=2),
                np.sum(negative, axis=2),
                times,
                quantiles,
                book.reporting_currency,
            ),
            FrozenArray.from_array(positive),
            FrozenArray.from_array(negative),
            (
                "Undiscounted equal-weight alive exposure paths; no CVA or loss adjustment",
                "PFE uses retained-sample linear quantiles; EPE trapezoidal over supplied horizon",
                "Research same-currency zero-haircut cash settles perfectly; daily grid for CSA",
                "EAD uses right endpoint alive collateral; no default-conditioned freeze/MPOR",
                "Static ranks are non-adapted stress; dynamic survival is not baseline-calibrated",
                "Caller declares Q drift consistency; correlation does not ensure no arbitrage",
            ),
        )
