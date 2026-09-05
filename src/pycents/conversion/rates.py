from dataclasses import dataclass, field
from decimal import Decimal

from pycents.currency import Currency

from .exchange_ctx import ExchangeRateContext

__all__ = ["ExchangeRate"]


@dataclass(frozen=True, slots=True)
class ExchangeRate:
    base: Currency
    term: Currency
    factor: Decimal
    context: ExchangeRateContext | None = field(default=None, repr=False)
