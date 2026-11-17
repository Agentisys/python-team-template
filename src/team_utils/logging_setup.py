"""Logging that every script shares.

    log = configure_logging("daily_report")
    log.info("rows loaded", extra={"rows": 120})

Writes to:
  * the console
  * a rotating file per job in LOG_DIR (default logs/, 5 MB x 5 files), so a
    3 a.m. failure leaves something to read on the server
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from team_utils.config import get_settings

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_configured = False


def configure_logging(job_name: str) -> logging.Logger:
    """Set up logging once per process and return a logger named after the job."""
    global _configured
    if _configured:
        return logging.getLogger(job_name)

    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    formatter = logging.Formatter(_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    settings.log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        settings.log_dir / f"{job_name}.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Quieten chatty Azure SDK HTTP logging; our own messages stay at LOG_LEVEL.
    logging.getLogger("azure").setLevel(logging.WARNING)

    _configured = True

    log = logging.getLogger(job_name)
    log.debug("logging configured (env=%s, dir=%s)", settings.app_env, settings.log_dir)
    return log


def reset_logging_for_tests() -> None:
    """Remove handlers so each test starts clean. Not for use in scripts."""
    global _configured
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    _configured = False
