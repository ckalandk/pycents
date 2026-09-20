from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from typing import Any, overload

from pycents._decimal import _force_decimal
from pycents.conversion.provider import ExchangeRateProvider
from pycents.conversion.rate import ExchangeRate
from pycents.conversion.rate_context import ExchangeRateInfo
from pycents.currency import Currency
from pycents.exceptions import ProviderQueryError

__all__ = ["FixedRateProvider"]

type _CacheKey = tuple[Currency, Currency]


class FixedRateProvider(ExchangeRateProvider):
    def __init__(self, name: str = "FixedRateProvider"):
        self.name = name
        self._cache: dict[_CacheKey, ExchangeRate] = {}

    @overload
    def add_rate(
        self,
        base: str,
        quote: str,
        rate: str | Decimal,
        /,
        info: ExchangeRateInfo | None = None,
    ) -> None: ...

    @overload
    def add_rate(self, rate: ExchangeRate, /) -> None: ...

    def add_rate(
        self,
        base: str | ExchangeRate,
        quote: str | None = None,
        rate: str | Decimal | None = None,
        /,
        info: ExchangeRateInfo | None = None,
    ) -> None:
        if isinstance(base, ExchangeRate):
            if quote is not None or rate is not None or info is not None:
                raise TypeError("Adding an ExchangeRate requires no other arguments")
            ex_rate = base
        else:
            if quote is None or rate is None:
                raise TypeError(
                    "base, quote, and rate are required when adding a new rate"
                )
            ex_rate = ExchangeRate(
                Currency.from_code(base),
                Currency.from_code(quote),
                rate=_force_decimal(rate),
                info=info,
            )

        key = (ex_rate.base, ex_rate.quote)
        if key in self._cache:
            return
        self._cache[key] = ex_rate

    def get_rate(
        self,
        base: Currency,
        quote: Currency,
        /,
        *,
        asof: date | None = None,
        **kwargs: Any,
    ) -> ExchangeRate:
        key = (base, quote)
        try:
            return self._cache[key]
        except KeyError as err:
            msg = f"No exchange rate available for {base!s}/{quote!s}"
            raise ProviderQueryError(msg) from err

    def find_rate(self, base: str, quote: str) -> ExchangeRate:
        return self.get_rate(Currency.from_code(base), Currency.from_code(quote))

    def __iter__(self) -> Iterator[ExchangeRate]:
        return iter(self._cache.values())
