import timeit
from decimal import Decimal

from pycents import RoundingMode
from pycents.rounding import as_decimal_rounding


def round(amount: Decimal, rounding: RoundingMode = RoundingMode.HALF_EVEN) -> int:
    rounded = amount.quantize(Decimal("1"), rounding=as_decimal_rounding(rounding))
    return int(rounded)


def round_check(
    amount: Decimal, rounding: RoundingMode = RoundingMode.HALF_EVEN
) -> int:
    if amount == amount.to_integral_value():
        return int(amount)
    rounded = amount.quantize(Decimal("1"), rounding=as_decimal_rounding(rounding))
    return int(rounded)


if __name__ == "__main__":
    amount = Decimal("123456")
    iterations = 1_000_000

    # Benchmark the round function
    round_time = timeit.timeit(
        "round(amount, RoundingMode.HALF_EVEN)", globals=globals(), number=iterations
    )
    print(f"round() time: {round_time:.4f} seconds")

    # Benchmark the round_check function
    round_check_time = timeit.timeit(
        "round_check(amount, RoundingMode.HALF_EVEN)",
        globals=globals(),
        number=iterations,
    )
    print(f"round_check() time: {round_check_time:.4f} seconds")
