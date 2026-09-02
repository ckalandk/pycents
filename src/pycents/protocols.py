from decimal import Decimal
from typing import Protocol

from pycents.currency import Currency


class MonetaryAmount(Protocol):
    @property
    def _as_decimal(self) -> Decimal:
        """Return the amount as a Decimal for internal arithmetic."""
        ...  # pragma: no cover

    @property
    def currency(self) -> Currency: ...

    @property
    def as_majors(self) -> Decimal: ...

    def to_decimal(self) -> Decimal: ...
