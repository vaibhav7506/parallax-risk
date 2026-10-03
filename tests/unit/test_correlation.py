"""Correlation validation, singular policy and reported explicit repair."""

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from parallax_risk.common.errors import CorrelationError, ParallaxError
from parallax_risk.domain.models.correlation import CorrelationMatrix, repair_correlation


def test_valid_cholesky_reconstruction_and_identity():
    matrix = CorrelationMatrix(
        ("rate", "spot", "variance"), ((1.0, 0.3, -0.2), (0.3, 1.0, 0.4), (-0.2, 0.4, 1.0))
    )
    factor = np.array(matrix.cholesky())
    np.testing.assert_allclose(factor @ factor.T, matrix.values, atol=1e-14, rtol=0)
    assert matrix.diagnostics.numerically_positive_definite
    assert np.array_equal(factor, np.tril(factor))
    assert CorrelationMatrix(matrix.factors, matrix.values).hash == matrix.hash
    assert CorrelationMatrix(tuple(reversed(matrix.factors)), matrix.values).hash != matrix.hash
    with pytest.raises(FrozenInstanceError):
        matrix.values = ()


@pytest.mark.parametrize(
    "factors,values",
    [
        ((), ()),
        (("a", "a"), ((1.0, 0.0), (0.0, 1.0))),
        (("bad name",), ((1.0,),)),
        (("a", "b"), ((1.0,),)),
        (("a", "b"), ((1.0, 0.0), (0.0,))),
        (("a", "b"), [[1.0, 0.0], [0.0, 1.0]]),
        (("a",), ((0.9999999999999999,),)),
        (("a", "b"), ((1.0, 0.2), (0.2 + 1e-15, 1.0))),
        (("a", "b"), ((1.0, 1.01), (1.01, 1.0))),
        (("a",), ((float("nan"),),)),
        (("a", "b", "c"), ((1.0, 0.9, 0.9), (0.9, 1.0, -0.9), (0.9, -0.9, 1.0))),
    ],
)
def test_invalid_correlations_are_rejected(factors, values):
    with pytest.raises(ParallaxError):
        CorrelationMatrix(factors, values)


@pytest.mark.parametrize("tolerance", [0.0, -1.0, 1e-6, float("nan")])
def test_invalid_psd_tolerance(tolerance):
    with pytest.raises(ParallaxError):
        CorrelationMatrix(("a",), ((1.0,),), tolerance)


def test_singular_and_roundoff_psd_are_not_silently_factorized():
    singular = CorrelationMatrix(("a", "b"), ((1.0, 1.0), (1.0, 1.0)))
    assert singular.diagnostics.eigenvalues[0] == 0
    with pytest.raises(CorrelationError, match="minimum eigenvalue"):
        singular.cholesky()
    rho = -0.5 - 2.5e-14
    values = ((1.0, rho, rho), (rho, 1.0, rho), (rho, rho, 1.0))
    unresolved = CorrelationMatrix(("a", "b", "c"), values)
    assert unresolved.values == values and unresolved.diagnostics.eigenvalues[0] < 0
    with pytest.raises(CorrelationError):
        unresolved.cholesky()


def test_explicit_repair_reports_original_output_and_transformation():
    factors = ("a", "b", "c")
    values = ((1.0, 0.9, 0.9), (0.9, 1.0, -0.9), (0.9, -0.9, 1.0))
    for request in (False, None, 1):
        with pytest.raises(CorrelationError, match="explicit"):
            repair_correlation(factors, values, requested=request)
    report = repair_correlation(factors, values, requested=True)
    assert report.original_values == values and report.clipped_eigenvalue_count == 1
    assert report.frobenius_change > 0 and report.original_eigenvalues[0] < 0
    assert report.repaired.diagnostics.eigenvalues[0] > 0
    factor = np.asarray(report.repaired.cholesky())
    np.testing.assert_allclose(factor @ factor.T, report.repaired.values, atol=1e-14, rtol=0)
    assert report.method == "eigenvalue_clipping_and_diagonal_rescaling"
    assert report.original_hash != report.repaired.hash


@pytest.mark.parametrize("floor", [0.0, 1e-12, 1.0, float("inf")])
def test_invalid_repair_floor(floor):
    with pytest.raises(ParallaxError):
        repair_correlation(("a",), ((1.0,),), requested=True, eigenvalue_floor=floor)


def test_numerical_factorization_failure_is_visible(monkeypatch):
    matrix = CorrelationMatrix(("a",), ((1.0,),))

    def fail(array):
        raise np.linalg.LinAlgError("test failure")

    monkeypatch.setattr(np.linalg, "cholesky", fail)
    with pytest.raises(CorrelationError, match="no fallback"):
        matrix.cholesky()
