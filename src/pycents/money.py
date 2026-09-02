from __future__ import annotations

from collections.abc import Callable, Iterable
from decimal import Decimal
from functools import total_ordering
from typing import Any, Self, final, overload
from warnings import deprecated

from pycents.formatting import format as money_format

from ._decimal import _decimal_places, _force_decimal, _trim_trailing_zeros
from .currency import Ccy, Currency, Xcy
from .exceptions import CurrencyMismatchError
from .protocols import MonetaryAmount
from .rounding import RoundingMode, as_decimal_rounding

__all__ = ["Money", "UnroundedMoney"]


@total_ordering
@final
class UnroundedMoney(MonetaryAmount):
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

    @property
    def as_majors(self) -> Decimal:
        """Return the monetary amount expressed in major currency units.

        Unlike ``Money``, the returned amount may contain more fractional
        digits than the currency's standard minor unit.

        Returns:
        The amount expressed in major currency units.
        """
        mn_unit = self._currency.minor_units
        exponent = Decimal("1").scaleb(-mn_unit)
        ret = Decimal(self._amount) * exponent
        return _trim_trailing_zeros(ret)

    @property
    def _as_decimal(self) -> Decimal:
        return self._amount

    @classmethod
    @deprecated("use 'from_major()' instead")
    def from_decimal(
        cls, amount: int | str | Decimal, currency: str | Ccy | Xcy
    ) -> UnroundedMoney:
        return cls.from_major(amount, currency)

    @classmethod
    def from_major(
        cls, amount: int | str | Decimal, currency: str | Ccy | Xcy
    ) -> UnroundedMoney:
        amount = _force_decimal(amount)
        new = cls.__new__(cls)
        new._currency = Currency.from_code(currency)
        new._amount = amount * (10**new._currency.minor_units)
        return new

    @deprecated("Use the 'as_majors' property instead.")
    def to_decimal(self) -> Decimal:
        return self.as_majors

    def __add__(self, other: MonetaryAmount) -> UnroundedMoney:
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

    def __sub__(self, other: MonetaryAmount) -> UnroundedMoney:
        if not isinstance(other, (UnroundedMoney, Money)):
            return NotImplemented
        if self._currency != other._currency:
            raise CurrencyMismatchError("Operands currencies must be equal")
        new = self.__class__.__new__(self.__class__)
        new._currency = self._currency
        new._amount = self._amount - other._amount
        return new

    def __rsub__(self, other: MonetaryAmount) -> UnroundedMoney:
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

    def __abs__(self) -> UnroundedMoney:
        new = self.__class__.__new__(self.__class__)
        new._currency = self._currency
        new._amount = abs(self._amount)
        return new

    def __bool__(self) -> bool:
        return self._amount != 0

    def __hash__(self) -> int:
        return hash((self._amount, self._currency))

    def __repr__(self) -> str:
        return f"Unrounded({self._amount}, '{self._currency.ccy_code}')"

    def __str__(self) -> str:
        return f"{self._currency.ccy_code}\xa0{self.as_majors}"

    def __format__(self, format_spec: str) -> str:
        return money_format(self, format_spec)


@total_ordering
@final
class Money(MonetaryAmount):
    """Represents an immutable monetary amount in a specific ISO 4217 currency
    or a custom one.

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

    @property
    def _as_decimal(self) -> Decimal:
        return Decimal(self._amount)

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
    def from_minor(cls, amount: int, currency: Ccy | Xcy | str) -> Money:
        """Construct a Money instance from an amount expressed in minor units.

        Args:
            amount: The monetary amount expressed in minor units (e.g cents).
            currency: Either a member of the ``Ccy``/``Xcy``,
                or an alphabetic currency code.

        Returns:
            The corresponding Money instance.

        Notes:
            This method is equivalent to calling the Money constructor after
            resolving the currency from its code.

            Unlike the constructor, from_minor() accepts a currency code as a
            string in addition to a Ccy or Xcy instance.

            For example:

            `Money.from_minor(100, "EUR")` is equivalent to `Money(100, Ccy.EUR)`.
        """
        ccy = Currency.from_code(currency)
        return cls(amount, ccy)

    @classmethod
    def from_major(
        cls,
        amount: int | str | Decimal,
        currency: Ccy | Xcy | str,
        *,
        rounding: RoundingMode | None = None,
    ) -> Money:
        """Construct a Money instance from an amount expressed in major units.

        Args:
            amount: The monetary amount expressed in major units.
            currency: Either a member of the ``Ccy``/``Xcy``,
                or an alphabetic currency code.
            rounding: The rounding mode to use if the amount has more
                fractional digits than the currency supports.
                If ``None``, an exception is raised when the amount cannot
                be represented exactly.

        Returns:
            The corresponding Money instance.

        Raises:
            ValueError: If ``amount`` is not finite, or if it has more fractional digits
            than the currency supports and no ``rounding`` mode was specified.

        Note:
            ``Money`` only represents amounts that can be expressed exactly
            using the currency's standard minor units. If the input amount has more
            fractional digits than the currency supports, an explicit rounding mode
            must be supplied.
            When ``rounding`` is ``None``, the input is rejected rather than being
            rounded implicitly.

        Examples
        --------
        >>> Money.from_major(Decimal("29.34"), "USD")
        Money(2934, 'USD')
        >>> Money.from_major(Decimal("29.345"), "USD")
        Traceback (most recent call last):
        ...
        ValueError: Amount 29.345 has more fractional digits ...
        >>> Money.from_major(Decimal("29.345"), "USD", rounding=RoundingPolicy.UP))
        Money(2935, 'USD')
        >>> Money.from_major("29.99", Ccy.USD)
        Money(2999, 'USD')
        """
        decimal_amount = _force_decimal(amount)
        ccy = Currency.from_code(currency)
        decimal_amount = cls._validate_amount(decimal_amount, ccy, rounding)
        if decimal_amount.is_zero():
            return cls.zero(currency)
        minor_units = int(decimal_amount * (10**ccy.minor_units))
        return cls(minor_units, currency=ccy)

    @staticmethod
    def _validate_amount(
        amount: Decimal,
        currency: Currency,
        rounding: RoundingMode | None = None,
    ) -> Decimal:
        if not amount.is_finite():
            raise ValueError(f"Special/infinite values are forbidden: {amount}")
        exponent = _decimal_places(amount)

        if exponent <= currency.minor_units:
            return amount

        if rounding is None:
            raise ValueError(
                f"Amount {amount} has more fractional digits than the "
                f"{currency.ccy_code} minor units: {currency.minor_units}.\n"
                "Specify a rounding mode to convert it to a valid monetary amount."
            )

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
    @deprecated("Use the 'as_minors' property instead.")
    def minor_units(self) -> int:
        """
        The monetary amount expressed in minor units.

        Returns:
            The amount stored internally as an integer number of minor units.
        """
        return self._amount

    @property
    def as_majors(self) -> Decimal:
        """
        Convert the monetary amount to its major-unit representation.

        The returned Decimal always uses the exact number of fractional digits
        defined by the currency's minor units.

        Returns:
            The amount expressed in major units.

        Examples
        --------
        >>> Money(2934, Currency(Ccy.USD)).as_majors
        Decimal('29.34')
        >>> Money(29, Currency(Ccy.JPY)).as_majors
        Decimal('29')
        >>> Money(29123, Currency(Ccy.KWD)).as_majors
        Decimal('29.123')
        """
        mn_unit = self._currency.minor_units
        exponent = Decimal("1").scaleb(-mn_unit)
        ret = Decimal(self._amount) * exponent
        return ret

    @property
    def as_minors(self) -> int:
        """Return the monetary amount expressed in minor currency units.

        This is the preferred way to access the amount in minor units.
        Use this property instead of :attr:`minor_units`.

        Returns:
            The amount stored internally as an integer number of minor units.
        """
        return self._amount

    @deprecated("Use the 'as_majors' property instead.")
    def to_decimal(self) -> Decimal:
        """
        Convert the monetary amount to its major-unit representation.

        The returned Decimal always uses the exact number of fractional digits
        defined by the currency's minor units.

        Returns:
            The amount expressed in major units.

        Notes:
            This method is deprecated. Use the 'as_majors' property instead.
        """
        return self.as_majors

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

    def __add__(self, other: MonetaryAmount) -> MonetaryAmount:
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

    def __sub__(self, other: MonetaryAmount) -> MonetaryAmount:
        if not isinstance(other, (Money, UnroundedMoney)):
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

    def __mul__(self, factor: int | Decimal) -> MonetaryAmount:
        if type(factor) is int:
            return Money(self._amount * factor, self._currency)
        return UnroundedMoney(self) * factor

    def __rmul__(self, factor: int | Decimal) -> MonetaryAmount:
        return self * factor

    @overload
    def __truediv__(self, factor: Money) -> Decimal: ...

    @overload
    def __truediv__(self, factor: int | Decimal) -> UnroundedMoney: ...

    def __truediv__(self, factor: int | Decimal | Money) -> MonetaryAmount | Decimal:
        if isinstance(factor, Money):
            if self.currency != factor.currency:
                raise CurrencyMismatchError(
                    "Cannot divide money amounts with different currencies"
                )
            return Decimal(self._amount) / Decimal(factor._amount)
        unrounded = UnroundedMoney(self) / factor
        return unrounded

    def __abs__(self) -> Money:
        return Money(abs(self._amount), self.currency)

    def __bool__(self) -> bool:
        """Return ``False`` if the monetary amount is zero."""
        return self._amount != 0

    @classmethod
    def sum(
        cls, iterable: Iterable[MonetaryAmount], *, rounding: RoundingMode | None = None
    ) -> MonetaryAmount:
        """Bulk addition for Money."""
        iterator = iter(iterable)
        try:
            first_item = next(iterator)
        except StopIteration:
            raise ValueError(
                "Expected an iterable of Moneys objects, got an empty iterable"
            ) from None
        ccy = first_item.currency
        total = first_item._as_decimal
        for item in iterator:
            if item.currency != ccy:
                raise CurrencyMismatchError(
                    "Cannot add money amounts with different currencies."
                )
            total += item._as_decimal
        if total == total.to_integral_value():
            return cls(int(total), ccy)

        unrounded = UnroundedMoney(Money.zero(ccy.ccy_code))
        unrounded._amount = total
        if rounding is not None:
            return unrounded.round(rounding)
        return unrounded

    def __hash__(self) -> int:
        return hash((self._amount, self._currency))

    def __repr__(self) -> str:
        return f"Money({self._amount}, '{self._currency.ccy_code}')"

    def __str__(self) -> str:
        fmt = "{sign}{currency}\xa0{number}"
        sign = "-" if self._amount < 0 else ""
        return fmt.format(
            sign=sign, currency=self.currency.ccy_code, number=abs(self.as_majors)
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
