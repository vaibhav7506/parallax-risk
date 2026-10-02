"""Support python -m parallax_risk without starting services on import."""

from parallax_risk.cli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
