import decimal
import timeit
from decimal import localcontext


class NoContextSwitch:
    def __init__(self, value):
        self.value = value

    def __add__(self, other):
        return NoContextSwitch(self.value + other.value)

    def __mul__(self, other):
        return NoContextSwitch(self.value * other.value)


class WithContextSwitch:
    def __init__(self, value):
        self.value = value

    def __add__(self, other):
        with localcontext() as ctx:
            ctx.traps[decimal.Inexact] = True
            result = self.value + other.value
        return WithContextSwitch(result)

    def __mul__(self, other):
        with localcontext() as ctx:
            ctx.traps[decimal.Inexact] = True
            result = self.value * other.value
        return WithContextSwitch(result)


def run_benchmark():
    # Setup variables for the timeit module
    setup_code = """
from __main__ import NoContextSwitch, WithContextSwitch, Decimal
a_no = NoContextSwitch(Decimal('19.12'))
b_no = NoContextSwitch(Decimal('15.12'))

a_with = WithContextSwitch(Decimal('19.12'))
b_with = WithContextSwitch(Decimal('15.12'))
"""

    iterations = 100_000

    print(f"Number of iterations: {iterations}")

    # Measure Addition
    add_no_time = timeit.timeit("a_no + b_no", setup=setup_code, number=iterations)
    add_with_time = timeit.timeit(
        "a_with + b_with", setup=setup_code, number=iterations
    )

    print("--- Addition ---")
    print(f"No Context:   {add_no_time:.4f} seconds")
    print(f"With Context: {add_with_time:.4f} seconds")
    print(f"Overhead:     {(add_with_time / add_no_time):.2f}x slower\n")

    # Measure Multiplication
    mul_no_time = timeit.timeit("a_no * b_no", setup=setup_code, number=iterations)
    mul_with_time = timeit.timeit(
        "a_with * b_with", setup=setup_code, number=iterations
    )

    print("--- Multiplication ---")
    print(f"No Context:   {mul_no_time:.4f} seconds")
    print(f"With Context: {mul_with_time:.4f} seconds")
    print(f"Overhead:     {(mul_with_time / mul_no_time):.2f}x slower\n")


if __name__ == "__main__":
    run_benchmark()
