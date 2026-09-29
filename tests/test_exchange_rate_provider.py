import json
from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError

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

    provider.name = None
    provider.rate_date = date(2027, 9, 14)

    assert provider.name == "Frankfurter"
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
    assert rate.info.asof == date(2026, 9, 13)
    assert rate.info.metadata == {}


def test_successfull_direct_rate_lookup_with_ecb_provider(provider, monkeypatch):
    provider.name = "ECB"
    rate = provider.get_rate(Currency.from_code("EUR"), Currency.from_code("USD"))
    assert rate.base.ccy_code == "EUR"
    assert rate.quote.ccy_code == "USD"
    assert rate.rate == Decimal("1.1414")
    assert not rate.is_cross
    assert rate.info is not None
    assert rate.info.provider == "ECB"
    assert rate.info.ratetype == "reference rate"
    assert rate.info.asof == date(2026, 9, 13)
    assert rate.info.metadata == {}


def test_succesfull_rate_lookup_with_date(provider):
    assert provider.default_provider is None
    eur_usd = provider.get_rate(
        Currency.from_code("EUR"), Currency.from_code("USD"), asof=date(1999, 12, 1)
    )

    assert eur_usd.rate == Decimal("1.1313")

    provider.name = "ECB"

    eur_usd = provider.get_rate(
        Currency.from_code("EUR"), Currency.from_code("USD"), asof=date(1999, 12, 1)
    )

    assert eur_usd.rate == Decimal("1.1515")


def test_succesfull_cross_rate_lookup(provider):
    provider.name = "ECB"
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

    body_dict = json.loads(body.decode())

    def mock_urlopen(*args, **kwargs):
        raise HTTPError(
            url="https://example.com",
            code=body_dict["status"],
            msg=body_dict["message"],
            hdrs=None,  # type: ignore
            fp=BytesIO(body),
        )

    monkeypatch.setattr(
        "pycents.conversion.providers.default_provider.urlopen", mock_urlopen
    )

    with pytest.raises(ProviderQueryError, match=msg):
        _ = provider._fetch_rate("https://example.com")


def test_rate_lookup_url_failures(monkeypatch):

    provider = DefaultProvider("ECB")

    def mock_urlopen(*args, **kwargs):
        raise URLError("Random Error")

    monkeypatch.setattr(
        "pycents.conversion.providers.default_provider.urlopen", mock_urlopen
    )

    with pytest.raises(ProviderQueryError, match="Random Error"):
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

    assert info["code"] == "Frankfurter"
    assert info["name"] == "Frankfurter"

    provider.name = "ECB"
    info = provider.provider_info()

    assert info["code"] == "ECB"
    assert info["name"] == "European Central Bank"
    assert info["country_code"] == "EU"
    assert info["data_url"] == "www.ecb.com"


@pytest.mark.parametrize(
    "status, msg", [(404, "Unknown provider name"), (422, "Silly error")]
)
def test_provider_info_http_failure(monkeypatch, status, msg):
    provider = DefaultProvider("Monty Python")

    def mock_urlopen(*args, **kwargs):
        raise HTTPError(
            url="https://example.com",
            code=status,
            msg=msg,
            hdrs=None,  # type: ignore
            fp=BytesIO(b""),
        )

    monkeypatch.setattr(
        "pycents.conversion.providers.default_provider.urlopen", mock_urlopen
    )

    with pytest.raises(ProviderQueryError, match=msg):
        _ = provider.provider_info()


def test_provider_info_url_failure(monkeypatch):
    provider = DefaultProvider("Monty Python")

    def mock_urlopen(*args, **kwargs):
        raise URLError("Unable to connect to the provider")

    monkeypatch.setattr(
        "pycents.conversion.providers.default_provider.urlopen", mock_urlopen
    )

    with pytest.raises(ProviderQueryError, match="Unable to connect to the provider"):
        _ = provider.provider_info()


def test_provider_info_cache(provider, monkeypatch):
    _provider_cache_patch = {}
    monkeypatch.setattr(DefaultProvider, "_metadata_cache", _provider_cache_patch)

    provider.name = "ECB"

    assert len(_provider_cache_patch) == 0

    info = provider.provider_info()
    assert info["code"] == "ECB"
    assert len(_provider_cache_patch) == 1

    assert info is _provider_cache_patch["ECB"]

    # Make any cache miss fail the test.
    def fail(*args, **kwargs):
        raise AssertionError("Rate was fetched again instead of using the cache")

    monkeypatch.setattr(provider, "_fetch_provider_details", fail)
    info = provider.provider_info()

    assert info is _provider_cache_patch["ECB"]


def test_prefetch_rates_populates_cache(monkeypatch):
    provider = DefaultProvider("ECB")

    fake_payload = [
        {"base": "EUR", "quote": "USD", "rate": "1.1000", "date": "2026-09-28"},
        {"base": "EUR", "quote": "CAD", "rate": "1.5000", "date": "2026-09-28"},
    ]

    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    monkeypatch.setattr(
        "pycents.conversion.providers.default_provider.json.load",
        lambda response: fake_payload,
    )
    monkeypatch.setattr(
        provider,
        "provider_info",
        lambda: {
            "code": "ECB",
            "name": "European Central Bank",
            "ratetype": "reference",
        },
    )

    monkeypatch.setattr(
        "pycents.conversion.providers.default_provider.urlopen",
        lambda req, timeout: mock_resp,
    )

    provider.prefetch_rates()

    key_usd = ("EUR", "USD", "ECB", provider.rate_date)
    key_cad = ("EUR", "CAD", "ECB", provider.rate_date)
    assert provider._rate_cache[key_usd].rate == Decimal("1.1000")
    assert provider._rate_cache[key_cad].rate == Decimal("1.5000")


@pytest.mark.parametrize(
    "status, msg", [(404, "Unknown provider name:"), (422, "Something bad happened")]
)
def test_prefetch_rates_httperror(monkeypatch, status, msg):
    provider = DefaultProvider("ECB")

    def mock_urlopen(*args, **kwargs):
        raise HTTPError(
            url="https://example.com",
            code=status,
            msg=msg,
            hdrs=None,  # type: ignore
            fp=BytesIO(b""),
        )

    monkeypatch.setattr(
        "pycents.conversion.providers.default_provider.urlopen", mock_urlopen
    )

    with pytest.raises(ProviderQueryError, match=msg):
        provider.prefetch_rates()


def test_prefetch_rates_urllerror(monkeypatch):
    provider = DefaultProvider("ECB")

    def mock_urlopen(*args, **kwargs):
        raise URLError("Unkwown reason")

    monkeypatch.setattr(
        "pycents.conversion.providers.default_provider.urlopen", mock_urlopen
    )

    with pytest.raises(ProviderQueryError, match="Unkwown reason"):
        provider.prefetch_rates()
