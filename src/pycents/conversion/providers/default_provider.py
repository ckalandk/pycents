from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pycents.conversion.provider import ExchangeRateProvider
from pycents.conversion.rate import ExchangeRate
from pycents.conversion.rate_context import ExchangeRateInfo
from pycents.currency import Currency
from pycents.exceptions import ProviderQueryError

_rate_cache_key = tuple[str, str, str | None, date | None]

__all__ = ["DefaultProvider", "ProviderInfo"]


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    code: str
    name: str
    country_code: str
    ratetype: str
    pivot_currency: str
    data_url: str

    @classmethod
    def from_dict(cls, data: Mapping[str, str]) -> ProviderInfo:
        return cls(
            code=data["key"],
            name=data["name"],
            country_code=data["country_code"],
            ratetype=data["rate_type"],
            pivot_currency=data["pivot_currency"],
            data_url=data["data_url"],
        )


class DefaultProvider(ExchangeRateProvider):
    _rate_cache: dict[_rate_cache_key, ExchangeRate] = {}
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
    def provider(self) -> str:
        return self.default_provider or "Frankfurter"

    @provider.setter
    def provider(self, value: str | None) -> None:
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
        metadata = None
        if self.default_provider is not None:
            metadata = self.provider_info()

        ratetype = metadata.ratetype if metadata is not None else "blended"

        url = self._build_url_query(
            base.ccy_code, quote.ccy_code, asof.isoformat() if asof else ""
        )

        rate = self._fetch_rate(url)

        asof = date.fromisoformat(rate["date"])
        rateinfo = ExchangeRateInfo(
            provider=self.default_provider or "frankfurter",
            ratetype=ratetype,
            timestamp=datetime.combine(asof, datetime.min.time()),
        )

        ex_rate = ExchangeRate.from_pair(
            f"{rate['base']}/{rate['quote']}", Decimal(str(rate["rate"])), info=rateinfo
        )

        type(self)._rate_cache[cache_key] = ex_rate
        return ex_rate

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
        pivot = Currency.from_code(metadata.pivot_currency)

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
        req = Request(
            url, headers={"User-Agent": "pycents/1.3.0", "Accept": "application/json"}
        )

        try:
            with urlopen(req, timeout=5) as response:
                data = json.load(response)
        except HTTPError as err:
            error = json.load(err)
            msg = error["message"]
            raise ProviderQueryError(f"{msg}") from err
        return cast(dict[str, Any], data)

    def _fetch_provider_details(self) -> ProviderInfo:
        url = f"https://api.frankfurter.dev/v2/providers/{self.default_provider}"
        req = Request(
            url, headers={"User-Agent": "pycents/1.3.0", "Accept": "application/json"}
        )

        try:
            with urlopen(req, timeout=5) as response:
                provider = json.load(response)
        except HTTPError:
            raise ProviderQueryError(
                f"Unkown provider name: '{self.default_provider}'"
            ) from None
        return ProviderInfo.from_dict(provider)

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
