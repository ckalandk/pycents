import decimal
from typing import Any

import icu as _icu

from pycents._decimal import _trim_trailing_zeros
from pycents.currency import Currency
from pycents.exceptions import BackendConfigurationError, InvalidFormatSpecError
from pycents.rounding import RoundingMode

from .base_formatter import BaseFormatter
from .formatspec import FormatSpec

icu: Any = _icu

_icu_rounding_map = {
    RoundingMode.CEILING: icu.DecimalFormat.kRoundCeiling,  #
    RoundingMode.FLOOR: icu.DecimalFormat.kRoundFloor,  #
    RoundingMode.DOWN: icu.DecimalFormat.kRoundDown,  #
    RoundingMode.UP: icu.DecimalFormat.kRoundUp,  #
    RoundingMode.HALF_EVEN: icu.DecimalFormat.kRoundHalfEven,  #
    RoundingMode.HALF_DOWN: icu.DecimalFormat.kRoundHalfDown,  #
    RoundingMode.HALF_UP: icu.DecimalFormat.kRoundHalfUp,  #
    RoundingMode.HALF_ODD: icu.UNumberFormatRoundingMode.HALF_ODD,
    RoundingMode.HALF_CEILING: icu.UNumberFormatRoundingMode.HALF_CEILING,
    RoundingMode.HALF_FLOOR: icu.UNumberFormatRoundingMode.HALF_FLOOR,
    RoundingMode.UNNECESSARY: icu.UNumberFormatRoundingMode.UNNECESSARY,
}


def _get_currency_display_part(
    amount: decimal.Decimal, locale: str, currency: Currency
) -> str:
    ccy_formatter = (
        icu.NumberFormatter.withLocale(icu.Locale(locale))
        .unit(icu.CurrencyUnit("EUR"))
        .unitWidth(icu.UNumberUnitWidth.FULL_NAME)
    )

    number_formatter = icu.NumberFormatter.withLocale(icu.Locale(locale))

    precision_rule = icu.Precision.fixedFraction(currency.minor_units)
    number_formatter = number_formatter.precision(precision_rule)
    ccy_display = str(ccy_formatter.formatDecimal(str(amount).encode("utf-8")).strip())
    ccy_display = ccy_display.replace("€", "").strip()
    number = str(number_formatter.formatDecimal(str(amount).encode("utf-8")).strip())
    result = ccy_display.strip(number).strip()
    return result


def _normalize_xcurrency_display(
    currency: Currency, locale: str, result: str, spec: FormatSpec
) -> str:
    assert not currency.is_iso
    if spec.ccy_display == "symbol":
        result = result.replace("€", currency.symbol)
        # Some locales use EUR code instead of the symbol € for displaying
        # even if the formatter was build explicitly to use currency symbol
        result = result.replace("EUR", currency.ccy_code)
    elif spec.ccy_display == "iso":
        result = result.replace("EUR", currency.ccy_code)
    else:
        pass
    return result


def _build_icu_currency_formatter(
    currency: Currency, locale: str, spec: FormatSpec, rounding: RoundingMode
) -> icu.NumberFormatter:  # pyright: ignore[reportInvalidTypeForm, type]
    """
    Returns an ICU NumberFormatter configured for specific financial layouts.
    """
    if spec.ccy_display == "name" and spec.accounting:
        raise InvalidFormatSpecError(
            "Accounting format is not supported with currency name display."
        )

    # Common formatter setup. When the currency is a custom currency
    # we use EUR as a placeholder currency, and replace the formatted
    # result symbol/code/name with the corresponding currency datas.
    if not currency.is_iso:
        iso_code = "EUR"
    else:
        iso_code = currency.ccy_code

    formatter = icu.NumberFormatter.withLocale(icu.Locale(locale)).unit(
        icu.CurrencyUnit(iso_code)
    )

    # Apply currency display
    display_widths = {
        "hidden": icu.UNumberUnitWidth.HIDDEN,
        "symbol": icu.UNumberUnitWidth.SHORT,
        "iso": icu.UNumberUnitWidth.ISO_CODE,
        "name": icu.UNumberUnitWidth.FULL_NAME,
    }

    if spec.ccy_display not in display_widths:
        raise InvalidFormatSpecError(f"Unknown format field {spec.ccy_display}")

    formatter = formatter.unitWidth(display_widths[spec.ccy_display])

    # Apply number presentation
    if spec.accounting:
        formatter = formatter.sign(icu.UNumberSignDisplay.ACCOUNTING)
    else:
        formatter = formatter.sign(icu.UNumberSignDisplay.AUTO)

    if spec.compact:
        formatter = formatter.notation(icu.Notation.compactShort())
        precision = spec.compact_precision
    else:
        precision = currency.minor_units

    if spec.trim_trailing_zeros:
        precision_rule = icu.Precision.minMaxFraction(0, precision)
    else:
        precision_rule = icu.Precision.fixedFraction(precision)

    formatter = formatter.precision(precision_rule)

    # Apply decimal rounding strategy
    try:
        icu_rounding = _icu_rounding_map[rounding]
    except KeyError:
        raise AssertionError(f"Missing ICU mapping for {rounding}") from None
    formatter = formatter.roundingMode(icu_rounding)

    # Apply group separator
    if not spec.group_separator:
        formatter = formatter.grouping(icu.UNumberGroupingStrategy.OFF)
    else:
        formatter = formatter.grouping(icu.UNumberGroupingStrategy.AUTO)

    return formatter


class IcuFormatter(BaseFormatter):
    def __init__(self, locale: str = "") -> None:
        _locale = str(icu.Locale(locale) if locale else icu.Locale.getDefault())
        super().__init__(_locale)

    @property
    def locale(self) -> str:
        return self._locale

    @locale.setter
    def locale(self, value: str) -> None:
        self._locale = str(icu.Locale(value))

    def _validate_numbering_system(self, value: str | None) -> None:
        _valid_icu_numbering_system = set(icu.NumberingSystem.getAvailableNames())
        if value is not None and value not in _valid_icu_numbering_system:
            raise BackendConfigurationError(
                f"ICU backend expected a valid numbering system: got '{value}'"
            )

    @property
    def _icu_locale_string(self) -> str:
        if self.numbering_system is not None:
            return f"{self._locale}@numbers={self.numbering_system}"
        return self._locale

    def format(
        self,
        amount: decimal.Decimal,
        currency: Currency,
        spec: FormatSpec,
    ) -> str:
        formatter = _build_icu_currency_formatter(
            currency, self._icu_locale_string, spec, self._rounding
        )

        # Important! we need to trim insignificant zeros
        # from amount before passing it to format method
        # otherwise pyicu will still display keep them!
        if spec.trim_trailing_zeros:
            amount = _trim_trailing_zeros(amount)
        # Adapt precision display to the number of decimals
        # of amount.
        # In compact notation, the precision is controlled by spec.compact_prrecision
        if not spec.compact:
            exp = amount.as_tuple().exponent
            assert isinstance(exp, int)
            exact_places = abs(exp)
            precision_rule = icu.Precision.fixedFraction(exact_places)
            formatter = formatter.precision(precision_rule)

        str_result = str(formatter.formatDecimal(str(amount).encode("utf-8")).strip())
        if not currency.is_iso:
            if spec.ccy_display == "name":
                ccy_part = _get_currency_display_part(amount, self.locale, currency)
                str_result = str_result.replace(
                    ccy_part, currency.ccy_name.lower()
                ).replace("€", currency.symbol)
            else:
                str_result = _normalize_xcurrency_display(
                    currency, self.locale, str_result, spec
                )
        if spec.accounting and spec.compact and amount < 0:
            # ICU/CLDR does not define accounting formatting for compact notation.
            # or maybe i am wrong???
            # We emulate it by formatting the absolute value and surrounding it
            # with parentheses. we strip the result to avoid extra spaces that may arise
            # when the currency symbol is hidden
            # TODO: This needs to be extensively tested across locales to ensure
            # it behaves as expected.
            str_result = str_result.replace("-", "")
            return f"({str_result.strip()})"
        # The returned formatted string stripped from leading/trailing whitespace
        # to avoid issues when using hidden currency symbols format in compact notation.
        return str_result.strip()
