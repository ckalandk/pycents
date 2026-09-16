from __future__ import annotations

from datetime import date
from typing import Any, Protocol, runtime_checkable

from pycents.currency import Currency

from .rate import ExchangeRate


@runtime_checkable
class ExchangeRateProvider(Protocol):
    """Protocol for objects that provide exchange rates.

    Implementations return an exchange rate for a base/quote currency pair.
    Providers may support historical rates through the ``asof`` parameter and
    may accept provider-specific options through ``kwargs``.
    """

    def get_rate(
        self,
        base: Currency,
        quote: Currency,
        /,
        *,
        asof: date | None = None,
        **kwargs: Any,
    ) -> ExchangeRate: ...
