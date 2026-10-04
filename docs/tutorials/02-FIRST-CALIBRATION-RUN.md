# Your first calibration run

## What we are fitting

The sample teaches three Q-model fits: Vasicek discount bonds, Hull–White European
bond options and Heston European calls. Data are generated from declared parameters,
not real market observations. This tests recovery, not actual trading calibration quality.

1. Install Parallax Risk with the locked development environment described in
   [local setup](../operations/LOCAL_SETUP.md).
2. Read `data/sample/phase3_calibration.json`. Every observation has a source with
   is_sample=true, explicit expiry/maturity in years and residual scale. Bounds and
   starting guesses differ from the generating parameters.
3. From the repository root run:

   ```sh
   python scripts/demo_calibration.py
   ```

4. Inspect each result's status, fitted_parameters and parameter_bounds (names/order).
   Compare against generating_parameters: Vasicek (.35,.055,.025), Hull–White
   (.18,.012), Heston (1.5,.045,.35,-.65,.035). Check raw RMSE in the stated value_unit
   and scaled RMSE after dividing each residual by scale. Residual sign is model minus quote.
5. Inspect optimizer_status/message, active_bounds and uncertainty. Success means
   local solver termination, not global optimality or model validation. A covariance
   of nearly zero on exact generated data is not a market confidence statement.
6. Preserve input_data_hash, configuration_hash, calibration_id and enclosing context.
   Changing source metadata, an observation or its scale alters the input hash. Changing
   solver settings/bounds changes the configuration hash. A seed is metadata here;
   calibration does not consume random draws.

## Follow the code

`scripts/demo_calibration.py` loads the sample, uses CalibrationRequest.to_domain(),
then CalibrationService.calibrate() with ScipyLeastSquares. Models supply instrument
values; the example contains no duplicated pricing formula. The full call path is
in [calibration workflow](../workflows/CALIBRATION_WORKFLOW.md).

`tests/quantitative/test_calibration.py` checks actual parameter recovery and failure
limits. `tests/integration/test_calibration_workflow.py` executes this script.
The [methodology](../methodology/CALIBRATION.md) explains bounds, units and uncertainty.
No random paths, exposure, XVA, global optimizer, persisted fit or market vendor is
present. Detailed assumptions are in the individual [model documents](../methodology/INDEX.md).
