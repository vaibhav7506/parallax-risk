"""Injected actual simulation per legal unit, with retained evidence and research comparisons."""

from dataclasses import dataclass, replace
from decimal import Decimal

from parallax_risk.application.context import RunContext
from parallax_risk.application.exposure import ExposureService
from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import DomainValidationError
from parallax_risk.common.identifiers import CounterpartyId, NettingSetId
from parallax_risk.common.money import Money
from parallax_risk.domain._validation import require_tuple
from parallax_risk.domain.ccr.challenger import challenger
from parallax_risk.domain.ccr.comparison import ComparisonResult, compare
from parallax_risk.domain.ccr.contracts import (
    ComparisonPolicy,
    MarginTerms,
    StandardizedInputs,
    SupervisoryParameters,
)
from parallax_risk.domain.ccr.mapping import map_trade
from parallax_risk.domain.ccr.standardized import standardized
from parallax_risk.domain.exposure.markets import ConditionalMarketScenario
from parallax_risk.domain.portfolio.collateral import CollateralAccount
from parallax_risk.domain.portfolio.contracts import Counterparty, NettingSet, PortfolioSnapshot
from parallax_risk.domain.portfolio.csa import CollateralDirection
from parallax_risk.domain.simulation.contracts import SimulationMetadata, SimulationRequest


@dataclass(frozen=True, slots=True)
class ScopeMargin:
    netting_set_id: NettingSetId
    terms: MarginTerms

    def __post_init__(self) -> None:
        if not isinstance(self.netting_set_id, NettingSetId) or not isinstance(
            self.terms, MarginTerms
        ):
            raise DomainValidationError("Scope margin requires typed identity and validated terms")


@dataclass(frozen=True, slots=True)
class ScopeComparison:
    counterparty_id: CounterpartyId
    netting_set_id: NettingSetId
    unit_hash: str
    market_path_digest: str
    positive_path_hash: str
    account_hashes: tuple[str, ...]
    simulation: SimulationMetadata
    comparison: ComparisonResult


@dataclass(frozen=True, slots=True)
class CcrRunResult:
    context: RunContext
    portfolio_hash: str
    request_hash: str
    market_scenario_hash: str
    parameter_hash: str
    policy_hash: str
    scopes: tuple[ScopeComparison, ...]
    standardized_ead: Money
    challenger_ead: Money
    assumptions: tuple[str, ...] = (
        "Restricted domestic IRS/domestic-quote FX; no regulatory compliance or model approval",
        "Separate legal units; non-enforceable sets run each active trade separately",
        "Actual Q simulation; no stressed calibration, regulatory MPOR closeout or rollover model",
        "Business-day MPOR/NICA explicitly supplied; calendar-day CSA policy remains research-only",
        "EE/effective EE use right-endpoint averages at explicit first-year/final-maturity node",
        "Illustrative caller risk weights/capital ratio; no regulatory capital rulebook",
        "Per-unit memory budget; serial replay uses common addressed simulation streams",
    )


@dataclass(frozen=True, slots=True)
class CcrService:
    exposure: ExposureService

    def run(
        self,
        request: SimulationRequest,
        book: PortfolioSnapshot,
        markets: ConditionalMarketScenario,
        run: RunContext,
        parameters: SupervisoryParameters,
        policy: ComparisonPolicy,
        *,
        accounts: tuple[CollateralAccount, ...] = (),
        margins: tuple[ScopeMargin, ...] = (),
        maximum_output_bytes: int = 256 * 1024 * 1024,
    ) -> CcrRunResult:
        if (
            not isinstance(request, SimulationRequest)
            or not isinstance(book, PortfolioSnapshot)
            or not isinstance(markets, ConditionalMarketScenario)
            or not isinstance(run, RunContext)
        ):
            raise DomainValidationError(
                "CCR workflow needs validated simulation/book/conditional markets/run"
            )
        if (
            not isinstance(parameters, SupervisoryParameters)
            or not isinstance(policy, ComparisonPolicy)
            or policy.currency != book.reporting_currency
        ):
            raise DomainValidationError("CCR configuration must use portfolio reporting currency")
        if (
            markets.request != request
            or markets.dates[0] != book.as_of
            or run.seed != request.sequence.key.seed
        ):
            raise DomainValidationError("CCR simulation/market origin/run seed must agree")
        require_tuple(accounts, CollateralAccount)
        require_tuple(margins, ScopeMargin)
        sets = tuple(n for c in book.counterparties for n in c.netting_sets)
        if any(n.reporting_currency != policy.currency for n in sets):
            raise DomainValidationError(
                "Prototype requires all legal sets in portfolio reporting currency"
            )
        expected = {n.netting_set_id for n in sets if n.csa is not None}
        if (
            len({a.netting_set_id for a in accounts}) != len(accounts)
            or {a.netting_set_id for a in accounts} != expected
        ):
            raise DomainValidationError("Provide exactly one collateral ledger per CSA scope")
        if (
            len({m.netting_set_id for m in margins}) != len(margins)
            or {m.netting_set_id for m in margins} != expected
        ):
            raise DomainValidationError(
                "Provide exactly one explicit regulatory-style margin specification per CSA scope"
            )
        batch = next(self.exposure.engine.iter_batches(request))
        origin = next(markets.path(book, batch, 0))
        # Validate all ledgers/dates and price the complete book before splitting scopes.
        self.exposure.portfolio_service.value(book, origin, run, accounts)
        margin_map = {m.netting_set_id: m.terms for m in margins}
        results: list[ScopeComparison] = []
        for counterparty in book.counterparties:
            for netting in counterparty.netting_sets:
                active = tuple(t for t in netting.trades if t.active(book.as_of))
                if not active:
                    raise DomainValidationError(
                        "CCR comparison requires at least one active derivative per set"
                    )
                units = (
                    (replace(netting, trades=active),)
                    if netting.netting_enforceable
                    else tuple(replace(netting, trades=(t,)) for t in active)
                )
                for unit in units:
                    results.append(
                        self._unit(
                            request,
                            book,
                            markets,
                            run,
                            parameters,
                            policy,
                            counterparty,
                            unit,
                            accounts,
                            margin_map.get(unit.netting_set_id),
                            maximum_output_bytes,
                        )
                    )
        if not results:
            raise DomainValidationError("CCR comparison requires a nonempty book")
        zero = Money(Decimal(0), policy.currency)
        return CcrRunResult(
            run,
            book.snapshot_hash,
            content_hash(request),
            markets.hash,
            content_hash(parameters),
            content_hash(policy),
            tuple(results),
            sum((r.comparison.standardized.ead for r in results), zero),
            sum((r.comparison.challenger.ead for r in results), zero),
        )

    def _unit(
        self,
        request: SimulationRequest,
        book: PortfolioSnapshot,
        markets: ConditionalMarketScenario,
        run: RunContext,
        parameters: SupervisoryParameters,
        policy: ComparisonPolicy,
        counterparty: Counterparty,
        unit: NettingSet,
        accounts: tuple[CollateralAccount, ...],
        margin: MarginTerms | None,
        maximum_output_bytes: int,
    ) -> ScopeComparison:
        unit_book = replace(book, counterparties=(replace(counterparty, netting_sets=(unit,)),))
        ledgers = tuple(a for a in accounts if a.netting_set_id == unit.netting_set_id)
        origin = next(markets.path(unit_book, next(self.exposure.engine.iter_batches(request)), 0))
        values = self.exposure.portfolio_service.value(unit_book, origin, run, ledgers)
        net_value = values.counterparties[0].netting_sets[0]
        collateral = (
            Money(Decimal(0), policy.currency)
            if net_value.margin is None
            else net_value.margin.settled_collateral
        )
        if unit.csa is not None:
            assert margin is not None
            if unit.csa.direction == CollateralDirection.POST_ONLY or unit.csa.frequency_days != 1:
                raise DomainValidationError(
                    "Prototype margined comparisons require daily receive-capable CSA"
                )
            if (
                margin.threshold != unit.csa.receive_threshold
                or margin.minimum_transfer_amount != unit.csa.minimum_transfer_amount
            ):
                raise DomainValidationError(
                    "Explicit threshold/MTA must match actual simulation CSA"
                )
        trades = tuple(map_trade(t, book.as_of, policy.currency, origin) for t in unit.trades)
        scope = f"{counterparty.counterparty_id}/{unit.netting_set_id}"
        if not unit.netting_enforceable:
            scope += f"/{unit.trades[0].trade_id}"
        standard = standardized(
            StandardizedInputs(scope, net_value.signed_value, collateral, trades, margin),
            parameters,
        )
        exposure = self.exposure.run(
            request,
            unit_book,
            markets,
            run,
            accounts=ledgers,
            maximum_output_bytes=maximum_output_bytes,
        )
        if (
            exposure.portfolio_hash != unit_book.snapshot_hash
            or exposure.context != run
            or exposure.market_scenario_hash != markets.hash
            or exposure.initial_account_hashes != values.account_hashes
            or exposure.simulation.request_hash != request.hash
            or exposure.dates != markets.dates
            or exposure.total_profile.currency != policy.currency
            or exposure.total_profile.times != request.grid.times
            or exposure.total_profile.paths != request.path_count
            or exposure.positive_paths.shape != (request.path_count, len(markets.dates), 1)
        ):
            raise DomainValidationError(
                "Exposure adapter returned inconsistent legal-unit evidence"
            )
        internal = challenger(
            scope, exposure.total_profile, max(t.maturity for t in trades), policy.challenger_alpha
        )
        return ScopeComparison(
            counterparty.counterparty_id,
            unit.netting_set_id,
            unit_book.snapshot_hash,
            exposure.market_path_digest,
            exposure.positive_paths.hash,
            exposure.initial_account_hashes,
            exposure.simulation,
            compare(standard, internal, policy),
        )
