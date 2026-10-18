"""Create fresh local opaque credentials; never print a secret or overwrite a file."""

import argparse
import hashlib
import json
import secrets
from pathlib import Path

from parallax_risk.application.access import Principal, Role


def main() -> None:
    parser = argparse.ArgumentParser(description="Parallax Risk local credential provisioning")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--roles", nargs="+", choices=[r.value for r in Role], required=True)
    parser.add_argument("--output", default="artifacts/local/service-credentials")
    args = parser.parse_args()
    principal = Principal(args.subject, frozenset(Role(role) for role in args.roles))
    target = Path(args.output)
    target.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(48)
    credential = target / "api-key.txt"
    configuration = target / "credentials.json"
    if credential.exists() or configuration.exists():
        parser.error("Credential output already exists; choose a fresh directory")
    with credential.open("x", encoding="ascii") as stream:
        stream.write(token + "\n")
    credential.chmod(0o600)
    with configuration.open("x", encoding="utf-8") as stream:
        json.dump(
            [
                {
                    "sha256": hashlib.sha256(token.encode()).hexdigest(),
                    "subject": principal.subject,
                    "roles": sorted(r.value for r in principal.roles),
                }
            ],
            stream,
        )
    print(
        json.dumps(
            {
                "credential_file": str(credential.resolve()),
                "digest_configuration_file": str(configuration.resolve()),
            }
        )
    )


if __name__ == "__main__":
    main()
