from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any, TypedDict, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pycents.conversion.provider import ExchangeRateProvider
from pycents.conversion.rate import ExchangeRate
from pycents.conversion.rate_context import ExchangeRateInfo
from pycents.currency import Currency
from pycents.exceptions import ProviderQueryError

__all__ = ["DefaultProvider", "ProviderInfo"]

_RateCacheKey = tuple[str, str, str | None, date | None]


def _get_request(url: str) -> Request:
    return Request(
        url, headers={"User-Agent": "pycents/1.3.0", "Accept": "application/json"}
    )


class ProviderInfo(TypedDict):
    code: str
    name: str
    country_code: str
    ratetype: str
    pivot_currency: str
    data_url: str


class DefaultProvider(ExchangeRateProvider):
    _rate_cache: dict[_RateCacheKey, ExchangeRate] = {}
    _metadata_cache: dict[str, ProviderInfo] = {}

    def __init__(self, provider: str | None = None, asof: date | None = None):
        self.base_url = "https://api.frankfurter.dev/v2"
        self.default_provider = provider
        self._date = asof

    @property
    def rate_date(self) -> date | None:
        return self._date

    @rate_date.setter
    def rate_date(self, value: date | None) -> None:
        self._date = value

    @property
    def name(self) -> str:
        return self.default_provider or "Frankfurter"

    @name.setter
    def name(self, value: str | None) -> None:
        self.default_provider = value

    def _get_rate(
        self,
        base: Currency,
        quote: Currency,
        /,
        *,
        asof: date | None = None,
        **kwargs: Any,
    ) -> ExchangeRate:
        cache_key = (base.ccy_code, quote.ccy_code, self.default_provider, asof)

        if cache_key in type(self)._rate_cache:
            return self._rate_cache[cache_key]
        url = self._build_url_query(
            base.ccy_code, quote.ccy_code, asof.isoformat() if asof else ""
        )

        rate = self._fetch_rate(url)

        exchange_rate = self._make_exchange_rate(rate)
        self._rate_cache[cache_key] = exchange_rate

        return exchange_rate

    def get_rate(
        self,
        base: Currency,
        quote: Currency,
        /,
        *,
        asof: date | None = None,
        **kwargs: Any,
    ) -> ExchangeRate:
        _date = asof if asof is not None else self.rate_date
        if self.default_provider is None:
            return self._get_rate(base, quote, asof=_date, **kwargs)
        metadata = self.provider_info()
        pivot = Currency.from_code(metadata["pivot_currency"])

        if pivot == base:
            return self._get_rate(base, quote, asof=_date, **kwargs)

        pivot_base = self._get_rate(pivot, base, asof=_date, **kwargs)
        pivot_quote = self._get_rate(pivot, quote, asof=_date, **kwargs)
        return pivot_base.invert() * pivot_quote

    def _build_url_query(self, base: str, quote: str, date: str) -> str:
        url = f"{self.base_url}/rate/{base}/{quote}"
        params = {}
        if date:
            params["date"] = date
        if self.default_provider is not None:
            params["providers"] = self.default_provider
        if params:
            url += f"?{urlencode(params)}"
        return url

    def _fetch_rate(self, url: str) -> dict[str, Any]:
        req = _get_request(url)

        try:
            with urlopen(req, timeout=5) as response:
                data = json.load(response)
        except HTTPError as err:
            raise ProviderQueryError(f"{err.code}: {err.reason}") from err
        except URLError as err:
            raise ProviderQueryError(f"{err.reason}") from err

        return cast(dict[str, Any], data)

    def _fetch_provider_details(self) -> ProviderInfo:
        url = f"https://api.frankfurter.dev/v2/providers/{self.default_provider}"
        req = _get_request(url)
        try:
            with urlopen(req, timeout=5) as response:
                provider = json.load(response)
        except HTTPError as err:
            if err.code == 404:
                raise ProviderQueryError(
                    f"Unknown provider name: '{self.default_provider}'"
                ) from None
            raise ProviderQueryError(f"{err.code}: {err.reason}") from None
        except URLError as err:
            raise ProviderQueryError(f"Could not reach provider: {err.reason}") from err
        print(provider)
        return ProviderInfo(
            code=provider["key"],
            name=provider["name"],
            country_code=provider["country_code"],
            ratetype=provider["rate_type"],
            pivot_currency=provider["pivot_currency"],
            data_url=provider["data_url"],
        )

    def provider_info(self) -> ProviderInfo:
        """Fetches provider metadata from Frankfurter."""
        if self.default_provider is None:
            return ProviderInfo(
                code="Frankfurter",
                name="Frankfurter",
                country_code="",
                ratetype="blended",
                pivot_currency="",
                data_url="https://api.frankfurter.dev/",
            )
        code_upper = self.default_provider.upper()

        if code_upper in type(self)._metadata_cache:
            return type(self)._metadata_cache[code_upper]

        provider = self._fetch_provider_details()
        type(self)._metadata_cache[code_upper] = provider
        return provider

    def prefetch_rates(self) -> None:
        base_url = "https://api.frankfurter.dev/v2/rates"
        if self.default_provider is not None:
            base_url += f"?providers={self.default_provider}"
        if self.rate_date is not None:
            base_url += f"&date={self.rate_date.isoformat()}"
        req = _get_request(base_url)
        try:
            with urlopen(req, timeout=5) as response:
                rates = json.load(response)
        except HTTPError as err:
            if err.code == 404:
                raise ProviderQueryError(
                    f"Unknown provider name: '{self.default_provider}'"
                ) from None
            raise ProviderQueryError(f"{err.code}: {err.reason}") from err
        except URLError as err:
            raise ProviderQueryError(f"Could not reach provider: {err.reason}") from err
        for rate in rates:
            exchange_rate = self._make_exchange_rate(rate)
            cache_key = (
                exchange_rate.base.ccy_code,
                exchange_rate.quote.ccy_code,
                self.default_provider,
                self.rate_date,
            )
            self._rate_cache[cache_key] = exchange_rate

    def _make_exchange_rate(self, data: dict[str, Any]) -> ExchangeRate:
        metadata = None
        if self.default_provider is not None:
            metadata = self.provider_info()

        ratetype = metadata["ratetype"] if metadata is not None else "blended"

        asof = date.fromisoformat(data["date"])
        rateinfo = ExchangeRateInfo(
            provider=self.default_provider or "frankfurter",
            ratetype=ratetype,
            asof=asof,
        )

        ex_rate = ExchangeRate.from_pair(
            f"{data['base']}/{data['quote']}", Decimal(str(data["rate"])), info=rateinfo
        )
        return ex_rate
