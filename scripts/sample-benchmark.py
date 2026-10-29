"""Sample the isolated benchmark's DB connections and API/dispatcher RSS."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import psycopg

parser = argparse.ArgumentParser()
parser.add_argument("--seconds", type=int, default=620)
parser.add_argument(
    "--output", type=Path, default=Path("docs/evidence/benchmark-utilization.json")
)
args = parser.parse_args()
started = time.monotonic()
samples = []
report = {
    "scope": "API/dispatcher process RSS sum includes shared pages; excludes PostgreSQL, Redis, k6 and demo services. DB collector connection excluded. Five-second samples are not continuous peak measurements.",
    "available_cpu_cores": len(os.sched_getaffinity(0)),
    "host_memory_total_kib": int(
        next(
            line.split()[1]
            for line in Path("/proc/meminfo").read_text().splitlines()
            if line.startswith("MemTotal:")
        )
    ),
    "samples": samples,
}
while time.monotonic() - started < args.seconds:
    groups = subprocess.run(
        ["pgrep", "-f", "^bash scripts/benchmark-services.sh$"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.splitlines()
    if not groups:
        break
    row = {"elapsed_seconds": round(time.monotonic() - started, 2)}
    with psycopg.connect(
        "postgresql://supportdesk:local-development-only@127.0.0.1:55432/supportdesk_benchmark"
    ) as db:
        row["database_connections"] = dict(
            db.execute(
                "select coalesce(state,'unknown'),count(*) from pg_stat_activity where datname='supportdesk_benchmark' and pid<>pg_backend_pid() group by state"
            ).fetchall()
        )
    total_rss = 0
    for line in subprocess.check_output(
        ["ps", "-eo", "pgid=,rss="], text=True
    ).splitlines():
        group, rss = line.split()
        if group in groups:
            total_rss += int(rss)
    row["application_rss_kib"] = total_rss
    samples.append(row)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    time.sleep(5)
print(f"Recorded {len(samples)} five-second utilization samples")
