from __future__ import annotations

from typing import Protocol, runtime_checkable

from pycents.currency import Currency

from .exchange_ctx import ExchangeRateContext
from .rates import ExchangeRate


@runtime_checkable
class ExchangeRateProvider(Protocol):
    def get_exchange_rate(
        self,
        base: Currency,
        term: Currency,
        /,
        context: ExchangeRateContext | None = None,
    ) -> ExchangeRate: ...
