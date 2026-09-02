from random import randint

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pycents.allocation import allocate, allocate_base, hamilton, round_robin
from pycents.money import Money

amounts_st = st.integers(min_value=0, max_value=1_000_000_000)

ratios_st = st.lists(
    st.integers(min_value=0, max_value=10_000), min_size=1, max_size=100
).filter(lambda r: sum(r) > 0)

strictly_positive_ratios_st = st.lists(
    st.integers(min_value=1, max_value=100), min_size=2, max_size=100
)

strictly_increasing = st.sets(
    st.integers(min_value=1, max_value=10_000), min_size=2
).map(sorted)


@given(amount=amounts_st, ratios=ratios_st)
def test_hamilton_never_loses_pennies(amount: int, ratios: list[int]):
    result = hamilton(amount, ratios)

    assert len(result) == len(ratios), "Must return exactly one share per ratio"
    assert sum(result) == amount, (
        "The sum of shares must exactly equal the original amount"
    )
    for i, ratio in enumerate(ratios):
        if ratio == 0:
            assert result[i] == 0


@given(amount=amounts_st, ratios=ratios_st)
def test_round_robin_never_loses_pennies(amount: int, ratios: list[int]):
    result = round_robin(amount, ratios)

    assert len(result) == len(ratios)
    assert sum(result) == amount
    for i, ratio in enumerate(ratios):
        if ratio == 0:
            assert result[i] == 0


@pytest.mark.parametrize(
    "amount, ratios, expected_hamilton, expected_rr",
    [
        # Even split: remainders are tied
        (100, [1, 1, 1], [34, 33, 33], [34, 33, 33]),
        # 100 split by [3, 4, 4]
        # RR: base is [27, 36, 36], 1 leftover penny goes to index 0
        # Hamilton: fractions are [0.27, 0.36, 0.36]. 1 penny goes to index 1
        (100, [3, 4, 4], [27, 37, 36], [28, 36, 36]),
        # Zero ratios involved
        (10, [1, 0, 1], [5, 0, 5], [5, 0, 5]),
        (100, [0, 1, 1], [0, 50, 50], [0, 50, 50]),
        # Zero money
        (0, [1, 2, 3], [0, 0, 0], [0, 0, 0]),
    ],
)
def def_test_strategies_with_known_data(amount, ratios, expected_hamilton, expected_rr):
    assert hamilton(amount, ratios) == expected_hamilton
    assert round_robin(amount, ratios) == expected_rr


def test_allocate_base_preserves_remainder():
    money = Money.from_major(1, "USD")
    ratios = [1, 1, 1]

    shares, remainder = allocate_base(money, ratios)

    assert len(shares) == 3
    assert all(isinstance(s, Money) for s in shares)
    assert [s.as_minors for s in shares] == [33, 33, 33]

    assert isinstance(remainder, Money)
    assert remainder.as_minors == 1
    assert remainder._currency.ccy_code == "USD"


def test_allocate_integration_default_strategy():
    money = Money.from_major(1, "USD")
    result = allocate(money, [3, 4, 4])

    assert all(isinstance(s, Money) for s in result)
    assert [s.as_minors for s in result] == [27, 37, 36]


def test_allocate_integration_explicit_strategy():
    money = Money.from_major(1, "USD")
    result = allocate(money, [3, 4, 4], strategy=round_robin)

    assert [s.as_minors for s in result] == [28, 36, 36]


def test_allocation_validations_trigger_correctly():
    money = Money.from_major(10000, "USD")

    # Empty ratio
    with pytest.raises(ValueError, match="Sum of ratios must be greater than zero"):
        allocate(money, [])

    # Zero sum ratios
    with pytest.raises(ValueError, match="Sum of ratios must be greater than zero"):
        allocate(money, [0, 0, 0])

    # Negative ratios
    with pytest.raises(ValueError, match="Ratios cannot contain negative values"):
        allocate(money, [1, -1])

    # Negative money boundary
    negative_money = Money.from_major(-50, "USD")
    with pytest.raises(ValueError, match="Expected positive money"):
        allocate(negative_money, [1, 1])


@pytest.mark.parametrize("strategy", [hamilton, round_robin])
@given(
    amount=amounts_st,
    ratios=ratios_st,
    multiplier=st.integers(min_value=2, max_value=1000),
)
def test_allocation_homogeneity(strategy, amount, ratios, multiplier):
    scaled_ratios = [r * multiplier for r in ratios]

    non_scaled = strategy(amount, ratios)
    scaled = strategy(amount, scaled_ratios)

    assert non_scaled == scaled


@pytest.mark.parametrize(
    "strategy",
    [
        hamilton,
    ],
)
@given(amount=amounts_st, ratios=strictly_increasing)
def test_hamilton_allocation_concordance(strategy, amount, ratios):

    result = strategy(amount, ratios)

    for i in range(len(result) - 1):
        assert result[i] <= result[i + 1]


@pytest.mark.parametrize("strategy", [hamilton, round_robin])
@given(
    amount=amounts_st,
    ratios=strictly_positive_ratios_st,
)
def test_allocation_balancedness(strategy, amount, ratios):
    length = len(ratios) - 1
    i = randint(1, length)
    ratios[i] = ratios[0]
    result = strategy(amount, ratios)
    assert abs(result[0] - result[i]) <= 1


@pytest.mark.parametrize("strategy", [hamilton, round_robin])
@given(
    amount=st.integers(min_value=1, max_value=100),
    ratios=ratios_st,
)
def test_allocation_exactness(strategy, amount, ratios):
    h = sum(ratios)
    h_multiple = amount * h
    result = strategy(h_multiple, ratios)
    assert result == [amount * r for r in ratios]
