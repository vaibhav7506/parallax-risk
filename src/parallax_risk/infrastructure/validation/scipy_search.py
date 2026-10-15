"""SciPy differential evolution, no polishing or parallel/global random state."""

from collections.abc import Callable

import numpy as np
import scipy
from scipy.optimize import LinearConstraint, differential_evolution

from parallax_risk.common.errors import DomainValidationError
from parallax_risk.domain.simulation.arrays import FloatArray
from parallax_risk.domain.validation.search import OptimizerResult, SearchSpec


class _ObjectiveFailure(Exception):
    """Keep callback validation errors out of SciPy's map-shape exception wrapper."""

    def __init__(self, original: Exception) -> None:
        self.original = original


class ScipyDifferentialEvolution:
    def maximize(
        self, objective: Callable[[tuple[float, ...]], float], spec: SearchSpec
    ) -> OptimizerResult:
        recorded: list[tuple[tuple[float, ...], float]] = []

        def minimize(values: FloatArray) -> float:
            parameters = tuple(float(v) for v in values)
            try:
                score = objective(parameters)
            except (TypeError, ValueError) as error:
                raise _ObjectiveFailure(error) from error
            recorded.append((parameters, score))
            return -score

        constraints: LinearConstraint | tuple[()] = ()
        if spec.restrictions:
            constraints = LinearConstraint(
                np.asarray(tuple(c.weights for c in spec.restrictions)),
                np.asarray(tuple(c.lower for c in spec.restrictions)),
                np.asarray(tuple(c.upper for c in spec.restrictions)),
            )
        try:
            result = differential_evolution(
                minimize,
                tuple((d.lower, d.upper) for d in spec.dimensions),
                maxiter=spec.maximum_iterations,
                popsize=spec.population_multiplier,
                tol=spec.convergence_relative,
                atol=spec.convergence_absolute,
                rng=spec.key.generator(),
                constraints=constraints,
                polish=False,
                workers=1,
                updating="immediate",
                init="latinhypercube",
            )
        except _ObjectiveFailure as error:
            raise error.original from None
        if not recorded:
            raise DomainValidationError(
                "Optimizer found no feasible population; no risk conclusion"
            )
        # Preserve the actual best tie by first evaluation; no unbudgeted final revaluation.
        parameters, score = max(recorded, key=lambda entry: entry[1])
        return OptimizerResult(
            parameters,
            score,
            bool(result.success),
            str(result.message),
            int(result.nit),
            len(recorded),
            f"scipy-{scipy.__version__}.differential_evolution; PCG64DXSM; no polish",
        )
