from decimal import Decimal

from pycents.rounding import RoundingMode, as_decimal_rounding


def _decimal_places(x: Decimal) -> int:
    """
    Return the number of significant decimal places in a Decimal number.
    """
    if x.is_zero():
        return 0

    exponent = x.normalize().as_tuple().exponent

    assert isinstance(exponent, int)
    return abs(exponent) if exponent < 0 else 0


def _trim_trailing_zeros(value: Decimal) -> Decimal:
    """
    Removes trailing fractional zeroes from a Decimal .
    """
    if value == value.to_integral():
        cleaned = value.quantize(Decimal("1"))
    else:
        cleaned = value.normalize()
    return cleaned


def _enforce_precision(
    value: Decimal, precision: int, rounding: RoundingMode
) -> Decimal:
    return value.quantize(
        Decimal(f"1.{'0' * precision}"), rounding=as_decimal_rounding(rounding)
    )


def _force_decimal(value: int | str | Decimal) -> Decimal:
    if not isinstance(value, Decimal):
        return Decimal(value)
    return value
