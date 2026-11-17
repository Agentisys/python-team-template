from __future__ import annotations

from pathlib import Path

from example_project.stock import StockItem, load_stock, low_stock


def test_low_stock_sorted_by_shortfall() -> None:
    items = [
        StockItem("A-1", on_hand=10, reorder_level=5),
        StockItem("B-2", on_hand=2, reorder_level=5),
        StockItem("C-3", on_hand=5, reorder_level=5),
        StockItem("D-4", on_hand=0, reorder_level=8),
    ]
    assert [i.sku for i in low_stock(items)] == ["D-4", "B-2", "C-3"]


def test_load_stock_reads_csv(tmp_path: Path) -> None:
    path = tmp_path / "stock.csv"
    path.write_text("sku,on_hand,reorder_level\n A-1 ,3,5\n", encoding="utf-8")
    assert load_stock(path) == [StockItem("A-1", 3, 5)]
