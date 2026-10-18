"""CLI service commands share the authenticated application boundaries."""

from __future__ import annotations

import argparse
import json
import time
from urllib.parse import quote, urlencode

from parallax_risk.common.errors import InfrastructureError
from parallax_risk.infrastructure.http_client import ServiceClient, read_json

SUBMIT = {
    "price-trade": "pricing/trades",
    "price-portfolio": "pricing/portfolios",
    "simulate": "simulation",
    "exposure": "exposure",
    "xva": "xva",
    "capital": "capital",
    "calibrate": "market/calibrations",
    "bootstrap-curve": "market/curves",
    "compare": "validation/comparison",
    "convergence": "validation/convergence",
    "invariants": "validation/invariants",
    "sensitivity": "validation/sensitivity",
    "stress": "validation/stress",
    "uncertainty": "validation/uncertainty",
    "mutate": "validation/mutation",
    "adversarial": "validation/adversarial",
}


def add_commands(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    for name in (*SUBMIT, "ingest", "governance-write", "report", "query"):
        parser = commands.add_parser(name, help="Authenticated service workflow")
        parser.add_argument("--server", required=True)
        parser.add_argument("--credential-file", required=True)
        if name in SUBMIT:
            parser.add_argument("--input", required=True, help="Strict schema-1 JobInput JSON")
            parser.add_argument("--idempotency-key", required=True)
            parser.add_argument("--wait-seconds", type=float, default=0)
        elif name == "query":
            parser.add_argument("--path", required=True, help="Versioned /v1/ read path")
            parser.add_argument("--after", default="")
            parser.add_argument("--limit", type=int, default=None)
        else:
            parser.add_argument("--input", required=True)
            if name == "ingest":
                parser.add_argument(
                    "--kind",
                    choices=(
                        "market",
                        "portfolio",
                        "counterparty",
                        "netting-set",
                        "csa",
                        "scenario",
                        "pricing-context",
                    ),
                    required=True,
                )


def run(args: argparse.Namespace) -> None:
    client = ServiceClient(args.server, args.credential_file)
    if args.command in SUBMIT:
        if not 0 <= args.wait_seconds <= 300:
            raise InfrastructureError("Wait budget must be in [0,300] seconds")
        result = client.request(
            "POST",
            "/v1/" + SUBMIT[args.command],
            read_json(args.input),
            idempotency_key=args.idempotency_key,
        )
        if args.wait_seconds:
            data = result.get("data") if isinstance(result, dict) else None
            if not isinstance(data, dict):
                raise InfrastructureError("Invalid service submission response")
            key = data.get("job_id")
            if not isinstance(key, str):
                raise InfrastructureError("Missing service job identifier")
            deadline = time.monotonic() + args.wait_seconds
            while time.monotonic() < deadline:
                status = client.request("GET", "/v1/runs/" + quote(key, safe=""))
                data = status.get("data") if isinstance(status, dict) else None
                if not isinstance(data, dict):
                    raise InfrastructureError("Invalid job status response")
                state = data.get("status")
                if state == "failed":
                    raise InfrastructureError("Service computation failed; inspect retained job")
                if state == "succeeded":
                    result = client.request("GET", "/v1/runs/" + quote(key, safe="") + "/result")
                    break
                time.sleep(min(0.1, max(0, deadline - time.monotonic())))
            else:
                raise InfrastructureError("Wait budget elapsed; durable job remains available")
    elif args.command == "query":
        path = args.path
        if args.limit is not None:
            if not 1 <= args.limit <= 100 or "?" in path:
                raise InfrastructureError("Invalid query page")
            path += "?" + urlencode({"after": args.after, "limit": args.limit})
        result = client.request("GET", path)
    else:
        path = {"governance-write": "governance", "report": "reports"}.get(args.command)
        if args.command == "ingest":
            path = {
                "market": "market/snapshots",
                "portfolio": "portfolios",
                "counterparty": "counterparties",
                "netting-set": "netting-sets",
                "csa": "csas",
                "scenario": "market/scenarios",
                "pricing-context": "market/pricing-contexts",
            }[args.kind]
        result = client.request("POST", "/v1/" + str(path), read_json(args.input))
    print(json.dumps(result, allow_nan=False, sort_keys=True))
