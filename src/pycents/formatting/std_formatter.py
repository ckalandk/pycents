from decimal import Decimal

from pycents._decimal import _enforce_precision, _trim_trailing_zeros
from pycents.currency import Currency
from pycents.exceptions import InvalidFormatSpecError

from .base_formatter import BaseFormatter
from .formatspec import FormatSpec

__all__ = ["StdFormatter"]


def _format_compact_decimal(number: Decimal) -> tuple[Decimal, str]:
    """
    Format a number in compact form (e.g., 1,000 -> 1K, 1,000,000 -> 1M).
    """
    suffix = ["", "K", "M", "B", "T", "Q"]  # 10^3, 10^6, 10^9, 10^12, 10^15
    idx = 0
    while idx < len(suffix) - 1 and abs(number) >= 1000:
        number /= 1000
        idx += 1
    return number, suffix[idx]


def _get_currency_code(currency: Currency, display_option: str) -> str:
    _map_display = {
        "iso": currency.ccy_code,
        "name": currency.ccy_name,
        "hidden": "",
    }
    try:
        symbol = _map_display[display_option]
        return symbol
    except KeyError:
        raise AssertionError(
            f"Invalid currency display option: {display_option}. "
        ) from None


class StdFormatter(BaseFormatter):
    def __init__(self, locale: str = "") -> None:
        super().__init__(locale)
        self._default_spec = FormatSpec(ccy_display="iso")

    def _validate_numbering_system(self, value: str | None) -> None:  # pragma: no cover
        pass

    def format(
        self,
        amount: Decimal,
        currency: Currency,
        spec: FormatSpec,
    ) -> str:
        if spec.ccy_display == "symbol":
            raise InvalidFormatSpecError(
                f"{type(self).__name__} doesn't support symbol currency display."
                "Use IcuFormatter or BabelFormatter instead."
            )

        symbol = _get_currency_code(currency, spec.ccy_display)
        if not currency.is_iso and spec.ccy_display == "name":
            symbol = symbol.lower()

        if spec.ccy_display == "name":
            format_type = "{sign}{number}{suffix} {currency}"
        elif spec.ccy_display == "iso":
            format_type = "{sign}{currency}\xa0{number}{suffix}"
        else:
            format_type = "{sign}{number}{suffix}{currency}"

        suffix = ""  # K, M, B...

        if spec.compact:
            amount, suffix = _format_compact_decimal(amount)
            if spec.compact_precision is not None:
                amount = _enforce_precision(
                    amount, spec.compact_precision, self._rounding
                )

        if spec.trim_trailing_zeros:
            amount = _trim_trailing_zeros(amount)

        if amount < 0:
            sign = "-"
            amount = abs(amount)
        else:
            sign = ""

        if spec.group_separator:
            number = format(amount, ",")
        else:
            number = format(amount, "f")

        result = format_type.format(
            sign=sign, number=number, currency=symbol, suffix=suffix
        )
        if spec.accounting and sign == "-":
            result = result.lstrip("-")
            result = f"({result})"

        return result
