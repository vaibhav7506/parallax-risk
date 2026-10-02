import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_sample_ingestion_prices_bootstrap_and_sensitivities_replay():
    outputs = []
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/demo_deterministic.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        payload = json.loads(result.stdout)
        assert payload["project"] == "Parallax Risk"
        assert "SYNTHETIC SAMPLE" in payload["data_status"]
        assert len(payload["snapshot_hash"]) == 64
        assert len(payload["prices"]) == 4
        assert payload["fx_delta_per_spot_unit"] > 0
        assert all(abs(row["residual"]) <= 1e-12 for row in payload["bootstrap"]["diagnostics"])
        logs = [json.loads(line) for line in result.stderr.splitlines()]
        assert len(logs) == 8
        assert all(log["run_id"] == "phase2-synthetic-demo" for log in logs)
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1]
