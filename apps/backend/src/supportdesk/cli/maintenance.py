"""Supervised retention schedule for an always-running portfolio stack."""

import logging
import subprocess
import sys
import time


def main() -> None:
    while True:
        try:
            subprocess.run(
                [sys.executable, "-m", "supportdesk.cli.purge_expired"],
                check=True,
                timeout=300,
            )
        except (subprocess.SubprocessError, OSError):
            logging.error("Retention failed; will retry on the next hourly cycle")
        time.sleep(3600)


if __name__ == "__main__":
    main()
