from decimal import Decimal
from functools import partial

import pytest

from pycents.currency import Currency
from pycents.exceptions import InvalidFormatSpecError
from pycents.formatting.formatspec import FormatSpec
from pycents.formatting.std_formatter import StdFormatter
from pycents.rounding import RoundingMode


class TestStdFormatter:
    @pytest.fixture
    def std_formatter(self):
        fmt = StdFormatter()
        _format = partial(
            fmt.format,
        )
        fmt.format = _format
        return fmt

    # Basic Currency Display Tests

    def test_locale_property(self, std_formatter):
        assert std_formatter.locale == ""

    @pytest.mark.parametrize(
        "display, amount, expected",
        [
            ("hidden", Decimal("1234.56"), "1,234.56"),
            ("iso", Decimal("1234.56"), "USD\xa01,234.56"),
            ("name", Decimal("1234.56"), "1,234.56 US Dollar"),
        ],
    )
    def test_currency_display_widths(self, std_formatter, display, amount, expected):
        spec = FormatSpec(ccy_display=display)
        result = std_formatter.format(amount, Currency.from_code("USD"), spec)
        assert result == expected

    def test_invalid_display_width_raises_error(self, std_formatter):
        spec = FormatSpec(ccy_display="invalid_type")  # type: ignore
        with pytest.raises(AssertionError):
            std_formatter.format(Decimal("100"), Currency.from_code("USD"), spec)

    def test_symbol_raises_invalid_format_spec_error(self, std_formatter):
        spec = FormatSpec(ccy_display="symbol")
        with pytest.raises(InvalidFormatSpecError):
            std_formatter.format(Decimal("-100"), Currency.from_code("USD"), spec)

    # Accounting Sign Tests

    @pytest.mark.parametrize(
        "amount, accounting, expected",
        [
            (Decimal("-1232.56"), False, "-1,232.56"),  # Standard Negative
            (Decimal("-1233.56"), True, "(1,233.56)"),  # Accounting Negative
            (Decimal("1234.56"), True, "1,234.56"),  # Accounting Positive (no parens)
        ],
    )
    def test_accounting_format(self, std_formatter, amount, accounting, expected):
        spec = FormatSpec(accounting=accounting, ccy_display="hidden")
        result = std_formatter.format(amount, Currency.from_code("USD"), spec)
        assert result == expected

    # Compact Notation Tests

    @pytest.mark.parametrize(
        "amount, expected",
        [
            (Decimal("1500"), "USD\xa01.5K"),
            (Decimal("1500000"), "USD\xa01.5M"),
            (Decimal("1500000000"), "USD\xa01.5B"),
        ],
    )
    def test_compact_notation_positive(self, std_formatter, amount, expected):
        spec = FormatSpec(compact=True, ccy_display="iso")
        result = std_formatter.format(amount, Currency.from_code("USD"), spec)
        assert result == expected

    @pytest.mark.parametrize(
        "amount,ccy_display,expected",
        [
            (Decimal("-2500000"), "iso", "(USD\xa02.5M)"),
            (Decimal("-2500000"), "hidden", "(2.5M)"),
            (Decimal("-2500000"), "name", "(2.5M US Dollar)"),
        ],
    )
    def test_compact_accounting_negative(
        self, std_formatter, amount, ccy_display, expected
    ):

        spec = FormatSpec(compact=True, accounting=True, ccy_display=ccy_display)
        result = std_formatter.format(amount, Currency.from_code("USD"), spec)

        assert result == expected

    # Grouping Separators

    @pytest.mark.parametrize(
        "group_sep, expected",
        [
            (True, "1,234,567.89"),
            (False, "1234567.89"),
        ],
    )
    def test_group_separator(self, std_formatter, group_sep, expected):
        spec = FormatSpec(group_separator=group_sep, ccy_display="hidden")
        result = std_formatter.format(
            Decimal("1234567.89"), Currency.from_code("USD"), spec
        )
        assert result == expected

    # Rounding Policies

    @pytest.mark.parametrize(
        "amount, policy, expected",
        [
            (Decimal("12340"), RoundingMode.DOWN, "12.34K"),
            (Decimal("12345"), RoundingMode.UP, "12.35K"),
            (
                Decimal("12345"),
                RoundingMode.HALF_EVEN,
                "12.34K",
            ),
            (
                Decimal("12355"),
                RoundingMode.HALF_EVEN,
                "12.36K",
            ),
            (
                Decimal("12345"),
                RoundingMode.HALF_UP,
                "12.35K",
            ),
        ],
    )
    def test_rounding_policies(self, std_formatter, amount, policy, expected):
        spec = FormatSpec(ccy_display="hidden", compact=True, compact_precision=2)
        std_formatter._rounding = policy
        result = std_formatter.format(amount, Currency.from_code("USD"), spec)
        assert result == expected

    def test_configure(self, std_formatter):
        std_formatter.configure(
            ccy_display="iso",
            compact=True,
            compact_precision=3,
            accounting=True,
            group_separator=False,
        )
        expected = FormatSpec(
            ccy_display="iso",
            compact=True,
            compact_precision=3,
            accounting=True,
            group_separator=False,
        )

        assert std_formatter._default_spec == expected

    @pytest.mark.parametrize(
        "display, amount, expected",
        [
            ("hidden", Decimal("23876"), "23876"),
            ("iso", Decimal("23876"), "TST\xa023876"),
            ("name", Decimal("23876"), "23876 test coin"),
        ],
    )
    def test_custom_currency_formatting(self, display, amount, expected, std_formatter):
        result = std_formatter.format(
            amount,
            Currency.from_code("TST"),
            FormatSpec(ccy_display=display, group_separator=False),
        )

        assert result == expected
