from __future__ import annotations

from collections.abc import Callable, Iterable
from decimal import Decimal
from functools import total_ordering
from typing import Any, Self, final, overload

from pycents.formatting import format as money_format

from ._decimal import _decimal_places, _force_decimal, _remove_trailing_zeros
from .currency import Ccy, Currency, Xcy
from .exceptions import CurrencyMismatchError
from .formatting.protocols import _SupportMoneyOperation
from .rounding import RoundingMode, as_decimal_rounding

__all__ = ["Money", "UnroundedMoney", "MoneyLike"]


# Type Aliases
type MoneyLike = Money | UnroundedMoney


@total_ordering
@final
class UnroundedMoney(_SupportMoneyOperation):
    """
    Class to hold any intermediate result of a Sub-Unit arithmetic
    expressions.

    A sub-unit arithmetic operation is an operation on money that may produce
    an amount with more fractional digits than the currency's standard minor unit.

    Unrounded objects participate seamlessly with Money arithmetics
    according to the following rules:

    * Money + Money -> Money
    * Money - Money -> Money
    * Money + Unrounded -> Unrounded
    * Unrounded + Unrounded - > Unrounded
    * Money * IntegerFactor -> Money
    * Money * DecimalFactor -> Unrounded
    * Money / Factor -> Unrounded

    AN Unrounded object is not quite a Money in ISO4217 sens.
    Users must call `round()` on unrounded objects at the very end of arithmetic
    pipeline, to round the result and obtain a Money instance.
    """

    __slots__ = ("_amount", "_currency")

    def __init__(self, money: Money):
        self._amount = Decimal(money._amount)
        self._currency = money._currency

    @property
    def currency(self) -> Currency:
        return self._currency

    @classmethod
    def from_decimal(cls, amount: str | Decimal, currency: str) -> UnroundedMoney:
        amount = _force_decimal(amount)
        new = cls.__new__(cls)
        new._currency = Currency.from_code(currency)
        new._amount = amount * (10**new._currency.minor_units)
        return new

    def to_decimal(self) -> Decimal:
        mn_unit = self._currency.minor_units
        exponent = Decimal("1").scaleb(-mn_unit)
        ret = Decimal(self._amount) * exponent
        return _remove_trailing_zeros(ret)

    def __add__(self, other: MoneyLike) -> UnroundedMoney:
        if not isinstance(other, (UnroundedMoney, Money)):
            return NotImplemented
        if self._currency != other._currency:
            raise CurrencyMismatchError("Operands currencies must be equal")
        new = self.__class__.__new__(self.__class__)
        new._currency = self._currency
        new._amount = self._amount + other._amount
        return new

    def __neg__(self) -> UnroundedMoney:
        new = self.__class__.__new__(self.__class__)
        new._currency = self._currency
        new._amount = -self._amount
        return new

    def __sub__(self, other: MoneyLike) -> UnroundedMoney:
        if not isinstance(other, (UnroundedMoney, Money)):
            return NotImplemented
        if self._currency != other._currency:
            raise CurrencyMismatchError("Operands currencies must be equal")
        new = self.__class__.__new__(self.__class__)
        new._currency = self._currency
        new._amount = self._amount - other._amount
        return new

    def __rsub__(self, other: MoneyLike) -> UnroundedMoney:
        return -(self - other)

    def __mul__(self, factor: int | Decimal) -> UnroundedMoney:
        factor = _force_decimal(factor)
        new = self.__class__.__new__(self.__class__)
        new._currency = self._currency
        new._amount = self._amount * factor
        return new

    def __rmul__(self, factor: Decimal) -> UnroundedMoney:
        return self * factor

    def __truediv__(self, factor: int | Decimal) -> UnroundedMoney:
        factor = _force_decimal(factor)
        new = self.__class__.__new__(self.__class__)
        new._currency = self._currency
        new._amount = self._amount / factor
        return new

    def round(self, rounding: RoundingMode = RoundingMode.HALF_EVEN) -> Money:
        """Round this result to the currency's standard minor units.

        Args:
            rounding: A member of RoundingMode enumeration. Defaults to
                :attr:`RoundingMode.HALF_EVEN`

        Returns:
            A ``Money`` instance containing the quantized result in minor units.
        """
        # TODO Maybe avoid rounding if self.amount is an integer? profile
        rounded = self._amount.quantize(
            Decimal("1"), rounding=as_decimal_rounding(rounding)
        )
        return Money(int(rounded), self._currency)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UnroundedMoney):
            return NotImplemented
        return self._amount == other._amount and self._currency == other._currency

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, UnroundedMoney):
            return NotImplemented

        if self._currency != other._currency:
            raise CurrencyMismatchError(
                "Cannot compare money values with different currencies"
            )
        return self._amount < other._amount

    def __repr__(self) -> str:
        return f"Unrounded({self._amount}, '{self._currency.ccy_code}')"

    def __str__(self) -> str:
        return f"{self._currency.ccy_code}\xa0{self.to_decimal()}"

    def __format__(self, format_spec: str) -> str:
        return money_format(self, format_spec)


@total_ordering
@final
class Money(_SupportMoneyOperation):
    """Represents an immutable monetary amount in a specific ISO 4217 currency.

    Monetary amounts are stored internally as an integer number of minor units
    (for example, cents for USD). Arithmetic and comparison operations are only
    permitted between Money objects that share the same currency.
    Money instances are exact. No rounding is performed when constructing
    or manipulating monetary amounts.

    Args
        minor_units: The monetary amount expressed in the currency's minor units.
        currency: The currency associated with the monetary amount.
    """

    _amount: int
    _currency: Currency

    __slots__ = ("_amount", "_currency")

    __match_args__ = ("_amount", "_currency")

    _zero_cache: dict[str, Self] = {}

    def __init__(self, minor_units: int, currency: Currency) -> None:
        object.__setattr__(self, "_amount", minor_units)
        object.__setattr__(self, "_currency", currency)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{type(self).__name__} instances are immutable")

    @classmethod
    def zero(cls, currency: Ccy | Xcy | str) -> Money:
        """Create a zero-valued Money instance for the given currency.

        The zero-valued instance is cached and reused for subsequent
        calls with the same currency.

        Args:
            currency: Currency of the zero-valued money.

        Returns:
            A Money instance with an amount of zero in the given currency.
        """
        ccy = Currency.from_code(currency)
        code = ccy.ccy_code
        if code not in cls._zero_cache:
            cls._zero_cache[code] = cls(0, ccy)
        return cls._zero_cache[code]

    @classmethod
    def from_major(
        cls,
        amount: int | str | Decimal,
        currency: Ccy | Xcy | str,
        *,
        rounding: RoundingMode = RoundingMode.HALF_EVEN,
    ) -> Money:
        """Construct a Money instance from an amount expressed in major units.

        Args:
            amount: The monetary amount expressed in major units.
            currency: Either a member of the ``Ccy`` enumeration
                or a three-letter ISO 4217 currency code.
            rounding: The rounding policy if the decimal/float has more decimals then
                the currency supports

        Returns:
            The corresponding Money instance.

        Note:
            The input amount will be rounded to accommodate for the currency's
            standard minor units. The rounding mode is constrolled via the
            keyword argument `rounding`. If no rounding is supplied,
            `RoundingMode.HALF_EVEN` will be used.

        Examples
        --------
        >>> Money.from_major(Decimal("29.34"), "USD")
        Money(amount=2934, currency='USD')
        >>> Money.from_major(Decimal("29.345", "USD", rounding=RoundingPolicy.UP))
        Money(amount=2935, currency='USD')
        >>> Money.from_major(29.99, Ccy.USD)
        Money(amount=2999, currency='USD')
        """
        decimal_amount = _force_decimal(amount)
        ccy = Currency.from_code(currency)
        decimal_amount = cls._validate_amount(decimal_amount, ccy, rounding)
        if decimal_amount == 0:
            return cls.zero(currency)
        minor_units = int(decimal_amount * (10**ccy.minor_units))
        return cls(minor_units, currency=ccy)

    @staticmethod
    def _validate_amount(
        amount: Decimal,
        currency: Currency,
        rounding: RoundingMode = RoundingMode.HALF_EVEN,
    ) -> Decimal:
        if not amount.is_finite():
            raise ValueError(f"Special/infinite values are forbidden: {amount}")
        exponent = _decimal_places(amount)
        if exponent > currency.minor_units:
            exp = Decimal("1").scaleb(-currency.minor_units)
            amount = amount.quantize(exp, rounding=as_decimal_rounding(rounding))
        return amount

    @property
    def currency(self) -> Currency:
        """The currency associated with this monetary amount.

        Returns:
            currency: The Money object's currency.
        """
        return self._currency

    @property
    def minor_units(self) -> int:
        """
        The monetary amount expressed in minor units.

        Returns:
            The amount stored internally as an integer number of minor units.
        """
        return self._amount

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented

        return self._currency == other._currency and self._amount == other._amount

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented

        if self._currency != other._currency:
            raise CurrencyMismatchError(
                "Cannot compare money values with different currencies"
            )
        return self._amount < other._amount

    @overload
    def __add__(self, other: Money) -> Money: ...

    @overload
    def __add__(self, other: UnroundedMoney) -> UnroundedMoney: ...

    def __add__(self, other: MoneyLike) -> MoneyLike:
        if not isinstance(other, (Money, UnroundedMoney)):
            return NotImplemented
        if self._currency != other._currency:
            raise CurrencyMismatchError(
                "Cannot add money amounts with different currencies."
            )
        if isinstance(other, Money):
            return Money(
                self._amount + other._amount,
                self._currency,
            )
        return UnroundedMoney(self) + other

    @overload
    def __sub__(self, other: Money) -> Money: ...

    @overload
    def __sub__(self, other: UnroundedMoney) -> UnroundedMoney: ...

    def __sub__(self, other: MoneyLike) -> MoneyLike:
        if not isinstance(other, Money):
            return NotImplemented
        return self + (-other)

    def __neg__(self) -> Money:
        return Money(-self._amount, currency=self._currency)

    def __divmod__(self, divisor: int) -> tuple[Money, Money]:
        quot, rem = divmod(self._amount, divisor)
        return (
            Money(quot, currency=self._currency),
            Money(rem, currency=self._currency),
        )

    @overload
    def __mul__(self, factor: int) -> Money: ...

    @overload
    def __mul__(self, factor: Decimal) -> UnroundedMoney: ...

    def __mul__(self, factor: int | Decimal) -> MoneyLike:
        if type(factor) is int:
            return Money(self._amount * factor, self._currency)

        return UnroundedMoney(self) * factor

    def __rmul__(self, factor: int | Decimal) -> MoneyLike:
        return self * factor

    @overload
    def __truediv__(self, factor: Money) -> Decimal: ...

    @overload
    def __truediv__(self, factor: int | Decimal) -> UnroundedMoney: ...

    def __truediv__(self, factor: int | Decimal | Money) -> Decimal | UnroundedMoney:
        if isinstance(factor, Money):
            return Decimal(self._amount) / Decimal(factor._amount)
        unrounded = UnroundedMoney(self) / factor
        return unrounded

    def __abs__(self) -> Money:
        return Money(abs(self._amount), self.currency)

    @classmethod
    def sum(
        cls, iterable: Iterable[MoneyLike], *, rounding: RoundingMode | None = None
    ) -> MoneyLike:
        """Bulk addition for Money."""
        iterator = iter(iterable)
        try:
            first_item = next(iterator)
        except StopIteration:
            raise ValueError(
                "Expected an iterable of Moneys objects, got an empty iterable"
            ) from None
        ccy = first_item._currency
        total = first_item._amount
        for item in iterator:
            if item._currency != ccy:
                raise CurrencyMismatchError(
                    "Cannot add money amounts with different currencies."
                )
            total += item._amount
        if isinstance(total, int):
            return cls(total, ccy)
        unrounded = UnroundedMoney(Money.zero(ccy.ccy_code))
        unrounded._amount = total
        if rounding is not None:
            return unrounded.round(rounding)
        return unrounded

    def to_decimal(self) -> Decimal:
        """
        Convert the monetary amount to its major-unit representation.

        The returned Decimal always uses the exact number of fractional digits
        defined by the currency's minor units.

        Returns:
            The amount expressed in major units.

        Examples
        --------
        >>> Money(2934, Currency(Ccy.USD)).to_decimal()
        Decimal('29.34')
        >>> Money(29, Currency(Ccy.JPY)).to_decimal()
        Decimal('29')
        >>> Money(29123, Currency(Ccy.KWD)).to_decimal()
        Decimal('29.123')
        """
        mn_unit = self._currency.minor_units
        exponent = Decimal("1").scaleb(-mn_unit)
        ret = Decimal(self._amount) * exponent
        return ret

    def as_dict(self) -> dict[str, Any]:
        return {"minor_units": self._amount, "currency": self._currency.ccy_code}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Money:
        """Reconstruct a Money instance from a dictionary payload."""
        return cls(data["minor_units"], Currency.from_code(data["currency"]))

    def cash(self, rounding: Callable[[int], int]) -> Money:
        """Applies a custom cash-rounding strategy to the minor units amount.

        This is useful for physical cash transaction where the total must be
        rounded to the nearest physical coin denomination.

        For example, following the phase-out of the penny in Canada in 2013
        (and the United States in february 2025), cash transactions are required to be
        rounded to the nearest 5 cents (nickel), while electronic transactions
        continue to be processed to the exact cent.

        Note:
            Thanks to the random guy from discord that brought this case to my
            attention

        Args:
            rounding: A function that takes the current minor unit as an integer
            and returns the newly rounded minor unit amount

        Returns:
            A Money instance containing the rounded amount with the same currency

        Examples:
            >>> # Canadian cash rounding (nearest 5 cents)
            >>> def cad_round_cash(amount: int) -> int:
            ...     return int(round(amount / 5.0) * 5)
            ...
            >>> total = Money.from_major("12.03", "USD")
            >>> cash = total.cash(cand_round_cash)
            >>> print(cash)
        """
        amount = rounding(self._amount)
        return Money(amount, self._currency)

    def __hash__(self) -> int:
        return hash((self._amount, self._currency))

    def __repr__(self) -> str:
        return f"Money({self._amount}, '{self._currency.ccy_code}')"

    def __str__(self) -> str:
        fmt = "{sign}{currency}\xa0{number}"
        sign = "-" if self._amount < 0 else ""
        return fmt.format(
            sign=sign, currency=self._currency.ccy_code, number=abs(self.to_decimal())
        )

    def __format__(self, format_spec: str) -> str:
        """
        Format the monetary amount.

        Format specification grammar
        ----------------------------

        money-format ::= money-spec string-format

        money-spec ::= [display] [compact-precision] [compact] [accounting] [ungroup]

        display ::= h | i | n
        compact-precision ::= .integer
        compact ::= c
        accounting ::= a
        ungroup ::= u

        Display options:
            h: Hide the currency symbol.
            i: Display the ISO 4217 currency code.
            n: Display the currency name.
            .integer: Specify the number of fractional digits to display
                      when using compact notation
            c: Use compact notation (for example, ``1.2M``).
            a: Display negative amounts using accounting notation
               (for example, ``(123.45)`` instead of ``-123.45``).
            u: Disable digit grouping
               (for example, ``1000000`` instead of ``1,000,000``).

        string-format:
            Python's standard string format specification.
            It is applied after the money-specific options.

        Examples:
            >>> f"{money:}"
            >>> f"{money:h}"
            >>> f"{money:h.2c}"
            >>> f"{money:ia}"
            >>> f"{money:hc>20}"
        """
        return money_format(self, format_spec)
