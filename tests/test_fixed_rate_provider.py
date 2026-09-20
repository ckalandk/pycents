from decimal import Decimal

import pytest

from pycents import Money
from pycents.conversion import ExchangeRate, ExchangeRateInfo, FixedRateProvider
from pycents.exceptions import ProviderQueryError


class TestFixedRateProvider:
    @pytest.fixture
    def provider(self):
        provider = FixedRateProvider("name")
        provider.add_rate("EUR", "USD", "1.1539")
        provider.add_rate("EUR", "CAD", "1.6062")
        provider.add_rate("EUR", "AUD", "1.6194")
        provider.add_rate("EUR", "JPY", "178.86")
        provider.add_rate("EUR", "GBP", "0.8558")
        provider.add_rate("EUR", "CZK", "24.292")
        return provider

    def test_initialization(self, provider):
        assert provider.name == "name"

    def test_find_rate(self, provider):
        eur_jpy = provider.find_rate("EUR", "JPY")
        assert eur_jpy.base.ccy_code == "EUR"
        assert eur_jpy.quote.ccy_code == "JPY"
        assert str(eur_jpy.rate) == "178.86"

    def test_find_rate_failure(self, provider):
        with pytest.raises(ProviderQueryError):
            _ = provider.find_rate("USD", "CAD")

    def test_iteration(self, provider):
        it = iter(provider)
        rate = next(it)
        assert rate.base.ccy_code == "EUR"
        assert rate.quote.ccy_code == "USD"

    def test_money_conversion(self, provider):
        mny = Money.from_major("2.99", "EUR")

        result = mny.exchange_to("USD", provider=provider)
        assert str(result.as_majors) == "3.450161"

    def test_add_rate_from_components(self):
        provider = FixedRateProvider()
        provider.add_rate("EUR", "USD", "1.1539")

        rate = provider.find_rate("EUR", "USD")

        assert rate.base.ccy_code == "EUR"
        assert rate.quote.ccy_code == "USD"
        assert str(rate.rate) == "1.1539"

    def test_add_rate_accepts_decimal(self):
        provider = FixedRateProvider()
        provider.add_rate("EUR", "USD", Decimal("1.1539"))

        assert provider.find_rate("EUR", "USD").rate == Decimal("1.1539")

    def test_add_existing_exchange_rate(self):
        provider = FixedRateProvider()

        rate = ExchangeRate.from_pair("EUR/USD", "1.1539")

        provider.add_rate(rate)

        assert provider.find_rate("EUR", "USD") is rate

    def test_add_rate_with_info(self):
        provider = FixedRateProvider()

        info = ExchangeRateInfo(provider="test", ratetype="fixed")
        provider.add_rate("EUR", "USD", "1.1539", info=info)

        assert provider.find_rate("EUR", "USD").info is info

    @pytest.mark.parametrize(
        "args",
        [
            ("EUR",),
            ("EUR", "USD"),
        ],
    )
    def test_add_rate_missing_arguments(self, args):
        provider = FixedRateProvider()

        with pytest.raises(
            TypeError,
            match="base, quote, and rate are required",
        ):
            provider.add_rate(*args)

    def test_add_exchange_rate_with_other_arguments(self):
        provider = FixedRateProvider()
        info = ExchangeRateInfo(provider="test", ratetype="fixed")
        exchange_rate = ExchangeRate.from_pair("EUR/USD", "1.1539")

        with pytest.raises(
            TypeError, match="Adding an ExchangeRate requires no other arguments"
        ):
            provider.add_rate(exchange_rate, "EUR", "1.1415", info=info)  # type: ignore

    def test_add_duplicate_rate_is_ignored(self):
        provider = FixedRateProvider()

        first = ExchangeRate.from_pair("EUR/USD", "1.1539")
        second = ExchangeRate.from_pair("EUR/USD", "2.0000")

        provider.add_rate(first)
        provider.add_rate(second)

        assert provider.find_rate("EUR", "USD") is first

    def test_add_duplicate_rate_from_components_is_ignored(self):
        provider = FixedRateProvider()
        provider.add_rate("EUR", "USD", "1.1539")
        provider.add_rate("EUR", "USD", "2.0000")

        assert provider.find_rate("EUR", "USD").rate == Decimal("1.1539")
