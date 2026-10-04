# Local setup

Follow [DEVELOPMENT](../../DEVELOPMENT.md) for exact installation/check commands.
Use the project virtual environment, Python 3.12+, locked dependencies and editable
package installation. Package import does not load settings or open database connections.

The quickest financial learning path is `python scripts/demo_deterministic.py`:
it requires no database and reads a fixed labelled synthetic fixture. It prints
computed price/evidence JSON to stdout and safe workflow logs to stderr.

For model fitting run `python scripts/demo_calibration.py`. It uses sourced synthetic
discount/bond-option/European-call inputs and real SciPy objectives without a database
or random generator. Follow the [calibration tutorial](../tutorials/02-FIRST-CALIBRATION-RUN.md).

For operational API/CLI database checks, set explicit `PARALLAX_` environment settings.
Compose reads an untracked `.env` and passes settings; the library itself does not
auto-load that file. Replace `.env.example` placeholders and use an encoded URL.
Host API/CLI addresses differ from Compose's internal `postgres` hostname.

Do not connect tests to valuable production data. Use a separate test project and
ports with the [Docker lifecycle](DOCKER.md). No tables or migrations are currently
created; see [database scope](DATABASE.md). Service failures are described in
[troubleshooting](TROUBLESHOOTING.md).
