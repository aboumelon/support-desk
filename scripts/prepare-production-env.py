#!/usr/bin/env python3
"""Prepare private first-deployment settings without copying developer credentials."""

import argparse
import ipaddress
import json
import os
import re
import secrets
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True, help="Public HTTPS hostname only")
    parser.add_argument(
        "--trusted-proxy",
        action="append",
        help="Verified ingress IP/CIDR; repeat for multiple proxies",
    )
    parser.add_argument("--output", type=Path, default=Path(".env.production"))
    parser.add_argument("--release-id", help="Defaults to the current Git revision")
    args = parser.parse_args()
    domain = args.domain.strip().lower()
    labels = domain.split(".")
    if (
        len(domain) > 253
        or len(labels) < 2
        or any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in labels
        )
    ):
        parser.error("--domain requires a hostname without a scheme, path or port")
    proxies = args.trusted_proxy or ["127.0.0.1/32"]
    try:
        networks = [ipaddress.ip_network(value, strict=False) for value in proxies]
    except ValueError:
        parser.error("--trusted-proxy requires an IP address or CIDR")
    if any(network.prefixlen == 0 for network in networks):
        parser.error("Trust only specific ingress proxies, never all addresses")
    root = Path(__file__).resolve().parents[1]
    release = args.release_id
    if release is None:
        try:
            release = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except subprocess.CalledProcessError:
            parser.error("An exported source archive requires --release-id")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", release):
        parser.error("--release-id must be a valid image tag")
    owner, runtime = secrets.token_hex(32), secrets.token_hex(32)
    values = {
        "RELEASE_ID": release,
        "PUBLIC_BASE_URL": f"https://{domain}",
        "ALLOWED_ORIGINS": json.dumps([f"https://{domain}"]),
        "SESSION_SECRET": secrets.token_hex(32),
        "POSTGRES_OWNER_PASSWORD": owner,
        "MIGRATION_DATABASE_URL": (
            f"postgresql+psycopg://supportdesk_owner:{owner}@postgres:5432/supportdesk"
        ),
        "RUNTIME_DATABASE_URL": (
            f"postgresql+psycopg://supportdesk_runtime:{runtime}@postgres:5432/supportdesk"
        ),
        "GATEWAY_BIND_ADDRESS": "0.0.0.0",
        "EDGE_TRUSTED_PROXIES": " ".join(str(network) for network in networks),
    }
    lines = (root / "deploy/production.env.example").read_text().splitlines()
    content = []
    for line in lines:
        key = line.split("=", 1)[0]
        content.append(f"{key}={values[key]}" if key in values else line)
    try:
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        parser.error("Output already exists; existing database secrets were preserved")
    with os.fdopen(descriptor, "w") as output:
        output.write("\n".join(content) + "\n")
    print(f"Created {args.output} with private permissions (0600).")
    print("AI starts explicitly simulated; no developer credentials were copied.")
    if not args.trusted_proxy:
        print(
            "Verify EDGE_TRUSTED_PROXIES before public routing; bootstrap is private."
        )


if __name__ == "__main__":
    main()
