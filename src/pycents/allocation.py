from collections.abc import Callable, Sequence

from .money import Money

__all__ = ["allocate", "allocate_base", "hamilton", "round_robin"]

type Apportionment = Callable[[int, Sequence[int]], list[int]]


def _validate_allocation_args(amount: int, ratios: Sequence[int]) -> None:
    """Validates the arguments for money allocation operations.

    Args:
        amount: The monetary amount in minor units to allocate.
        ratios: A sequence of integer ratios representing the desired distribution.

    Raises:
        ValueError: If the amount is negative, if any ratio is negative,
        or if the sum of all ratios is zero.
    """
    if amount < 0:
        raise ValueError("Expected positive money")
    total = 0
    for ratio in ratios:
        if ratio < 0:
            raise ValueError(f"Ratios cannot contain negative values: {ratio}")
        total += ratio
    if total == 0:
        raise ValueError("Sum of ratios must be greater than zero")


def hamilton(amount: int, ratios: Sequence[int]) -> list[int]:
    """Allocates an integer amount according to given ratios using the Hamilton
       apportionment strategy.

    Args:
        amount: The total amount to be divided.
        ratios: The proportions to use for the division.

    Returns:
        list[int]: The allocated integer shares, summing exactly to the original amount.
    """
    total = sum(ratios)
    leftover = amount
    shares_info = []
    for i, ratio in enumerate(ratios):
        base_share = (amount * ratio) // total
        remainder = (amount * ratio) % total
        shares_info.append((i, base_share, remainder))
        leftover -= base_share

    results = [share[1] for share in shares_info]
    shares_info.sort(key=lambda x: x[2], reverse=True)
    assert leftover < len(ratios)
    idx = 0
    while leftover > 0:
        index = shares_info[idx][0]
        if ratios[index] != 0:
            results[index] += 1
            leftover -= 1
        idx += 1
    return results


def round_robin(amount: int, ratios: Sequence[int]) -> list[int]:
    """Allocates an integer amount according to given ratios using a
    sequential apportionment strategy.

    First we calculate the base share for each ratio, the leftover units are then
    distributed sequentially (round-robin) starting from the first ratio until the
    remainder is exhausted.

    Args:
        amount: The total amount to be divided.
        ratios: The proportions to use for the division.

    Returns:
        list[int]: The allocated integer shares, summing exactly to the original amount.
    """
    total = sum(ratios)
    results = []
    leftover = amount
    for ratio in ratios:
        share = (amount * ratio) // total
        leftover -= share
        results.append(share)

    assert leftover < len(ratios)
    idx = 0
    while leftover > 0:
        if ratios[idx] != 0:
            results[idx] += 1
            leftover -= 1
        idx += 1
    return results


def allocate_base(
    money: Money,
    ratios: Sequence[int],
) -> tuple[list[Money], Money]:
    """Distributes money according to ratios without resolving the remainder.

    Calculates the exact base shares based on the given ratios using floor division.
    Any unallocated leftover amount is returned separately
    rather than distributed among the shares.

    Args:
        money: The money instance to allocate.
        ratios: The proportions to use for the division.

    Returns:
        tuple[list[Money], Money]: A tuple containing a list of the base allocated
        Money instances and a single Money instance representing the unallocated
        remainder.

    Raises:
        ValueError: If validation of the money amount or ratios fails.
    """
    _validate_allocation_args(money.as_minors, ratios)
    total_ratio = sum(ratios)
    remainder = money.as_minors
    result = []
    for ratio in ratios:
        share = (money.as_minors * ratio) // total_ratio
        result.append(Money(share, money._currency))
        remainder -= share
    return result, Money(remainder, money._currency)


def allocate(
    money: Money,
    ratios: Sequence[int],
    strategy: Apportionment = hamilton,
) -> list[Money]:
    """Allocates money according to given ratios and apportionment strategy.

    Divides a money instance exactly so that no minor units are lost or created.
    The leftover unallocated pennies are distributed among the shares according
    to the chosen apportionment strategy.

    Args:
        money: The money instance to allocate.
        ratios: The proportions to use for the division.
        strategy (Apportionment, optional): The strategy used to distribute
        the remainder. Defaults to the Hamilton (Largest Remainder) method.

    Returns:
        list[Money]: A list of exactly allocated Money instances that sum
        to the original amount.

    Raises:
        ValueError: If validation of the money amount or ratios fails.
    """
    _validate_allocation_args(money.as_minors, ratios)
    shares = strategy(money.as_minors, ratios)
    return [Money(amount, money._currency) for amount in shares]
