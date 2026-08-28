from decimal import Decimal

import pytest

icu = pytest.importorskip("icu")

# ruff: isort: split
from pycents.currency import Currency  # noqa: E402
from pycents.exceptions import (  # noqa: E402
    BackendConfigurationError,
    InvalidFormatSpecError,
)
from pycents.formatting.formatspec import FormatSpec  # noqa: E402
from pycents.formatting.pyicu import (  # noqa: E402
    IcuFormatter,
    _get_currency_display_part,
)
from pycents.rounding import RoundingMode  # noqa: E402


def normalize_space(s: str) -> str:
    """Helper to convert ICU non-breaking spaces into regular spaces."""
    return s.replace("\xa0", " ").replace("\u202f", " ")


def indexof(text: str, substr: str):
    try:
        ind = text.index(substr)
        return ind
    except ValueError:
        return -1


class TestIcuFormatter:
    @pytest.fixture
    def usd_formatter(self):
        fmt = IcuFormatter(locale="en_US")
        return fmt

    @pytest.fixture
    def eur_formatter_fr(self):
        fmt = IcuFormatter(locale="fr_FR")
        return fmt

    @pytest.fixture
    def usd(self):
        return Currency.from_code("USD")

    def test_locale_setter(self, usd_formatter, usd):
        assert usd_formatter.locale == "en_US"

        spec = FormatSpec()
        result = usd_formatter.format(Decimal("2.99"), usd, spec)
        assert result == "$2.99"

        usd_formatter.locale = "fr_FR"
        assert usd_formatter.locale == "fr_FR"

        result = usd_formatter.format(Decimal("2.99"), usd, spec)
        assert result == "2,99\xa0$US"

    # Basic Currency Display Tests

    @pytest.mark.parametrize(
        "display, amount, expected",
        [
            ("symbol", Decimal("1234.56"), "$1,234.56"),
            ("hidden", Decimal("1234.56"), "1,234.56"),
            ("iso", Decimal("1234.56"), "USD 1,234.56"),
            ("name", Decimal("1234.56"), "1,234.56 US dollars"),
        ],
    )
    def test_currency_display_widths(
        self, usd_formatter, display, amount, expected, usd
    ):
        spec = FormatSpec(ccy_display=display)
        result = usd_formatter.format(amount, usd, spec)
        assert normalize_space(result) == expected

    def test_invalid_display_width_raises_error(self, usd_formatter, usd):
        spec = FormatSpec(ccy_display="invalid_type")  # type: ignore
        with pytest.raises(InvalidFormatSpecError):
            usd_formatter.format(Decimal("100"), usd, spec)

    def test_name_and_accounting_raises_value_error(self, usd_formatter, usd):
        spec = FormatSpec(ccy_display="name", accounting=True)
        with pytest.raises(InvalidFormatSpecError):
            usd_formatter.format(Decimal("-100"), usd, spec)

    # Accounting Sign Tests

    @pytest.mark.parametrize(
        "amount, display, accounting, expected",
        [
            (Decimal("-1234.56"), "symbol", False, "-$1,234.56"),
            (Decimal("-1234.56"), "symbol", True, "($1,234.56)"),
            (Decimal("-1234.56"), "iso", True, "(USD 1,234.56)"),
            (Decimal("1234.56"), "iso", True, "USD 1,234.56"),
        ],
    )
    def test_accounting_format(
        self, usd_formatter, amount, display, accounting, expected, usd
    ):
        spec = FormatSpec(ccy_display=display, accounting=accounting)
        result = usd_formatter.format(amount, usd, spec)
        assert normalize_space(result) == expected

    # Compact Notation Tests

    @pytest.mark.parametrize(
        "amount, expected",
        [
            (Decimal("1500"), "$1.5K"),
            (Decimal("1500000"), "$1.5M"),
            (Decimal("1500000000"), "$1.5B"),
        ],
    )
    def test_compact_notation_positive(self, usd_formatter, amount, expected, usd):
        spec = FormatSpec(compact=True, compact_precision=1)
        result = usd_formatter.format(amount, usd, spec)
        assert normalize_space(result) == expected

    def test_compact_accounting_negative_workaround(self, usd_formatter, usd):
        """
        Tests the specific hack ensuring CLDR supports
        compact + accounting for negatives
        """
        spec = FormatSpec(compact=True, compact_precision=1, accounting=True)
        amount = Decimal("-2500000")

        result = usd_formatter.format(amount, usd, spec)

        assert normalize_space(result) == "($2.5M)"

    # Precision in compact format

    @pytest.mark.parametrize(
        "amount, precision, expected",
        [
            (Decimal("1234"), 1, "$1.2K"),
            (Decimal("1234"), 2, "$1.23K"),
            (Decimal("1200"), 4, "$1.2000K"),
        ],
    )
    def test_precision_in_compact_format(
        self, usd_formatter, amount, precision, expected, usd
    ):
        spec = FormatSpec(compact=True, compact_precision=precision)
        result = usd_formatter.format(amount, usd, spec)
        assert normalize_space(result) == expected

    # Grouping Separators

    @pytest.mark.parametrize(
        "group_sep, expected",
        [
            (True, "$1,234,567.89"),
            (False, "$1234567.89"),
        ],
    )
    def test_group_separator(self, usd_formatter, group_sep, expected, usd):
        spec = FormatSpec(group_separator=group_sep)
        result = usd_formatter.format(Decimal("1234567.89"), usd, spec)
        assert normalize_space(result) == expected

    @pytest.mark.parametrize(
        "trim, amount, expected",
        [
            (True, Decimal("225.50"), "$225.5"),
            (False, Decimal("225.50"), "$225.50"),
            (True, Decimal("225.12345000"), "$225.12345"),
        ],
    )
    def teste_trim_trailing_zeros(self, trim, amount, expected, usd, usd_formatter):

        result = usd_formatter.format(amount, usd, FormatSpec(trim_trailing_zeros=trim))

        assert result == expected

    # Rounding Policies

    def test_icu_formatter_rejects_invalid_rounding_mode(self, usd_formatter, usd):
        usd_formatter._rounding = "no valid"
        with pytest.raises(AssertionError):
            usd_formatter.format(
                Decimal("1"),
                usd,
                FormatSpec(),
            )

    @pytest.mark.parametrize(
        "amount, policy, expected",
        [
            (Decimal("1345"), RoundingMode.DOWN, "$1.34K"),
            (Decimal("1234"), RoundingMode.UP, "$1.24K"),
            (
                Decimal("2345"),
                RoundingMode.HALF_EVEN,
                "$2.34K",
            ),
            (
                Decimal("2355"),
                RoundingMode.HALF_EVEN,
                "$2.36K",
            ),
            (
                Decimal("2345"),
                RoundingMode.HALF_UP,
                "$2.35K",
            ),
        ],
    )
    def test_rounding_policies(self, usd_formatter, amount, policy, expected, usd):
        spec = FormatSpec(compact=True, compact_precision=2)
        usd_formatter._rounding = policy
        result = usd_formatter.format(amount, usd, spec)
        assert normalize_space(result) == expected

    def test_rounding_mode_configuration(self, usd_formatter):
        usd_formatter.configure(rounding=RoundingMode.UNNECESSARY)
        assert usd_formatter._rounding == RoundingMode.UNNECESSARY

    def test_numbering_system(self, usd_formatter, usd):
        usd_formatter.numbering_system = "arab"
        result = usd_formatter.format(Decimal("2026"), usd, FormatSpec())
        assert normalize_space(result) == "٢٬٠٢٦ $"

    def test_formatter_rejects_invalid_numbering_system(self, usd_formatter):
        with pytest.raises(
            BackendConfigurationError,
            match="ICU backend expected a valid numbering system: got 'xxx'",
        ):
            usd_formatter.numbering_system = "xxx"

    # Cross-Locale Verification using French Locale

    def test_french_locale_formatting(self, eur_formatter_fr):
        # Standard
        spec = FormatSpec(group_separator=True)
        res_std = eur_formatter_fr.format(
            Decimal("1234.56"), Currency.from_code("EUR"), spec
        )
        assert normalize_space(res_std) == "1 234,56 €"

        # Accounting Negative
        spec_acc = FormatSpec(accounting=True)
        res_acc = eur_formatter_fr.format(
            Decimal("-1234.56"), Currency.from_code("EUR"), spec_acc
        )
        # Assuming French accounting wraps the whole string
        assert normalize_space(res_acc) == "(1 234,56 €)"

        # Compact Accounting Negative Workaround
        spec_comp = FormatSpec(accounting=True, compact=True, compact_precision=1)
        res_comp = eur_formatter_fr.format(
            Decimal("-1500000"), Currency.from_code("EUR"), spec_comp
        )
        assert normalize_space(res_comp) == "(1,5 M €)"

        # compact with negative amount andhidden symbol
        spec_comp_hidden = FormatSpec(
            accounting=True, compact=True, compact_precision=1, ccy_display="hidden"
        )
        res_comp_hidden = eur_formatter_fr.format(
            Decimal("-1500000000"), Currency.from_code("EUR"), spec_comp_hidden
        )
        assert normalize_space(res_comp_hidden) == "(1,5 Md)"

        res_comp_hidden = eur_formatter_fr.format(
            Decimal("1500000000"), Currency.from_code("EUR"), spec_comp_hidden
        )
        assert normalize_space(res_comp_hidden) == "1,5 Md"

    @pytest.mark.parametrize(
        "display",
        [
            "symbol",
            "iso",
            "hidden",
        ],
    )
    @pytest.mark.slow
    def test_custom_currency_formatting(self, display):
        locales = icu.Locale.getAvailableLocales()
        for locale in locales:
            icu_fmt = IcuFormatter(str(locale))
            eur = icu_fmt.format(
                Decimal("2999213"),
                Currency.from_code("EUR"),
                FormatSpec(ccy_display=display),
            )

            tst = icu_fmt.format(
                Decimal("2999213"),
                Currency.from_code("TST"),
                FormatSpec(ccy_display=display),
            )

            str_eur = eur.replace("EUR", "").replace("€", "")
            str_tst = tst.replace("TST", "").replace("¤", "")
            assert str_eur == str_tst

    @pytest.mark.slow
    def test_custom_currency_formatting_long_name(self):
        locales = icu.Locale.getAvailableLocales()
        for locale in locales:
            icu_fmt = IcuFormatter(str(locale))
            eur = icu_fmt.format(
                Decimal("2999213"),
                Currency.from_code("EUR"),
                FormatSpec(ccy_display="name"),
            )

            tst = icu_fmt.format(
                Decimal("2999213"),
                Currency.from_code("TST"),
                FormatSpec(ccy_display="name"),
            )

            assert indexof(tst, "¤") == indexof(eur, "€")

            name = _get_currency_display_part(
                Decimal("2999213"), str(locale), Currency.from_code("TST")
            )

            assert indexof(tst, "test coin") == indexof(eur, name)
            tst_s = tst.replace("test coin", "").replace("¤", "").strip()
            eur_s = eur.replace(name, "").replace("€", "").strip()

            assert tst_s == eur_s
