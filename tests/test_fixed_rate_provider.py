import pytest

from pycents import Money
from pycents.conversion import FixedRateProvider
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

    # integration test
    def test_money_conversion(self, provider):
        mny = Money.from_major("2.99", "EUR")

        result = mny.exchange_to("USD", provider=provider)
        assert str(result.as_majors) == "3.450161"
