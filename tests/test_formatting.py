# pyright: reportGeneralTypeIssues=false
# mypy: ignore-errors
from copy import copy

import pytest

from pycents import Money, formatting
from pycents.currency import Currency
from pycents.exceptions import InvalidFormatSpecError
from pycents.formatting._default import _FormatContext
from pycents.formatting.base_formatter import BaseFormatter
from pycents.formatting.formatspec import FormatSpec
from pycents.formatting.std_formatter import StdFormatter
from pycents.rounding import RoundingMode


class RecordingFormatter(BaseFormatter):
    def __init__(self):
        super().__init__("")
        self.calls = []

    def _validate_numbering_system(self, value: str | None) -> None:
        pass

    def format(
        self,
        amount,
        currency,
        spec: FormatSpec,
        *,
        precision: int | None = None,
        rounding: RoundingMode = RoundingMode.HALF_EVEN,
        omit_trailing_zeros: bool = False,
    ):
        self.calls.append(
            {
                "amount": amount,
                "currency": currency,
                "ctx": spec,
                "precision": precision,
                "omit_trailing_zeros": omit_trailing_zeros,
            }
        )
        return "dummy"


@pytest.fixture
def formatter():
    original_formatter = formatting._default._default.backend_formatter

    mock_formatter = RecordingFormatter()
    formatting.use_backend(mock_formatter)

    yield mock_formatter

    formatting._default._default.backend_formatter = original_formatter


def test_format_context_internals():
    ctx = _FormatContext(StdFormatter(), "xx_XX", "klingon")
    assert ctx.backend_formatter.locale == "xx_XX"
    assert ctx.backend_formatter.numbering_system == "klingon"
    assert not ctx.compact
    assert not ctx.accounting
    assert ctx.display == "iso"
    assert ctx.rounding == RoundingMode.HALF_EVEN
    assert ctx.compact_prec == 1
    assert ctx.group_separator


def test_money_format_forward_amount_and_currency_code(formatter):
    money = Money.from_major("12.34", "USD")
    assert format(money, "") == "dummy"

    assert formatter.calls[0]["amount"] == money.as_majors
    assert formatter.calls[0]["currency"] == Currency.from_code("USD")


@pytest.mark.parametrize(
    "fmt_spec,expected_ctx",
    [
        pytest.param("hcau", ("hidden", True, 1, True, False)),
        pytest.param("i.2c", ("iso", True, 2, False, True)),
        pytest.param("i.3c", ("iso", True, 3, False, True)),
        pytest.param("nau", ("name", False, None, True, False)),
    ],
)
def test_money_dunder_format(formatter, fmt_spec, expected_ctx):
    money = Money.from_major("12.34", "USD")

    assert format(money, fmt_spec) == "dummy"

    ctx = formatter.calls[0]["ctx"]
    assert ctx == FormatSpec(*expected_ctx)


def test_money_dunder_format_with_empty_spec_use_formatter_default_format_spec(
    formatter,
):
    money = Money.from_major("12.34", "USD")
    formatter.configure(ccy_display="dummy")  # type: ignore

    assert format(money, "") == "dummy"
    ctx = formatter.calls[0]["ctx"]

    assert ctx.ccy_display == "dummy"


def test_money_format_basic_config(formatter):
    formatting.basicConfig(
        locale="xx_XX",
    )
    money = Money.from_major("12.34", "USD")
    assert format(money, "") == "dummy"

    assert formatter.locale == "xx_XX"
    assert formatter.calls[0]["precision"] is None
    assert not formatter.calls[0]["omit_trailing_zeros"]


def test_money_format_raises_when_format_spec_has_precision_but_no_compact_format(
    formatter,
):
    money = Money.from_major("12.34", "USD")
    with pytest.raises(InvalidFormatSpecError) as exc:
        format(money, ".2")
    assert "Formatting precision is locked" in str(exc.value)


def test_money_format_rejects_invalid_format_spec(formatter):
    money = Money.from_major("12.34", "USD")
    with pytest.raises(
        InvalidFormatSpecError,
        match="Unknown format code 'x' for object of type 'Money'",
    ):
        format(money, "x")


# Format configuration tests


def test_money_format_use_backend(monkeypatch):
    original_formatter = formatting._default._default.backend_formatter
    monkeypatch.setattr(
        formatting._default._default, "backend_formatter", original_formatter
    )
    money = Money.from_major("12.34", "USD")
    f1 = RecordingFormatter()
    f2 = RecordingFormatter()

    formatting.use_backend(f1)
    format(money, "")

    formatting.use_backend(f2)
    format(money, "")

    assert len(f1.calls) == 1
    assert len(f2.calls) == 1


def test_money_format_use_backend_rejects_invalid_args():
    with pytest.raises(ValueError) as exc:
        formatting.use_backend("foo")
    assert "Unknown formatter backend 'foo'." in str(exc.value)

    class FooFormatter:
        pass

    with pytest.raises(TypeError) as exc:
        formatting.use_backend(FooFormatter())  # type: ignore

    assert str(exc.value) == "backend_formatter must be a BaseFormatter instance."


def test_money_format_get_formatter(formatter):
    assert formatting.get_formatter() == formatter


def test_money_format_current_backend(formatter):
    assert formatting.current_backend() == formatter.__class__.__name__


def test_money_format_register_backend(monkeypatch):
    registry = {}
    monkeypatch.setattr(formatting._default, "_BACKENDS", registry)

    def factory():
        return RecordingFormatter()

    formatting.register_backend("recording", factory)

    assert registry["recording"] is factory
    assert "recording" in formatting.available_backends()


def test_money_format_register_formatter_class(monkeypatch):
    registry = {}
    monkeypatch.setattr(formatting._default, "_BACKENDS", registry)

    original_formatter = formatting._default._default.backend_formatter
    monkeypatch.setattr(
        formatting._default._default, "backend_formatter", original_formatter
    )

    @formatting.register(name="dumb", locale="", bar="bar", foo=42)
    class DumbFormatter(BaseFormatter):
        def __init__(self, locale, bar: str, foo: int):
            super().__init__(locale)
            self.bar = bar
            self.foo = foo

        def _validate_numbering_system(self, value: str | None) -> None:
            pass

        def format(
            self,
            amount,
            currency,
            spec: FormatSpec,
        ) -> str:
            return f"dumb(bar={self.bar}, foo={self.foo})"

    assert "dumb" in formatting.available_backends()

    dumbFormatter = registry["dumb"]()
    assert isinstance(dumbFormatter, DumbFormatter)

    formatting.use_backend("dumb")

    money = Money.from_major("12.34", "USD")
    result = formatting.format(money, "")

    assert result == "dumb(bar=bar, foo=42)"


def test_money_format_available_backends():
    assert formatting.available_backends() == ["babel", "icu", "std"]


def test_register_backend_rejects_invalid_args():
    _callable = object()
    with pytest.raises(ValueError, match="The factory_function must be callable."):
        formatting.register_backend("foo", _callable)  # type: ignore


def test_register_backend_rejects_already_existing_backend():
    with pytest.raises(
        ValueError, match="A backend named 'std' is already registered."
    ):
        formatting.register_backend("std", lambda: None)  # type: ignore


def test_config_ignored_with_spec(monkeypatch):
    formatter = formatting.get_formatter()
    temp_spec = copy(formatter._default_spec)

    monkeypatch.setattr(formatter, "_default_spec", temp_spec)

    formatting.get_formatter().configure(
        compact=True,
        compact_precision=2,
        ccy_display="hidden",
        group_separator=True,
    )
    mny = Money.from_major("2123.95", "USD")
    result = formatting.format(mny, "")
    assert result == "2.12K"

    result = formatting.format(mny, "iu")
    assert result == "USD\xa02123.95"


def test_formatting_locale_format():
    money = Money.from_major(-26123, "USD")
    assert f"{money}" == "-USD\xa026,123.00"

    with formatting.local_format() as fmt:
        fmt.compact = True
        fmt.accounting = True
        fmt.compact_prec = 2
        fmt.display = "hidden"
        fmt.rounding = RoundingMode.UP
        assert f"{money}" == "(26.13K)"

    with formatting.local_format() as fmt:
        fmt.group_separator = False
        assert f"{money}" == "-USD\xa026123.00"

    # default should be restored
    assert f"{money}" == "-USD\xa026,123.00"
