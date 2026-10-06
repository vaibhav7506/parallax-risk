# Correlation validation and explicit repair

## Intuition and mathematics

Pairwise correlations must describe a possible joint dependence structure. Valid
individual entries are insufficient: the complete symmetric matrix must be positive
semidefinite (PSD), meaning every quadratic form has nonnegative variance.
Positive definite matrices can be factored as C=L L^T by Cholesky, with L mapping
independent shocks into correlated shocks. Singular PSD dependence is meaningful
but cannot use this implementation's Cholesky policy.

## Implementation and tolerances

CorrelationMatrix in `src/parallax_risk/domain/models/correlation.py` owns an ordered
unique factor tuple and finite square tuple matrix. Entries require [-1,1], diagonal
exactly one and symmetry exactly equal. Tiny asymmetric input is rejected; validation
never averages or changes it. PSD uses NumPy eigvalsh with an explicit absolute
eigenvalue roundoff allowance 1e-12 (positive and below 1e-6).
Eigenvalues below minus this tolerance reject the matrix. Eigenvalues in the
roundoff band can be accepted as numerical PSD, with unchanged input/eigenvalues
visible in diagnostics. Cholesky requires minimum eigenvalue greater than the
tolerance, and reconstruction max-entry error at most that tolerance. Near-singular
positive matrices below the policy threshold are also rejected for Cholesky.

## Explicit repair

`repair_correlation(factors, values, requested=True)` is the only opt-in repair path.
It clips eigenvalues to an explicit positive floor (default 1e-8), reconstructs,
rescales the diagonal to one and enforces exact symmetric output. The floor must
be strictly between 1e-12 and 1. Structural/finite/diagonal/symmetry defects are
still rejected. The immutable CorrelationRepair report includes original matrix/hash,
original eigenvalues, clipped count, output matrix/hash, floor, method and Frobenius
change. This is a single eigenvalue clipping/rescaling operation, **not** a nearest
correlation optimizer. No model, validator or calibration automatically calls repair.

## Tests and limitations

`tests/unit/test_correlation.py` checks positive-definite reconstruction, invalid
structure/entries/non-PSD inputs, singular/roundoff policy and explicit repair evidence.
`tests/property/test_model_invariants.py` verifies two-factor reconstruction over
bounded correlations. Factor order is included in the hash. Repair changes assumptions
and requires reviewing the report. Statistical correlation estimation, joint paths,
correlation reproduction is implemented in Phase 4; exposure effects remain deferred.
Brownian-driver order and exact OU innovation covariance are described in
[Monte Carlo](MONTE_CARLO.md). See [ADR 0005](../decisions/0005-correlation-validation.md).
