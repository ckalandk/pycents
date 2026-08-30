from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import ClassVar

from .exceptions import InvalidCurrencyError
from .iso4217 import Ccy
from .xcy import Xcy

__all__ = ["Currency", "Ccy", "Xcy"]


@dataclass(frozen=True, slots=True)
class Currency:
    """
    Represents an ISO 4217 currency or a custom currency.

    A Currency object provides metadata associated with an ISO 4217
    currency code, including its alphabetic code, numeric code, name,
    and number of minor units, the same metadas are also provided for custom
    currencies. Currency instances are immutable and
    cached internally.

    Attributes
    ----------
    ccy_code : str
        The alphabetic currency code (e.g. ``"USD"``).
    ccy_name : str
        The Currency name (e.g. ``"US Dollar"``).
    minor_units : int
        The number of decimal places used by the currency.
        For example, USD uses two minor units while JPY uses none.
    ccy_num_code : int
        The ISO 4217 numeric currency code. Custom currencies
        also receive a unique numerical code.
    """

    ccy: InitVar[Ccy | Xcy]
    ccy_code: str = field(init=False)
    ccy_name: str = field(init=False, repr=False)
    minor_units: int = field(init=False, repr=False)
    ccy_num_code: int = field(init=False, repr=False)

    _cache: ClassVar[dict[Ccy | Xcy, Currency]] = {}

    def __new__(cls, ccy: Ccy | Xcy) -> Currency:
        if ccy in cls._cache:
            return cls._cache[ccy]
        obj = object.__new__(cls)
        cls._cache[ccy] = obj
        return obj

    def __post_init__(self, ccy: Ccy | Xcy) -> None:
        if not isinstance(ccy, (Ccy, Xcy)):
            raise TypeError(
                f"Expected an instance of Ccy or Xcy, got {type(ccy).__name__}"
            )
        object.__setattr__(self, "ccy_code", ccy.ccy_code)
        object.__setattr__(self, "ccy_name", ccy.ccy_name)
        object.__setattr__(self, "minor_units", ccy.minor_units)
        object.__setattr__(self, "ccy_num_code", ccy.ccy_num_code)

    @classmethod
    def from_code(cls, ccy: Xcy | Ccy | str) -> Currency:
        """
        Construct a Currency instance from a currency code.

        Parameters
        ----------
        ccy : Xcy | Ccy | str
            Either a member of the ``Ccy``/``Xcy`` or a
            an alphabetic currency code (e.g. ``"USD"``, ``"USDT"``).

        Returns
        -------
        Currency
            The corresponding Currency instance.

        Raises
        ------
        ValueError
            If the supplied string is not a valid currency code.

        Examples
        --------
        >>> Currency.from_code(Ccy.USD)
        Currency(ccy_code='USD')
        >>> Currency.from_code("BTC")
        Currency(ccy_code='BTC')
        """
        if isinstance(ccy, str):
            code_upper = ccy.upper()
            curr = Ccy.__members__.get(code_upper) or getattr(Xcy, code_upper, None)

            if curr is None:
                raise InvalidCurrencyError(f"'{ccy}' is not a known currency code.")
        else:
            curr = ccy

        return cls(curr)

    def _is_iso(self) -> bool:
        return self.ccy_num_code < 1000

    def _get_xcy_def(self) -> Xcy:
        if self._is_iso():
            raise ValueError("Cannot get Xcy definition for an ISO currency")
        return Xcy[self.ccy_code]
