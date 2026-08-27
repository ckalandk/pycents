import timeit
from decimal import Decimal

from pycents import Money
from pycents.money import MoneyLike, UnroundedMoney


def manual_loop_sum(iterable):
    """Relies entirely on the objects' __add__ methods."""
    iterator = iter(iterable)
    total = next(iterator)

    for item in iterator:
        total = total + item

    return total


if __name__ == "__main__":
    print("Generating test datas...")
    pure_money_list: list[MoneyLike] = [
        Money.from_major(10, "USD") for _ in range(100_000)
    ]

    mixed_list = pure_money_list[:]
    ccy = mixed_list[0]._currency
    mixed_list[50_000] = UnroundedMoney.from_decimal(Decimal("20.5"), ccy.ccy_code)
    mixed_list[75_000] = UnroundedMoney.from_decimal(Decimal("250.8"), ccy.ccy_code)

    runs = 10

    # BENCHMARK 1:
    time_bulk_pure = timeit.timeit(lambda: Money.sum(pure_money_list), number=runs)
    time_manual_pure = timeit.timeit(
        lambda: manual_loop_sum(pure_money_list), number=runs
    )

    print("BENCHMARK 1: Pure Money (100,000 ints)")
    print(f"Optimized Money.sum: {time_bulk_pure:.4f} seconds")
    print(f"Manual Object __add__:    {time_manual_pure:.4f} seconds")
    print(f">>> Bulk sum is {time_manual_pure / time_bulk_pure:.1f}x faster.\n")

    # BENCHMARK 2: Mixed
    time_bulk_mixed = timeit.timeit(lambda: Money.sum(mixed_list), number=runs)
    time_manual_mixed = timeit.timeit(lambda: manual_loop_sum(mixed_list), number=runs)

    print("BENCHMARK 2: Mixed (Money + Unrounded)")
    print(f"Optimized Money.bulk_sum: {time_bulk_mixed:.4f} seconds")
    print(f"Manual Object __add__:    {time_manual_mixed:.4f} seconds")
    print(f">>> Bulk sum is {time_manual_mixed / time_bulk_mixed:.1f}x faster.\n")
