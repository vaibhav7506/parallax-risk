"""Run the full synthetic scenario against an explicitly configured authenticated API."""

import argparse
import json
import time
from pathlib import Path

from parallax_risk.application.service_demo import demonstrate
from parallax_risk.infrastructure.http_client import ServiceClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Parallax Risk synthetic service demonstration")
    parser.add_argument("--server", required=True)
    parser.add_argument("--credential-file", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--output", default="artifacts/local/phase12/demo")
    args = parser.parse_args()

    class PacedClient(ServiceClient):
        """Keep this demonstration below the default 120 requests/minute quota."""

        last_request = 0.0

        def _pause(self):
            time.sleep(max(0, 0.6 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()

        def request(self, *args, **kwargs):
            self._pause()
            return super().request(*args, **kwargs)

        def text(self, *args, **kwargs):
            self._pause()
            return super().text(*args, **kwargs)

    client = PacedClient(args.server, args.credential_file)
    result = demonstrate(client, args.subject, progress=lambda message: print(message, flush=True))
    target = Path(args.output)
    target.mkdir(parents=True, exist_ok=True)
    (target / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for key in result["report_ids"]:
        report = client.request("GET", "/v1/reports/" + str(key))
        (target / (str(key) + ".json")).write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        (target / (str(key) + ".html")).write_text(
            client.text("/v1/reports/" + str(key) + "/html"), encoding="utf-8"
        )
    for operation, job_id in result["jobs"].items():
        data = client.request("GET", "/v1/runs/" + str(job_id) + "/input")["data"]
        request = data["request"]
        payload = {"model_id": data["model_id"], "version_id": data["version_id"], **request}
        (target / (operation.replace("/", "-") + "-input.json")).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
    # HTML uses the same authenticated, immutable report object. Download with a
    # bounded adapter rather than permitting arbitrary client-supplied file paths.
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
