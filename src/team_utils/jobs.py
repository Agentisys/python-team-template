"""A standard wrapper for scheduled jobs.

    def main() -> None:
        ...

    if __name__ == "__main__":
        raise SystemExit(run_job("daily_report", main))

What it gives every job, for free:
  * logging configured (console and a rotating log file)
  * a "job started" line, and a "job finished" line with the duration
  * any exception logged with its full stack trace as "job failed"
  * exit code 0 on success and 1 on failure, so Windows Task Scheduler,
    cron and systemd all see the failure
"""

from __future__ import annotations

import time
from collections.abc import Callable

from team_utils.logging_setup import configure_logging


def run_job(name: str, func: Callable[[], object]) -> int:
    """Run `func` as the job called `name` and return a process exit code."""
    log = configure_logging(name)
    started = time.monotonic()
    log.info("job started", extra={"job": name})
    try:
        func()
    except Exception:
        log.exception(
            "job failed",
            extra={"job": name, "duration_s": round(time.monotonic() - started, 2)},
        )
        return 1
    log.info(
        "job finished",
        extra={"job": name, "duration_s": round(time.monotonic() - started, 2)},
    )
    return 0
