import ast
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "parallax_risk"


def test_core_and_application_dependency_direction():
    for layer, forbidden in (
        (
            "common",
            {
                "fastapi",
                "pydantic",
                "pydantic_settings",
                "sqlalchemy",
                "parallax_risk.api",
                "parallax_risk.application",
                "parallax_risk.infrastructure",
            },
        ),
        (
            "application",
            {"fastapi", "sqlalchemy", "parallax_risk.api", "parallax_risk.infrastructure"},
        ),
    ):
        for path in (PACKAGE / layer).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            for imported in imports:
                assert not any(
                    imported == item or imported.startswith(item + ".") for item in forbidden
                ), path


def test_imports_are_silent_and_do_not_read_environment_or_create_engines():
    code = """
import contextlib, importlib, io, pkgutil, os
import sqlalchemy, structlog

def forbidden(*args, **kwargs):
    raise AssertionError("Import-time dependency initialization")

sqlalchemy.create_engine = forbidden
structlog.configure = forbidden
import pydantic_settings
pydantic_settings.BaseSettings.__init__ = forbidden
import parallax_risk
stream = io.StringIO()
with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
    for module in pkgutil.walk_packages(parallax_risk.__path__, parallax_risk.__name__ + "."):
        importlib.import_module(module.name)
assert stream.getvalue() == "", stream.getvalue()
"""
    environment = dict(os.environ)
    environment["PARALLAX_DEFAULT_SEED"] = "INVALID-IF-LOADED"
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=environment,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


def test_module_cli_starts():
    result = subprocess.run(
        [sys.executable, "-m", "parallax_risk", "version"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0
    assert '"name": "Parallax Risk"' in result.stdout


def test_package_and_build_metadata_versions_match():
    import tomllib
    from importlib.metadata import version

    from parallax_risk import __version__

    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["version"] == __version__ == version("parallax-risk")
    assert (PACKAGE / "py.typed").is_file()
