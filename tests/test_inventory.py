"""Stock helpers.

Some of these tests already pass. The red ones point at real bugs in
`src/shop/inventory.py` - read the failure, fix the code, keep the test as is.
"""

from shop.inventory import (
    available_units,
    low_stock_items,
    reserve_units,
    write_off,
)


def test_available_units_returns_stored_count() -> None:
    assert available_units({"SKU-1": 3}, "SKU-1") == 3


def test_available_units_returns_zero_for_unknown_sku() -> None:
    assert available_units({"SKU-1": 3}, "SKU-404") == 0


def test_reserve_units_moves_units_out_of_stock() -> None:
    stock = {"SKU-1": 10}
    ledger = reserve_units(stock, {"sku": "SKU-1", "qty": "4"}, None)
    assert stock == {"SKU-1": 6}
    assert ledger == {"SKU-1": 4}


def test_reserve_units_starts_from_an_empty_ledger() -> None:
    reserve_units({"SKU-1": 10}, {"sku": "SKU-1", "qty": "4"}, None)
    ledger = reserve_units({"SKU-1": 10}, {"sku": "SKU-1", "qty": "4"}, None)
    assert ledger == {"SKU-1": 4}


def test_low_stock_items_ignores_threshold_itself() -> None:
    stock = {"SKU-1": 9, "SKU-2": 10, "SKU-3": 11}
    assert low_stock_items(stock, threshold=10) == ["SKU-1"]


def test_low_stock_items_is_sorted() -> None:
    stock = {"SKU-3": 1, "SKU-1": 2, "SKU-2": 3}
    assert low_stock_items(stock, threshold=10) == ["SKU-1", "SKU-2", "SKU-3"]


def test_write_off_reduces_stock() -> None:
    stock = {"SKU-1": 10}
    write_off(stock, "SKU-1", 4)
    assert stock == {"SKU-1": 6}


def test_write_off_drops_sku_when_nothing_is_left() -> None:
    stock = {"SKU-1": 3}
    write_off(stock, "SKU-1", 3)
    assert stock == {}
