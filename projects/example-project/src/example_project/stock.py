"""Find stock items at or below their reorder level."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StockItem:
    sku: str
    on_hand: int
    reorder_level: int

    @property
    def shortfall(self) -> int:
        return max(self.reorder_level - self.on_hand, 0)


def load_stock(path: Path) -> list[StockItem]:
    """Read the stock export: columns sku, on_hand, reorder_level."""
    with path.open(newline="", encoding="utf-8") as fh:
        return [
            StockItem(row["sku"].strip(), int(row["on_hand"]), int(row["reorder_level"]))
            for row in csv.DictReader(fh)
        ]


def low_stock(items: list[StockItem]) -> list[StockItem]:
    """Items at or below their reorder level, biggest shortfall first."""
    low = [item for item in items if item.on_hand <= item.reorder_level]
    return sorted(low, key=lambda item: (-item.shortfall, item.sku))


def write_report(items: list[StockItem], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["sku", "on_hand", "reorder_level", "shortfall"])
        for item in items:
            writer.writerow([item.sku, item.on_hand, item.reorder_level, item.shortfall])
