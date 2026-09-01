from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pycents import Ccy, Currency, Money
from pycents.exceptions import CurrencyMismatchError
from pycents.money import UnroundedMoney
from pycents.rounding import RoundingMode


def _usd_money(amount: int, currency: str = "USD") -> Money:
    return Money(amount, Currency.from_code(currency))


@pytest.fixture(scope="session")
def money():
    def _amount(amount=200, ccy="USD"):
        return Money(amount, currency=Currency.from_code(ccy))

    return _amount


@pytest.fixture
def usd():
    return Currency(Ccy.USD)


@st.composite
def ordered_pairs(draw):
    n1 = draw(st.integers())
    n2 = draw(st.integers(min_value=n1))
    return (n1, n2)


@st.composite
def strict_ordered_pairs(draw):
    n1 = draw(st.integers())
    n2 = draw(st.integers(min_value=n1 + 1))
    return (n1, n2)


@st.composite
def ccy_code(draw):
    return draw(st.from_type(Ccy))


@st.composite
def rounding(draw):
    return draw(
        st.from_type(RoundingMode).filter(
            lambda rounding: rounding != RoundingMode.UNNECESSARY
        )
    )


@pytest.mark.parametrize(
    "minor_units, currency",
    [
        pytest.param(100, Currency(Ccy.USD), id="usd"),
        pytest.param(123456000, Currency(Ccy.EUR), id="eur"),
        pytest.param(-100, Currency(Ccy.JPY), id="negative amount"),
    ],
)
def test_money_init(minor_units, currency):
    money = Money(minor_units, currency=currency)

    assert money.minor_units == minor_units
    assert money._currency == currency


@pytest.mark.parametrize(
    "minor_units, currency",
    [
        pytest.param(100, "USD"),
        pytest.param(123456000, "EUR"),
        pytest.param(-100, "JPY"),
    ],
)
def test_money_from_minor(minor_units, currency):
    money = Money.from_minor(minor_units, currency)

    assert money.minor_units == minor_units
    assert money.currency.ccy_code == currency


def test_money_instances_are_immutable(money):
    with pytest.raises(AttributeError, match="Money instances are immutable"):
        money()._amount = 1000


def test_money_with_zero_amounts_are_cached():
    zero1 = Money.zero("USD")
    zero2 = Money.zero("USD")
    zero3 = Money.from_major(0, "USD")
    assert zero1 is zero2
    assert zero3 is zero2


@pytest.mark.parametrize(
    "amount,currency,expected",
    [
        pytest.param(
            Decimal("29"),
            "USD",
            2900,
            id="USD whole dollars",
        ),
        pytest.param(
            Decimal("29.3400"),
            "USD",
            2934,
            id="USD two decimals",
        ),
        pytest.param(
            Decimal("29000"),
            "JPY",
            29000,
            id="JPY no minor units",
        ),
        pytest.param(
            Decimal("29.123"),
            "KWD",
            29123,
            id="KWD three decimal places",
        ),
    ],
)
def test_from_major(amount, currency, expected):
    money = Money.from_major(amount, currency)
    assert money.minor_units == expected


@pytest.mark.parametrize(
    "amount,currency,expected",
    [
        pytest.param(
            Decimal("29.345"),
            "USD",
            Decimal("29.35"),
            id="USD too many fractional digits",
        ),
        pytest.param(
            Decimal("29.1"),
            "JPY",
            Decimal("30"),
            id="JPY fractional amount",
        ),
        pytest.param(
            Decimal("29.1234"),
            "KWD",
            Decimal("29.124"),
            id="KWD four fractional digits",
        ),
    ],
)
def test_from_major_round_numbers_with_more_then_minor_unit_decimals(
    amount, currency, expected
):
    mny = Money.from_major(amount, currency, rounding=RoundingMode.UP)
    assert mny.to_decimal() == expected


@pytest.mark.parametrize(
    "svalue",
    [
        pytest.param(
            Decimal("Inf"),
            id="positive Infinity",
        ),
        pytest.param(
            Decimal("-Inf"),
            id="negative Infinity",
        ),
        pytest.param(
            Decimal("NaN"),
            id="Quiet NaN",
        ),
        pytest.param(
            Decimal("sNaN"),
            id="Signaling NaN",
        ),
    ],
)
def test_money_from_major_rejects_non_finite_decimals(svalue):
    with pytest.raises(ValueError) as exc_info:
        Money.from_major(svalue, "USD")
    assert str(exc_info.value) == f"Special/infinite values are forbidden: {svalue!s}"


def test_money_as_dict(money):
    expected = {"minor_units": 200, "currency": "USD"}
    mny = money(200)
    assert mny.as_dict() == expected


def test_money_from_dict(money):
    data = {"minor_units": 200, "currency": "USD"}
    left = Money.from_dict(data)
    right = money(200)
    assert left == right


# Testing the Comparisons
@pytest.mark.parametrize(
    "self_,other,expected",
    [
        pytest.param(
            _usd_money(199),
            _usd_money(199),
            True,
            id="Same amount, same currencies",
        ),
        pytest.param(
            _usd_money(199),
            _usd_money(199, "EUR"),
            False,
            id="Same amounts, different currencies",
        ),
        pytest.param(
            _usd_money(199),
            _usd_money(200),
            False,
            id="Different amounts, same currencies",
        ),
        pytest.param(
            _usd_money(199),
            _usd_money(200, "EUR"),
            False,
            id="Different amounts, Different currencies",
        ),
        pytest.param(
            _usd_money(199),
            object(),
            False,
            id="Comparing with object",
        ),
    ],
)
def test_money_equality(self_, other, expected):
    assert (self_ == other) == expected


@given(strict_ordered_pairs())
def test_money_strict_comparison(pair):
    n1, n2 = pair
    ccy = Currency(Ccy.USD)
    left, right = Money(n1, currency=ccy), Money(n2, currency=ccy)
    assert left < right
    assert right > left


@given(ordered_pairs())
def test_money_equality_comparison(pair):
    n1, n2 = pair
    ccy = Currency(Ccy.USD)
    left, right = Money(n1, currency=ccy), Money(n2, currency=ccy)
    assert left <= right
    assert right >= left


def test_money_comparison_not_implemented_for_non_money(money):
    assert money().__lt__(object()) is NotImplemented


def test_money_comparison_raises_when_operands_have_different_currencies(money):
    other = money(499, "EUR")
    with pytest.raises(
        CurrencyMismatchError,
        match="Cannot compare money values with different currencies",
    ):
        _ = money() < other


# Test Arithmetic operations
@given(n=st.integers(), m=st.integers())
def test_money_add_return_expected_amount(n, m):
    left = Money(n, currency=Currency(Ccy.USD))
    right = Money(m, currency=Currency(Ccy.USD))
    result = left + right
    assert result.minor_units == n + m


@given(
    left=st.integers(),
    right=st.integers(),
)
def test_money_add_is_commutative(left, right):
    ccy = Currency(Ccy.USD)

    left = Money(left, currency=ccy)
    right = Money(right, currency=ccy)
    assert left + right == right + left


@given(
    first=st.integers(),
    second=st.integers(),
    third=st.integers(),
)
def test_money_add_is_associative(first, second, third):
    first = Money(first, currency=Currency(Ccy.USD))
    second = Money(second, currency=Currency(Ccy.USD))
    third = Money(third, currency=Currency(Ccy.USD))

    assert first + (second + third) == (first + second) + third


def test_money_add_not_implemented_for_non_money(money):
    assert money().__add__(object()) is NotImplemented


def test_money_add_raises_when_operand_have_different_currencies(money):
    left = money(100, "USD")
    right = money(200, "EUR")
    with pytest.raises(
        CurrencyMismatchError,
        match="Cannot add money amounts with different currencies.",
    ):
        _ = left + right


@given(st.integers(), st.integers())
def test_money_sub_return_expected_amount(n, m):
    left = Money(n, currency=Currency(Ccy.USD))
    right = Money(m, currency=Currency(Ccy.USD))
    result = left - right
    assert result.minor_units == n - m


@given(st.integers())
def test_money_sub_is_zero_when_operands_are_equal(n):
    left = Money(n, currency=Currency(Ccy.USD))
    right = Money(n, currency=Currency(Ccy.USD))
    result = left - right
    assert result.minor_units == 0


def test_money_sub_not_implemented_for_non_money(money):
    assert money().__sub__(object()) is NotImplemented


@given(st.integers())
def test_money_negation(n):
    money = Money(n, currency=Currency(Ccy.USD))

    assert (-money).minor_units == -n


@given(st.integers(min_value=-10, max_value=10))
def test_money_abs(n):
    mny = Money(n, Currency.from_code("USD"))
    assert abs(mny) == Money(abs(n), Currency.from_code("USD"))


def test_money_bool_dunder():
    zero = Money.zero("USD")
    not_zero = Money.from_minor(1000, "USD")
    assert not zero.__bool__()
    assert not_zero.__bool__()


@given(st.integers())
def test_money_negation_is_additive_inverse(n):
    money = Money(n, currency=Currency(Ccy.USD))
    zero = Money(0, currency=Currency(Ccy.USD))

    assert money + (-money) == zero


@given(st.integers(), st.integers())
def test_money_add_and_sub_are_compatible(n, m):
    left = Money(n, currency=Currency(Ccy.USD))
    right = Money(m, currency=Currency(Ccy.USD))
    result = Money(n - m, currency=Currency(Ccy.USD))
    assert right + result == left


def test_money_truediv_when_both_operands_are_money_objects():
    a = Money(5, currency=Currency(Ccy.USD))
    b = Money(2, currency=Currency(Ccy.USD))

    result = a / b
    assert result == Decimal("2.5")


def test_money_truediv_raises_when_operands_have_different_currencies():
    a = Money(5, currency=Currency(Ccy.USD))
    b = Money(2, currency=Currency(Ccy.EUR))

    with pytest.raises(CurrencyMismatchError):
        _ = a / b


@pytest.mark.parametrize(
    "money_,expected",
    [
        pytest.param(
            _usd_money(1234),
            Decimal("12.34"),
            id="Currency with two minor_unit",
        ),
        pytest.param(
            _usd_money(1234, "JPY"),
            Decimal("1234"),
            id="Currency with 0 minor_unit",
        ),
        pytest.param(
            _usd_money(1234, "KWD"),
            Decimal("1.234"),
            id="Currency with 3 minor_unit",
        ),
        pytest.param(
            _usd_money(12099, "KWD"),
            Decimal("12.099"),
            id="Add minor_unit trailing zeros",
        ),
    ],
)
def test_money_to_decimal(money_, expected):
    assert money_.to_decimal() == expected


@pytest.mark.parametrize(
    "amount, expected",
    [
        (100, 100),
        (101, 100),
        (102, 100),
        (103, 105),
        (104, 105),
        (105, 105),
        (106, 105),
        (107, 105),
        (108, 110),
        (109, 110),
    ],
)
def test_money_cash(amount, expected):
    mny = Money(amount, Currency.from_code("USD"))
    result = mny.cash(lambda x: int(round(x / 5.0) * 5))
    assert result._amount == expected


@pytest.mark.parametrize("amount, currency", [(299, "USD"), (199, "KWD"), (220, "EUR")])
def test_money_repr(amount, currency):
    mny = Money(amount, Currency.from_code(currency))
    assert repr(mny) == f"Money({amount}, '{currency}')"


@pytest.mark.parametrize(
    "amount, currency, expected",
    [
        (299, "USD", "USD\xa02.99"),
        (-199, "JPY", "-JPY\xa0199"),
        (220, "EUR", "EUR\xa02.20"),
    ],
)
def test_money_str(amount, currency, expected):
    mny = Money(amount, Currency.from_code(currency))
    assert str(mny) == expected


def test_money_bulk_sum(money):
    amounts = [money(i * 10) for i in range(100)]
    result = Money.sum(amounts)
    assert isinstance(result, Money)
    assert result._amount == 49500

    amounts[55] = amounts[55] * Decimal("1.53")
    result = Money.sum(amounts)

    assert isinstance(result, UnroundedMoney)
    assert result._amount == Decimal("49791.50")


def test_money_bulk_sum_rejects_empty_iterable():
    with pytest.raises(
        ValueError,
        match="Expected an iterable of Moneys objects, got an empty iterable",
    ):
        _ = Money.sum([])


def test_money_bulk_sum_rejects_different_currencies(money):
    seq = [money(10, "USD"), money(100, "EUR")]
    with pytest.raises(CurrencyMismatchError):
        Money.sum(seq)


def test_money_bulk_sum_with_no_rounding(money):
    seq = [money(2115, "USD"), money(120, "USD")]
    seq[0] = seq[0] / 1000
    result = Money.sum(seq)
    assert isinstance(result, UnroundedMoney)
    assert result._amount == Decimal("122.115")


def test_money_bulk_sum_with_rounding(money):
    seq = [money(2115, "USD"), money(120, "USD")]
    seq[0] = seq[0] / 1000
    result = Money.sum(seq, rounding=RoundingMode.UP)
    assert isinstance(result, Money)
    assert result._amount == 123


def test_money_divmod(money):
    mny = money(100)
    share, rest = divmod(mny, 3)
    assert share == Money(33, mny.currency)
    assert rest == Money(1, mny.currency)


def test_money_hash(money):
    mny = money(100, "USD")
    assert hash(mny) == hash((mny._amount, mny.currency))


@st.composite
def _any_money_unrounded(draw) -> UnroundedMoney:
    amount = draw(st.integers(min_value=-(10**19), max_value=10**19))
    return UnroundedMoney(Money(amount, Currency.from_code("USD")))


decimals = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("100"),
    places=6,
    allow_nan=False,
    allow_infinity=False,
)

non_zero_decimals = decimals.filter(lambda d: d != 0)


class Test_Unrounded_Money:
    def test_init(self, money):
        unrounded = UnroundedMoney(money())
        assert unrounded._amount == Decimal("200")
        assert unrounded._currency == Currency.from_code("USD")

    def test_unrounded_has_expected_currency(self, money):
        unrounded = UnroundedMoney(money())

        assert unrounded.currency == Currency.from_code("USD")

    def test_from_decimal(self):
        unrounded = UnroundedMoney.from_decimal(Decimal("2.99"), "USD")
        assert unrounded._currency.ccy_code == "USD"
        assert unrounded._amount == Decimal("299")

    @pytest.mark.parametrize(
        "amount, currency, expected",
        [
            (Decimal("123.1299"), "USD", Decimal("123.1299")),
            (Decimal("12312.99"), "JPY", Decimal("12312.99")),
        ],
    )
    def test_to_decimal(self, amount, currency, expected):
        unrounded = UnroundedMoney.from_decimal(amount, currency)
        assert unrounded.to_decimal() == expected

    def test_str_dunder_method(self, money):
        unrounded = UnroundedMoney.from_decimal("2.123", "USD")
        result = str(unrounded)
        assert result == f"{unrounded.currency.ccy_code}\xa02.123"

    def test_format_dunder_method(self):
        unrounded = UnroundedMoney.from_decimal("2.123", "USD")
        result = unrounded.__format__("h")
        assert result == "2.123"

    def test_negation(self):
        positive = UnroundedMoney.from_decimal("2.123", "USD")
        zero = UnroundedMoney.from_decimal("0", "USD")
        negative = UnroundedMoney.from_decimal("-2.123", "USD")

        assert -zero == zero
        assert -positive == negative

    @given(left=_any_money_unrounded(), right=_any_money_unrounded())
    def test_addition(self, left, right):
        result = left + right
        assert result._amount == left._amount + right._amount

    def test_addition_with_non_money_object(self, money):
        unrounded = UnroundedMoney(money(100))
        result = unrounded.__add__(object())  # type: ignore
        assert result is NotImplemented

    @given(left=_any_money_unrounded(), right=_any_money_unrounded())
    def test_substraction(self, left, right):
        result = left - right
        assert result._amount == left._amount - right._amount

    def test_substraction_with_non_money_object(self, money):
        unrounded = UnroundedMoney(money(100))
        result = unrounded.__sub__(object())  # type: ignore
        assert result is NotImplemented

    def test_reverse_substraction(self, money):
        unrounded = UnroundedMoney(money(100))
        mny = money(100)
        assert unrounded.__rsub__(mny) == UnroundedMoney(money(0))

    @given(mny=_any_money_unrounded(), factor=decimals)
    def test_multiplication(self, mny, factor):
        result = mny * factor
        assert result._amount == mny._amount * factor
        assert result._amount == factor * mny._amount

    def test_reverse_multiplication(self):
        unrounded = UnroundedMoney.from_decimal(Decimal("12.99"), "USD")
        result = Decimal("2.99") * unrounded
        assert isinstance(result, UnroundedMoney)
        assert result._amount == Decimal("1299") * Decimal("2.99")

    def test_multiplication_does_not_mutate_its_operand(self, money):
        unrounded = UnroundedMoney(money())
        original_amount = unrounded._amount
        _ = unrounded * Decimal("1.5")

        assert original_amount == unrounded._amount

    @given(mny=_any_money_unrounded(), left=decimals, right=decimals)
    def test_multiplication_is_associative_under_reasonable_input(
        self, mny, left, right
    ):
        # The range of inputs is encoded in the stategies
        # if the inputs are astronomically big, associativiy may break
        # du to implicit Decimal rounding to accomodate its context precision
        assert (mny * left) * right == mny * (left * right)

    @given(mny=_any_money_unrounded(), factor=non_zero_decimals)
    def test_true_division(self, mny, factor):
        result = mny / factor
        assert result._amount == mny._amount / factor

    def test_division_does_not_mutate_its_operand(self, money):
        unrounded = UnroundedMoney(money())
        original_amount = unrounded._amount
        _ = unrounded / Decimal("1.5")

        assert original_amount == unrounded._amount

    @given(mny=_any_money_unrounded())
    def test_division_by_one_return_the_same_amount(self, mny):
        result = mny / Decimal("1")
        assert result == mny

    def test_division_by_zero_raise_division_error(self, money):
        unrounded = UnroundedMoney(money())
        with pytest.raises(ZeroDivisionError):
            _ = unrounded / Decimal("0")

    def test_equality_with_any_object(self):
        unrounded = UnroundedMoney.from_decimal(Decimal("2.99"), "USD")
        result = unrounded.__eq__(object())
        assert result is NotImplemented

    def test_equality_with_difference_currencies(self):
        left = UnroundedMoney.from_decimal(Decimal("2.99"), "USD")
        right = UnroundedMoney.from_decimal(Decimal("2.99"), "EUR")

        assert not (left == right)

    @pytest.mark.parametrize(
        "left, right, expected",
        [
            (Decimal("2"), Decimal("5"), True),
            (Decimal("2"), Decimal("2"), False),
            (Decimal("5"), Decimal("1"), False),
        ],
    )
    def test_lt_comparison(self, left, right, expected):
        a = UnroundedMoney.from_decimal(left, "USD")
        b = UnroundedMoney.from_decimal(right, "USD")

        assert (a < b) == expected

    def test_lt_comparison_with_different_currencies(self):
        a = UnroundedMoney.from_decimal(Decimal("2"), "USD")
        b = UnroundedMoney.from_decimal(Decimal("3"), "EUR")
        with pytest.raises(CurrencyMismatchError):
            _ = a < b

    def test_lt_comparision_with_non_money_objects(self):
        a = UnroundedMoney.from_decimal(Decimal("2"), "EUR")
        assert a.__lt__(object()) is NotImplemented

    def test_repr(self):
        a = UnroundedMoney.from_decimal(Decimal("2"), "EUR")
        result = repr(a)
        assert result == f"Unrounded({Decimal('200')}, 'EUR')"


class Test_Money_Unrounded_Round:
    def test_round_preserves_currency(self, money):
        unrounded = UnroundedMoney(money())
        assert unrounded._currency == money().currency

    @pytest.mark.parametrize(
        "amount, rounding, expected",
        [
            (Decimal("123.4"), RoundingMode.HALF_EVEN, 123),
            (Decimal("123.5"), RoundingMode.HALF_EVEN, 124),
            (Decimal("124.5"), RoundingMode.HALF_EVEN, 124),
            (Decimal("123.5"), RoundingMode.HALF_UP, 124),
            (Decimal("123.5"), RoundingMode.DOWN, 123),
        ],
    )
    def test_round_produce_expected_result(self, amount, rounding, expected, money):
        unrounded = UnroundedMoney(money())
        unrounded._amount = amount
        assert unrounded.round(rounding) == money(expected)

    @given(amount=st.integers(-(10**19), 10**19), rounding=rounding())
    def test_round_integer_is_independant_of_rounding(self, amount, rounding, money):
        unrounded = UnroundedMoney(money())
        unrounded._amount = Decimal(amount)
        assert unrounded.round() == money(amount)

    @given(n=st.integers(1, 100))
    def test_round_multiplying_by_integer(self, n, money):
        mny = money(20)
        assert (mny * Decimal(str(n))).round() == (
            sum((money(20) for i in range(n)), Money.zero("USD"))
        )

    @given(amount=st.integers(-(10**19), 10**19))
    def test_round_after_division_by_one_is_identity(self, amount, money):
        unrounded = money(amount) / Decimal("1")
        assert unrounded.round() == money(amount)


class Test_Money_Unrounded_Properties:
    def test_chained_operations_preserve_order(self, money):
        expr = ((money(299) * Decimal("15")) / Decimal("0.15")) * Decimal("25")

        expected = Decimal("299") * Decimal("15") / Decimal("0.15") * Decimal("25")

        assert expr._amount == expected

    def test_round_after_chained_operations(self, money):
        result = ((money(199) * Decimal("15")) / Decimal("0.25")).round()

        expected = Money.from_major(
            Decimal(199) * Decimal("15") / Decimal("0.25") / 10**2, "USD"
        )

        assert result == expected


class Test_Money_Unrounded_Addition_Subtraction:
    def test_addition_unrounded_and_money(self, money):
        # Unrounded + Money -> Unrounded
        base = UnroundedMoney(money(100))
        result = base + money(50)

        assert isinstance(result, UnroundedMoney)
        assert result._amount == Decimal("150")

    def test_addition_money_and_unrounded(self, money):
        left = money(100)
        right = UnroundedMoney(left)
        result = left + right

        assert isinstance(result, UnroundedMoney)
        assert result._amount == Decimal("200")

    def test_addition_unrounded_and_unrounded(self, money):
        # Unrounded + Unrounded -> Unrounded
        u1 = UnroundedMoney(money(100)) * Decimal("1.5")
        u2 = UnroundedMoney(money(100)) * Decimal("0.5")
        result = u1 + u2

        assert isinstance(result, UnroundedMoney)
        assert result._amount == Decimal("200")

    def test_addition_subtraction_rejects_currency_mismatch(self, money):
        u_usd = UnroundedMoney(money(100))
        m_eur = Money.from_major(1, "EUR")

        with pytest.raises(CurrencyMismatchError):
            _ = u_usd + m_eur
        with pytest.raises(CurrencyMismatchError):
            _ = u_usd - m_eur

    def test_mult_money_by_integer_return_money(self, money):
        # Money * integer -> Money
        mny = money(100)
        result = mny * 10
        assert isinstance(result, Money)

    def test_mult_money_by_noninteger_return_unrounded(self, money):
        # Money * non-integer -> Money
        mny = money(100)
        result = mny * 10.0
        assert isinstance(result, UnroundedMoney)

    def test_mult_integer_by_money_return_money(self, money):
        mny = money(100)
        result = 10 * mny
        assert isinstance(result, Money)

    def test_mult_non_integer_by_money_return_unrounded(self, money):
        mny = money(100)
        result = 10.0 * mny
        assert isinstance(result, UnroundedMoney)

    def test_div_money_by_fact_return_unrounded(self, money):
        mny = money(100)
        result = mny / 5
        assert isinstance(result, UnroundedMoney)
        assert result._amount == Decimal("20")

    def test_div_money_by_money_return_decimal(self, money):
        num = money(100)
        den = money(10)
        result = num / den
        assert isinstance(result, Decimal)
        assert result == Decimal(10)
