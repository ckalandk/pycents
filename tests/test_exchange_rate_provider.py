from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock
from urllib.error import HTTPError

import pytest

from pycents.conversion.providers import DefaultProvider, ProviderInfo
from pycents.currency import Currency
from pycents.exceptions import ProviderQueryError


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear class-level caches before every test to prevent test leakage."""
    DefaultProvider._rate_cache.clear()
    DefaultProvider._metadata_cache.clear()


@pytest.fixture
def provider(monkeypatch):
    rates = dict(
        [
            (
                "https://api.frankfurter.dev/v2/rate/EUR/USD",
                {"date": "2026-09-13", "base": "EUR", "quote": "USD", "rate": 1.1212},
            ),
            (
                "https://api.frankfurter.dev/v2/rate/EUR/USD?date=1999-12-01",
                {"date": "1999-12-01", "base": "EUR", "quote": "USD", "rate": 1.1313},
            ),
            (
                "https://api.frankfurter.dev/v2/rate/EUR/USD?providers=ECB",
                {"date": "2026-09-13", "base": "EUR", "quote": "USD", "rate": 1.1414},
            ),
            (
                "https://api.frankfurter.dev/v2/rate/EUR/JPY?providers=ECB",
                {"date": "2026-09-13", "base": "EUR", "quote": "USD", "rate": 114.14},
            ),
            (
                "https://api.frankfurter.dev/v2/rate/EUR/USD?date=1999-12-01&providers=ECB",
                {"date": "2026-09-13", "base": "EUR", "quote": "USD", "rate": 1.1515},
            ),
        ]
    )

    providers: ProviderInfo = ProviderInfo(
        code="ECB",
        name="European Central Bank",
        country_code="EU",
        ratetype="reference rate",
        pivot_currency="EUR",
        data_url="https://www.ecb.europa.eu",
    )

    provider = DefaultProvider()

    monkeypatch.setattr(provider, "_fetch_rate", lambda url: rates[url])

    monkeypatch.setattr(provider, "_fetch_provider_details", lambda: providers)

    return provider


def test_default_provider_properties():
    provider = DefaultProvider("ECB", date(2026, 9, 14))

    assert provider.default_provider == "ECB"
    assert provider.rate_date == date(2026, 9, 14)

    provider.provider = None
    provider.rate_date = date(2027, 9, 14)

    assert provider.provider == "Frankfurter"
    assert provider.rate_date == date(2027, 9, 14)


def test_successfull_direct_rate_lookup_with_no_provider(provider):
    rate = provider.get_rate(Currency.from_code("EUR"), Currency.from_code("USD"))
    assert rate.base.ccy_code == "EUR"
    assert rate.quote.ccy_code == "USD"
    assert rate.rate == Decimal("1.1212")
    assert not rate.is_cross
    assert rate.info is not None
    assert rate.info.provider == "frankfurter"
    assert rate.info.ratetype == "blended"
    assert rate.info.timestamp.date() == date(2026, 9, 13)
    assert rate.info.metadata == {}


def test_successfull_direct_rate_lookup_with_ecb_provider(provider, monkeypatch):
    provider.provider = "ECB"
    rate = provider.get_rate(Currency.from_code("EUR"), Currency.from_code("USD"))
    assert rate.base.ccy_code == "EUR"
    assert rate.quote.ccy_code == "USD"
    assert rate.rate == Decimal("1.1414")
    assert not rate.is_cross
    assert rate.info is not None
    assert rate.info.provider == "ECB"
    assert rate.info.ratetype == "reference rate"
    assert rate.info.timestamp.date() == date(2026, 9, 13)
    assert rate.info.metadata == {}


def test_succesfull_rate_lookup_with_date(provider):
    assert provider.default_provider is None
    eur_usd = provider.get_rate(
        Currency.from_code("EUR"), Currency.from_code("USD"), asof=date(1999, 12, 1)
    )

    assert eur_usd.rate == Decimal("1.1313")

    provider.provider = "ECB"

    eur_usd = provider.get_rate(
        Currency.from_code("EUR"), Currency.from_code("USD"), asof=date(1999, 12, 1)
    )

    assert eur_usd.rate == Decimal("1.1515")


def test_succesfull_cross_rate_lookup(provider):
    provider.provider = "ECB"
    eur_usd = provider.get_rate(Currency.from_code("EUR"), Currency.from_code("USD"))
    eur_jpy = provider.get_rate(Currency.from_code("EUR"), Currency.from_code("JPY"))
    usd_jpy = provider.get_rate(Currency.from_code("USD"), Currency.from_code("JPY"))

    assert usd_jpy == eur_usd.invert() * eur_jpy


def test_rate_lookup_cache(provider, monkeypatch):
    _rate_cache_patch = {}
    monkeypatch.setattr(DefaultProvider, "_rate_cache", _rate_cache_patch)
    eur_usd = provider.get_rate(Currency.from_code("EUR"), Currency.from_code("USD"))
    assert len(_rate_cache_patch) == 1
    assert eur_usd in _rate_cache_patch.values()

    # Make any cache miss fail the test.
    def fail(*args, **kwargs):
        raise AssertionError("Rate was fetched again instead of using the cache")

    monkeypatch.setattr(provider, "_fetch_rate", fail)

    cached_eur_usd = provider.get_rate(
        Currency.from_code("EUR"),
        Currency.from_code("USD"),
    )

    assert cached_eur_usd is eur_usd


def test_fetch_rate(monkeypatch):
    response = MagicMock()
    response.__enter__.return_value = response
    response.__exit__.return_value = False

    response.read.return_value = b'{"base": "EUR", "quote": "USD", "rate": "1.1592"}'

    monkeypatch.setattr(
        "pycents.conversion.providers.default_provider.urlopen",
        lambda *args, **kwargs: response,
    )

    provider = DefaultProvider("ECB")

    result = provider._fetch_rate("https://example.com")

    assert result["base"] == "EUR"
    assert result["quote"] == "USD"
    assert result["rate"] == "1.1592"


@pytest.mark.parametrize(
    "body, msg",
    [
        (b'{"status": 422, "message": "Invalid currency"}', "Invalid currency"),
        (b'{"status": 404, "message": "No rate for you"}', "No rate for you"),
        (b'{"status": 405, "message": "Come back tomorrow"}', "Come back tomorrow"),
    ],
)
def test_rate_lookup_failures(monkeypatch, body, msg):

    provider = DefaultProvider("ECB")

    def mock_urlopen(*args, **kwargs):
        raise HTTPError(
            url="https://example.com",
            code=422,
            msg="Unprocessable Entity",
            hdrs=None,  # type: ignore
            fp=BytesIO(body),
        )

    monkeypatch.setattr(
        "pycents.conversion.providers.default_provider.urlopen", mock_urlopen
    )

    with pytest.raises(ProviderQueryError, match=msg):
        _ = provider._fetch_rate("https://example.com")


def test_provider_info(monkeypatch):
    response = MagicMock()
    response.__enter__.return_value = response
    response.__exit__.return_value = False

    response.read.return_value = (
        b'{"key": "ECB", "name": "European Central Bank", '
        b'"country_code": "EU", "rate_type": "reference rate", '
        b'"pivot_currency": "EUR", "data_url": "www.ecb.com"}'
    )

    monkeypatch.setattr(
        "pycents.conversion.providers.default_provider.urlopen",
        lambda *args, **kwargs: response,
    )

    provider = DefaultProvider()
    info = provider.provider_info()

    assert info.code == "Frankfurter"
    assert info.name == "Frankfurter"

    provider.provider = "ECB"
    info = provider.provider_info()

    assert info.code == "ECB"
    assert info.name == "European Central Bank"
    assert info.country_code == "EU"
    assert info.data_url == "www.ecb.com"


def test_provider_info_failure(monkeypatch):
    provider = DefaultProvider("Monty Python")

    def mock_urlopen(*args, **kwargs):
        raise HTTPError(
            url="https://example.com",
            code=422,
            msg="Unprocessable Entity",
            hdrs=None,  # type: ignore
            fp=BytesIO(b""),
        )

    monkeypatch.setattr(
        "pycents.conversion.providers.default_provider.urlopen", mock_urlopen
    )

    with pytest.raises(
        ProviderQueryError, match="Unkown provider name: 'Monty Python'"
    ):
        _ = provider.provider_info()


def test_provider_info_cache(provider, monkeypatch):
    _provider_cache_patch = {}
    monkeypatch.setattr(DefaultProvider, "_metadata_cache", _provider_cache_patch)

    provider.provider = "ECB"

    assert len(_provider_cache_patch) == 0

    info = provider.provider_info()
    assert info.code == "ECB"
    assert len(_provider_cache_patch) == 1

    assert info is _provider_cache_patch["ECB"]

    # Make any cache miss fail the test.
    def fail(*args, **kwargs):
        raise AssertionError("Rate was fetched again instead of using the cache")

    monkeypatch.setattr(provider, "_fetch_provider_details", fail)
    info = provider.provider_info()

    assert info is _provider_cache_patch["ECB"]
