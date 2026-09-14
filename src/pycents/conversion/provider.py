from __future__ import annotations

from datetime import date
from typing import Any, Protocol, runtime_checkable

from pycents.currency import Currency

from .rate import ExchangeRate


@runtime_checkable
class ExchangeRateProvider(Protocol):
    def get_rate(
        self,
        base: Currency,
        quote: Currency,
        /,
        *,
        asof: date | None = None,
        **kwargs: Any,
    ) -> ExchangeRate: ...
