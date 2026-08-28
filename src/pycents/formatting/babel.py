import decimal
import re
from decimal import Decimal
from typing import Literal, cast

from babel.core import Locale
from babel.numbers import (
    UnsupportedNumberingSystemError,
    format_compact_currency,
    format_compact_decimal,
    format_currency,
    format_decimal,
    get_currency_name,
    get_currency_unit_pattern,
    parse_pattern,
)

from pycents._decimal import _enforce_precision
from pycents.currency import Currency
from pycents.exceptions import BackendConfigurationError, InvalidFormatSpecError
from pycents.rounding import RoundingMode, as_decimal_rounding

from .base_formatter import BaseFormatter
from .formatspec import FormatSpec

__all__ = ["BabelFormatter"]


def _format_compact_decimal(number: Decimal) -> tuple[Decimal, str]:
    """
    Format a number in compact form (e.g., 1,000 -> 1K, 1,000,000 -> 1M).
    """
    suffix = [1, 10**3, 10**6, 10**9, 10**12, 10**15]
    idx = 0
    while idx < len(suffix) - 1 and abs(number) >= 1000:
        number /= 1000
        idx += 1
    return number, str(suffix[idx])


def _swap_euro_with_custom_currency(
    amount: Decimal, result: str, currency: Currency, locale: str, spec: FormatSpec
) -> str:
    if spec.ccy_display == "hidden":
        return result
    elif spec.ccy_display == "symbol":
        result = result.replace("€", currency.symbol)
        result = result.replace("EUR", currency.ccy_code)
    elif spec.ccy_display == "iso":
        result = result.replace("EUR", currency.ccy_code)
    elif spec.ccy_display == "name":
        ccy_name = get_currency_name("EUR", amount, locale=locale)
        result = result.replace(ccy_name, currency.ccy_name.lower())
    return result


def _adapt_pattern_to_xcurrency_minor_unit(
    pattern: str, currency: Currency, trim_trailing_zeros: bool = False
) -> str:
    base_pattern = re.sub(r"\.[0-9#]+", "", pattern)
    char = "#" if trim_trailing_zeros else "0"
    fraction_part = "." + (char * currency.minor_units)

    # if currency is an ISO 4217 Currency and users
    # didn't request to trim insignificant zeros
    # do not change the pattern.
    if currency.is_iso and not trim_trailing_zeros:
        return pattern

    custom_pattern = re.sub(r"0([^0]*(?:;|$))", rf"0{fraction_part}\g<1>", base_pattern)

    return custom_pattern


def _format_currency_name(
    amount: Decimal,
    currency: Currency,
    locale: str,
    spec: FormatSpec,
    rounding: RoundingMode = RoundingMode.HALF_EVEN,
    numbering_system: str = "latn",
) -> str:
    code = "EUR" if not currency.is_iso else currency.ccy_code
    if spec.accounting:
        raise InvalidFormatSpecError(
            "Cannot display currency name while using accounting format."
        )
    if spec.compact:
        unit_pattern = get_currency_unit_pattern(currency.ccy_code, amount, locale)
        display_name = get_currency_name(code, count=amount, locale=locale)

        assert spec.compact_precision is not None
        with decimal.localcontext(
            decimal.Context(rounding=as_decimal_rounding(rounding))
        ):
            number = format_compact_decimal(
                amount,
                locale=locale,
                fraction_digits=spec.compact_precision,
                numbering_system=numbering_system,
            )
        return unit_pattern.format(number, display_name)
    else:
        return format_currency(
            amount,
            code,
            locale=locale,
            format_type="name",
            decimal_quantization=False,
            currency_digits=False,
            numbering_system=numbering_system,
        )


def _format_currency_symbol(
    amount: Decimal,
    currency: Currency,
    locale: str,
    spec: FormatSpec,
    rounding: RoundingMode = RoundingMode.HALF_EVEN,
    numbering_system: str = "latn",
) -> str:
    code = currency.ccy_code if currency.is_iso else "EUR"
    if spec.compact and spec.accounting:
        raise InvalidFormatSpecError("Cannot mix compact and accounting format display")
    if not spec.compact:
        fmt_type: Literal["standard", "accounting"] = (
            "accounting" if spec.accounting else "standard"
        )
        pattern = Locale.parse(locale).currency_formats[fmt_type].pattern
        pattern = _adapt_pattern_to_xcurrency_minor_unit(
            pattern, currency, spec.trim_trailing_zeros
        )
        return format_currency(
            amount,
            code,
            pattern,
            locale=locale,
            format_type=fmt_type,
            currency_digits=False,
            decimal_quantization=False,
            numbering_system=numbering_system,
        )
    else:
        assert spec.compact_precision is not None
        with decimal.localcontext(
            decimal.Context(rounding=as_decimal_rounding(rounding))
        ):
            result = format_compact_currency(
                amount,
                code,
                locale=locale,
                fraction_digits=spec.compact_precision,
                numbering_system=numbering_system,
            )
        return result


def _format_currency_iso(
    amount: Decimal,
    currency: Currency,
    locale: str,
    spec: FormatSpec,
    rounding: RoundingMode = RoundingMode.HALF_EVEN,
    numbering_system: str = "latn",
) -> str:
    if spec.compact and spec.accounting:
        raise InvalidFormatSpecError("Cannot mix compact and accounting format display")

    loc = Locale.parse(locale)
    if spec.compact:
        assert spec.compact_precision is not None
        amount, magnitude = _format_compact_decimal(amount)
        plural_form = loc.plural_form(amount)
        # Safe lookup for compact plural categories
        # Adapted from babel source code. #TODO exception handling
        compact_formats = loc.compact_currency_formats["short"]
        plural_dict = compact_formats.get(plural_form, compact_formats.get("other", {}))
        pattern = plural_dict.get(magnitude, compact_formats["other"][magnitude])
    else:
        fmt_type = "accounting" if spec.accounting else "standard"
        pattern = loc.currency_formats[fmt_type]

    pattern_str = pattern.pattern
    if spec.compact:
        assert spec.compact_precision is not None
        pattern_str = re.sub(
            r"(0+)(?!\.)", rf"\g<1>.{'0' * spec.compact_precision}", pattern_str
        )

    pattern_str = re.sub(r"¤+(?=[#0.,])", "¤¤\xa0", pattern_str)
    pattern_str = re.sub(r"(?<=[#0.,])¤+", "\xa0¤¤", pattern_str)
    pattern_str = re.sub(r"¤+", "¤¤", pattern_str)

    pattern_str = _adapt_pattern_to_xcurrency_minor_unit(
        pattern_str, currency, spec.trim_trailing_zeros
    )
    custom_pattern = parse_pattern(pattern_str)
    if spec.compact:
        assert spec.compact_precision is not None
        amount = _enforce_precision(amount, spec.compact_precision, rounding)

    # babel apply method is unannotated, this cast is necessary
    return cast(
        str,
        custom_pattern.apply(
            value=amount,
            locale=locale,
            currency=currency.ccy_code,
            currency_digits=False,
            decimal_quantization=False,
            group_separator=spec.group_separator,
            numbering_system=numbering_system,
        ),
    )


def _format_currency_hidden(
    amount: Decimal,
    currency: Currency,
    locale: str,
    spec: FormatSpec,
    rounding: RoundingMode = RoundingMode.HALF_EVEN,
    numbering_system: str = "latn",
) -> str:
    if spec.compact:
        assert spec.compact_precision is not None
        with decimal.localcontext(
            decimal.Context(rounding=as_decimal_rounding(rounding))
        ):
            str_amount = format_compact_decimal(
                amount,
                locale=locale,
                fraction_digits=spec.compact_precision,
                numbering_system=numbering_system,
            )
    else:
        str_amount = format_decimal(
            amount,
            locale=locale,
            decimal_quantization=False,
            group_separator=spec.group_separator,
            numbering_system=numbering_system,
        )
    if spec.accounting and amount < 0:
        str_amount = f"({str_amount.lstrip('-')})"
    return str_amount


_map_display_format = {
    "hidden": _format_currency_hidden,
    "symbol": _format_currency_symbol,
    "iso": _format_currency_iso,
    "name": _format_currency_name,
}


def _format_currency(
    amount: Decimal,
    currency: Currency,
    locale: str,
    spec: FormatSpec,
    rounding: RoundingMode = RoundingMode.HALF_EVEN,
    numbering_system: str = "latn",
) -> str:
    try:
        result = _map_display_format[spec.ccy_display](
            amount, currency, locale, spec, rounding, numbering_system
        )
    except KeyError:
        raise AssertionError(f"Invalid display option: {spec.ccy_display}") from None
    return result


class BabelFormatter(BaseFormatter):
    def __init__(self, locale: str = "") -> None:
        _locale = str(Locale.parse(locale) if locale else Locale.default())
        super().__init__(_locale)

    @property
    def locale(self) -> str:
        return str(self._locale)

    @locale.setter
    def locale(self, value: str) -> None:
        self._locale = str(Locale.parse(value))

    def _validate_numbering_system(self, value: str | None) -> None:
        pass

    def format(
        self,
        amount: Decimal,
        currency: Currency,
        spec: FormatSpec,
    ) -> str:
        numbering_system: str = (
            self.numbering_system if self.numbering_system is not None else "default"
        )
        try:
            result = _format_currency(
                amount, currency, self.locale, spec, self._rounding, numbering_system
            )
        except UnsupportedNumberingSystemError:
            raise BackendConfigurationError(
                f"Numbering system '{numbering_system}' is not supported "
                f"by the Babel backend for locale '{self.locale}'"
            ) from None
        if not currency.is_iso:
            result = _swap_euro_with_custom_currency(
                amount, result, currency, self.locale, spec
            )
        return result
