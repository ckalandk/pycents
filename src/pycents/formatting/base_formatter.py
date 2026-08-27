from abc import ABC, abstractmethod
from decimal import Decimal

from pycents.currency import Currency
from pycents.rounding import RoundingMode

from .formatspec import DisplayOpts, FormatSpec


class BaseFormatter(ABC):
    """Base class for all Money's backend formatter"""

    def __init__(self, locale: str):
        self._locale = locale
        self._default_spec = FormatSpec()
        self._numbering_system: str | None = None
        self._rounding: RoundingMode = RoundingMode.HALF_EVEN

    @property
    def locale(self) -> str:
        return str(self._locale)

    @locale.setter
    def locale(self, value: str) -> None:
        self._locale = value

    @property
    def numbering_system(self) -> str | None:
        return self._numbering_system

    @numbering_system.setter
    def numbering_system(self, value: str | None) -> None:
        self._validate_numbering_system(value)
        self._numbering_system = value

    @abstractmethod
    def _validate_numbering_system(self, value: str | None) -> None:
        """
        Backends must implement this to reject invalid numbering systems.

        Raise UnsupportedBackendFeatureError if invalid.
        """
        pass

    def configure(
        self,
        *,
        ccy_display: DisplayOpts | None = None,
        compact: bool | None = None,
        compact_precision: int | None = None,
        accounting: bool | None = None,
        group_separator: bool | None = None,
        rounding: RoundingMode | None = None,
    ) -> None:
        self._default_spec.update(
            ccy_display, compact, compact_precision, accounting, group_separator
        )
        if rounding is not None:
            self._rounding = rounding

    @abstractmethod
    def format(
        self,
        amount: Decimal,
        currency: Currency,
        spec: FormatSpec,
    ) -> str:
        raise NotImplementedError
