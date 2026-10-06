"""Execute research notebooks with this interpreter and a workspace-local kernel spec."""

import json
import os
import sys
import time
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Save outputs only after successful execution; keep runtime files in ignored artifacts."""
    runtime = ROOT / "artifacts/local/phase4/notebook-runtime"
    specification = runtime / "kernels/parallax-phase4"
    specification.mkdir(parents=True, exist_ok=True)
    (specification / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                "display_name": "Parallax Risk project interpreter",
                "language": "python",
            }
        ),
        encoding="utf-8",
    )
    os.environ["JUPYTER_RUNTIME_DIR"] = str(runtime)
    os.environ["IPYTHONDIR"] = str(runtime / "ipython")
    os.environ["MPLCONFIGDIR"] = str(runtime / "matplotlib")
    manager = KernelSpecManager(kernel_dirs=[str(runtime / "kernels")])
    records = []
    for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
        notebook = nbformat.read(path, as_version=4)
        kernel = KernelManager(kernel_name="parallax-phase4", kernel_spec_manager=manager)
        client = NotebookClient(
            notebook,
            timeout=120,
            km=kernel,
            kernel_name="parallax-phase4",
            resources={"metadata": {"path": str(ROOT)}},
        )
        started = time.perf_counter()
        client.execute(cleanup_kc=True)
        duration = time.perf_counter() - started
        nbformat.validate(notebook)
        nbformat.write(notebook, path)
        records.append(
            {
                "path": str(path.relative_to(ROOT)),
                "seconds": duration,
                "code_cells": sum(cell.cell_type == "code" for cell in notebook.cells),
                "status": "passed",
                "interpreter": sys.executable,
            }
        )
    if not records:
        raise RuntimeError("No research notebooks found")
    report = {"project": "Parallax Risk", "executions": records}
    (ROOT / "artifacts/local/phase4/notebook-execution.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
