from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, NotRequired, Self, TypedDict

from pycents._decimal import _force_decimal
from pycents.currency import Currency
from pycents.exceptions import CurrencyMismatchError

from .rate_context import ExchangeRateInfo

__all__ = ["ExchangeRate", "ExchangeRateData"]


class ExchangeRateData(TypedDict):
    base: str
    quote: str
    rate: str
    sources: NotRequired[list[ExchangeRateData]]
    info: NotRequired[dict[str, str]]


@dataclass(frozen=True, slots=True)
class ExchangeRate:
    """Represents a financial exchange rate between two currencies.

    This class encapsulates the conversion rate from a base currency to a quote
    (term) currency. It is designed as an immutable dataclass and automatically
    tracks cross-rate derivations through the ``path`` and ``lineage`` attributes.

    Attributes:
        base (Currency): The base currency being converted from (e.g., EUR in EUR/USD).
        quote (Currency): The term or quote currency being converted to
            (e.g., USD in EUR/USD).
        rate (Decimal): The exact conversion factor. Must be strictly positive.
        path (tuple[ExchangeRate, ...]): The sequence of underlying exchange rates used
            to derive this rate, if it is a cross rate. Defaults to an empty tuple.
        info (ExchangeRateContext | None): Optional context associated with the
            rate, such as the data provider or effective date. Defaults to None.
    """

    base: Currency
    quote: Currency
    rate: Decimal
    path: tuple[ExchangeRate, ...] = field(default=(), repr=False)
    info: ExchangeRateInfo | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.rate < 0:
            raise ValueError(
                f"Expected a strictly positive exchage rate, got {self.rate}"
            )

    @property
    def is_cross(self) -> bool:
        return bool(self.path)

    @property
    def lineage(self) -> tuple[ExchangeRate, ...]:
        """Return the flat chain of direct exchange rates used to build this rate."""
        if not self.path:
            return (self,)
        flat_chain: list[ExchangeRate] = []
        for src in self.path:
            flat_chain.extend(src.lineage)
        return tuple(flat_chain)

    @classmethod
    def from_pair(
        cls,
        ratio: str,
        rate: int | str | Decimal,
        *,
        info: ExchangeRateInfo | None = None,
    ) -> Self:
        """Create an exchange rate from a currency pair and rate.

        Args:
            ratio: Currency pair in the form ``"BASE/TERM"`` with no spaces.
                For example, ``"USD/EUR"`` represents an exchange rate from USD to EUR.
            rate: Exchange rate factor. Integers, strings, and :class:`~decimal.Decimal`
                instances are accepted.
            info: Optional context associated with the exchange rate.

        Returns:
            A new :class:`ExchangeRate` instance.

        Raises:
            .class:`InvalidCurrencyError` If either currency code is invalid.

        Examples:
            Create an exchange rate from USD to EUR::
            >>> rate = ExchangeRate.from_ratio("USD/EUR", "0.875")
            >>> rate = ExchangeRate.from_ratio("USD/EUR", Decimal("0.875"))
            Context information can be supplied as well::
            >>> rate = ExchangeRate.from_ratio(
            ...     "USD/EUR",
            ...     "0.875",
            ...     info=ExchangeRateInfo(...),
            )
        """
        _base, _term = ratio.split("/", 1)
        base = Currency.from_code(_base)
        term = Currency.from_code(_term)
        factor = _force_decimal(rate)
        return cls(base=base, quote=term, rate=factor, info=info)

    @classmethod
    def from_string(
        cls, expr: str, *, info: ExchangeRateInfo | None = None
    ) -> ExchangeRate:
        """Parse a single string expression like 'USD/EUR=0.8901'."""
        match = re.fullmatch(
            r"([A-Z0-9]{2,10}/[A-Z0-9]{2,10})(?:\s*[=:]\s*|\s+)([0-9.]+)",
            expr.strip().upper(),
        )
        if match is None:
            raise ValueError(f"Invalid rate string format: '{expr}'.")
        pair, rate = match.groups()
        return cls.from_pair(pair, rate, info=info)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Create an exchange rate from its serialized representation."""
        base = Currency.from_code(data["base"])
        quote = Currency.from_code(data["quote"])
        rate = Decimal(data["rate"])
        path: tuple[ExchangeRate, ...] = tuple()
        if "sources" in data:
            path = tuple(ExchangeRate.from_dict(rate) for rate in data["sources"])
        info = None
        if "info" in data:
            info = ExchangeRateInfo.from_dict(data["info"])
        return cls(base=base, quote=quote, rate=rate, path=path, info=info)

    def as_dict(self) -> ExchangeRateData:
        """Return the exchange rate as a serializable dictionary."""
        data: ExchangeRateData = {
            "base": self.base.ccy_code,
            "quote": self.quote.ccy_code,
            "rate": str(self.rate),
        }
        if self.path:
            data["sources"] = [src.as_dict() for src in self.lineage]
        if self.info is not None:
            data["info"] = self.info.as_dict()
        return data

    def __mul__(self, other: ExchangeRate) -> ExchangeRate:
        if not isinstance(other, ExchangeRate):
            return NotImplemented

        if self.quote != other.base:
            raise CurrencyMismatchError(
                f"Cannot multiply {self.base}/{self.quote} by "
                f"{other.base}/{other.quote}: "
                f"{self.quote} does not match {other.base}."
            )
        return ExchangeRate(
            base=self.base,
            quote=other.quote,
            rate=self.rate * other.rate,
            info=None,
            path=(self, other),
        )

    def invert(self) -> ExchangeRate:
        return ExchangeRate(
            base=self.quote,
            quote=self.base,
            rate=Decimal(1) / self.rate,
            info=self.info,
            path=tuple(src.invert() for src in self.path[::-1]),
        )

    def __str__(self) -> str:
        return f"{self.base!s}/{self.quote!s} = {self.rate!s}"
