"""Daily low-stock check.

    uv run --package example-project projects/example-project/jobs/low_stock.py \
        --input stock.csv --output output/low_stock.csv
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from example_project.stock import load_stock, low_stock, write_report
from team_utils import run_job

JOB_NAME = "example_project.low_stock"
log = logging.getLogger(JOB_NAME)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report stock at or below its reorder level.")
    parser.add_argument("--input", type=Path, required=True, help="stock export CSV")
    parser.add_argument("--output", type=Path, required=True, help="where to write the report")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    low = low_stock(load_stock(args.input))
    write_report(low, args.output)
    for item in low:
        log.warning("low stock", extra={"sku": item.sku, "shortfall": item.shortfall})
    log.info("low-stock check done", extra={"low_items": len(low), "path": str(args.output)})


if __name__ == "__main__":
    raise SystemExit(run_job(JOB_NAME, main))
