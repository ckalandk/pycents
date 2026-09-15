from decimal import Decimal

import pytest

from pycents.conversion import ExchangeRate, ExchangeRateProvider
from pycents.exceptions import CurrencyMismatchError
from pycents.money import Money


def test_money_conversion():
    rate = ExchangeRate.from_string("EUR/USD=1.1655")
    mny = Money.from_major("2.99", "EUR")

    result = mny * rate
    assert result.as_majors == Decimal("3.484845")


def test_money_conversion_with_default_provider(monkeypatch):
    class DumbProvider(ExchangeRateProvider):
        def __init__(self, provider=None, asof=None):
            self.provider = provider
            self.date = asof

        def get_rate(self, base, quote, /, *, asof=None, **kwargs):
            if self.provider is None:
                return ExchangeRate.from_string("EUR/USD=1.1313")
            if self.date is None:
                return ExchangeRate.from_string("EUR/USD=1.1516")
            return ExchangeRate.from_string("EUR/USD=2.8811")

    monkeypatch.setattr(
        "pycents.money.DefaultProvider",
        DumbProvider,
    )
    mny = Money.from_major("2.99", "EUR")
    result = mny.exchange_to("USD", provider=DumbProvider())
    assert result.as_majors == mny.as_majors * Decimal("1.1313")

    result = mny.exchange_to("USD")
    assert result.as_majors == mny.as_majors * Decimal("1.1516")

    # Use a date
    result = mny.exchange_to("USD", provider=DumbProvider("ECB", "some_date"))
    assert result.as_majors == mny.as_majors * Decimal("2.8811")


def test_money_conversion_fails_with_incompatible_currency():
    mny = Money.from_major("2.99", "EUR")
    rate = ExchangeRate.from_string("USD/CAD=1.14")

    with pytest.raises(CurrencyMismatchError):
        _ = mny * rate
