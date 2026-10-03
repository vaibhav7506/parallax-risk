"""Immutable dependence inputs, strict structure and explicit opt-in eigenvalue repair."""

from dataclasses import dataclass

import numpy as np

from parallax_risk.common.canonical import content_hash
from parallax_risk.common.errors import CorrelationError
from parallax_risk.common.math import require_finite
from parallax_risk.domain._validation import require_token, require_tuple
from parallax_risk.domain.models.base import Matrix, positive, vector


def _structure(
    factors: tuple[str, ...], values: Matrix
) -> np.ndarray[tuple[int, int], np.dtype[np.float64]]:
    require_tuple(factors, str, nonempty=True)
    for factor in factors:
        require_token(factor)
    if len(set(factors)) != len(factors):
        raise CorrelationError("Correlation factors must be unique and ordered")
    if not isinstance(values, tuple) or len(values) != len(factors):
        raise CorrelationError("Correlation matrix must be square and aligned to factors")
    rows = tuple(vector(row, len(factors), "correlation row") for row in values)
    # Structural equality is exact. Never silently average an asymmetric matrix.
    if any(rows[i][i] != 1.0 for i in range(len(factors))):
        raise CorrelationError("Correlation diagonal must be exactly one")
    if any(rows[i][j] != rows[j][i] for i in range(len(factors)) for j in range(i)):
        raise CorrelationError("Correlation matrix must be exactly symmetric")
    return np.asarray(rows, dtype=np.float64)


def _matrix(array: np.ndarray[tuple[int, int], np.dtype[np.float64]]) -> Matrix:
    return tuple(tuple(float(value) for value in row) for row in array)


@dataclass(frozen=True, slots=True)
class CorrelationDiagnostics:
    eigenvalues: tuple[float, ...]
    psd_tolerance: float
    numerically_positive_definite: bool


@dataclass(frozen=True, slots=True)
class CorrelationMatrix:
    """Exact symmetry/unit diagonal; PSD allows roundoff down to -psd_tolerance.

    No matrix modification occurs on validation. Singular/unresolved-positive
    matrices are accepted as numerical PSD but cannot use this Cholesky policy.
    """

    factors: tuple[str, ...]
    values: Matrix
    psd_tolerance: float = 1e-12

    def __post_init__(self) -> None:
        array = _structure(self.factors, self.values)
        tolerance = positive(self.psd_tolerance, "PSD tolerance")
        if tolerance >= 1e-6:
            raise CorrelationError("PSD tolerance must be below 1e-6; it is a roundoff allowance")
        if np.any(np.abs(array) > 1):
            raise CorrelationError("Correlation entries must be in [-1,1]")
        if float(np.linalg.eigvalsh(array)[0]) < -tolerance:
            raise CorrelationError("Correlation matrix is not positive semidefinite")

    @property
    def diagnostics(self) -> CorrelationDiagnostics:
        eigenvalues = tuple(float(x) for x in np.linalg.eigvalsh(np.asarray(self.values)))
        return CorrelationDiagnostics(
            eigenvalues, self.psd_tolerance, eigenvalues[0] > self.psd_tolerance
        )

    @property
    def hash(self) -> str:
        return content_hash(self)

    def cholesky(self) -> Matrix:
        """L such that L L^T=C, columns independent drivers; no singular fallback."""
        if not self.diagnostics.numerically_positive_definite:
            raise CorrelationError("Cholesky requires minimum eigenvalue above the PSD tolerance")
        try:
            factor = np.linalg.cholesky(np.asarray(self.values))
        except np.linalg.LinAlgError as error:
            raise CorrelationError("Cholesky failed; no fallback or repair was applied") from error
        if float(np.max(np.abs(factor @ factor.T - np.asarray(self.values)))) > self.psd_tolerance:
            raise CorrelationError("Cholesky reconstruction exceeded the PSD tolerance")
        return _matrix(factor)


@dataclass(frozen=True, slots=True)
class CorrelationRepair:
    """Evidence of an explicit eigenvalue clipping and diagonal rescaling operation."""

    original_hash: str
    original_values: Matrix
    repaired: CorrelationMatrix
    eigenvalue_floor: float
    original_eigenvalues: tuple[float, ...]
    clipped_eigenvalue_count: int
    frobenius_change: float
    method: str = "eigenvalue_clipping_and_diagonal_rescaling"


def repair_correlation(
    factors: tuple[str, ...],
    values: Matrix,
    *,
    requested: bool = False,
    eigenvalue_floor: float = 1e-8,
) -> CorrelationRepair:
    """Explicit opt-in only; NOT a nearest-correlation optimization algorithm.

    Structure/finite checks remain mandatory. Only eigenvalues/entry bounds can
    change; the report contains both inputs and outputs. No automatic caller.
    """
    if requested is not True:
        raise CorrelationError("Correlation repair requires explicit requested=True")
    floor = positive(eigenvalue_floor, "repair eigenvalue floor")
    if not 1e-12 < floor < 1:
        raise CorrelationError("Repair eigenvalue floor must be between 1e-12 and 1")
    original = _structure(factors, values)
    eigenvalues, eigenvectors = np.linalg.eigh(original)
    clipped = np.maximum(eigenvalues, floor)
    rebuilt = (eigenvectors * clipped) @ eigenvectors.T
    scales = np.sqrt(np.diag(rebuilt))
    scaled = rebuilt / np.outer(scales, scales)
    # Repair is an explicitly requested transformation; enforce exact structure.
    scaled = (scaled + scaled.T) / 2
    np.fill_diagonal(scaled, 1.0)
    repaired = CorrelationMatrix(factors, _matrix(scaled))
    change = require_finite(float(np.linalg.norm(scaled - original)), name="repair change")
    return CorrelationRepair(
        content_hash((factors, values)),
        values,
        repaired,
        floor,
        tuple(float(x) for x in eigenvalues),
        int(np.sum(eigenvalues < floor)),
        change,
    )
