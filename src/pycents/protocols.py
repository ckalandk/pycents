from decimal import Decimal
from typing import Protocol

from pycents.currency import Currency


class MonetaryAmount(Protocol):
    @property
    def _as_decimal(self) -> Decimal: ...

    @property
    def currency(self) -> Currency: ...

    def to_decimal(self) -> Decimal: ...
