from decimal import Decimal

from app.scenarios.liquidity_evaporation import reference_level_quantity, thin_quantity


def test_liquidity_thinning_uses_portable_binary_to_decimal_half_even_rounding() -> None:
    assert reference_level_quantity([1.1, 2.2, 3.3]) == 6.6
    assert thin_quantity(4.35) == Decimal("1.522")
    assert thin_quantity(0.3) == Decimal("0.2")
