"""
Unit normalisation for prices.

Prices are stored per base unit (per gram / ml / each), so costing never
converts anything. People don't think that way, though: invoices say
"£93.60 for 12 x 1 kg". This converts a pack price into a base-unit price
at the moment it's entered. Every price input path should go through here.
"""

from models import UnitType

# Pack unit -> (the base unit it measures, how many base units it contains)
PACK_UNITS = {
    "kg": (UnitType.GRAM, 1000),
    "g": (UnitType.GRAM, 1),
    "l": (UnitType.ML, 1000),
    "ml": (UnitType.ML, 1),
    "each": (UnitType.EACH, 1),
}


def price_per_base_unit(pack_price: float, pack_quantity: float, pack_unit: str,
                        ingredient_unit: UnitType) -> float:
    """
    £93.60 for 12 kg of a gram-priced ingredient -> 93.60 / 12,000 g = £0.0078/g.

    Raises ValueError if the pack unit doesn't measure the same thing as the
    ingredient (e.g. litres for something priced by weight), or the numbers are
    impossible.
    """
    if pack_unit not in PACK_UNITS:
        raise ValueError(f"Unknown unit '{pack_unit}'. Use one of: {', '.join(PACK_UNITS)}")
    base_unit, base_units_per_pack_unit = PACK_UNITS[pack_unit]
    if base_unit != ingredient_unit:
        raise ValueError(f"This ingredient is measured in {ingredient_unit.value}, so '{pack_unit}' doesn't fit")
    if pack_quantity <= 0:
        raise ValueError("Pack quantity must be more than 0")
    if pack_price < 0:
        raise ValueError("Price can't be negative")

    return pack_price / (pack_quantity * base_units_per_pack_unit)
