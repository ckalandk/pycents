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
    setup_babel = """
from isomoney import Money, formatting
formatting.use_backend("babel")

mny = Money.from_major("29999.99", "USD")
"""
    setup_icu = """
from isomoney import Money, formatting
formatting.use_backend("icu")

mny = Money.from_major("29999.99", "USD")
"""
    iterations = 100_000

    print(f"Number of iterations: {iterations}")

    # Measure standard display
    babel_standard_display = timeit.timeit(
        "lambda : f'{mny}'", setup=setup_babel, number=iterations
    )
    icu_standard_display = timeit.timeit(
        "lambda : f'{mny}'", setup=setup_icu, number=iterations
    )

    print("--- standard formatting ---")
    print(f"Babel:   {babel_standard_display:.4f} seconds")
    print(f"Icu: {icu_standard_display:.4f} seconds")
    print(
        f"Icu vs babel:{(babel_standard_display / icu_standard_display):.2f}x faster\n"
    )

    babel_iso_display = timeit.timeit(
        "lambda : f'{mny:i}'", setup=setup_babel, number=iterations
    )
    icu_iso_display = timeit.timeit(
        "lambda : f'{mny:i}'", setup=setup_icu, number=iterations
    )
    print("--- iso formatting ---")
    print(f"Babel:   {babel_iso_display:.4f} seconds")
    print(f"Icu: {icu_iso_display:.4f} seconds")
    print(f"Icu vs babel:     {(babel_iso_display / icu_iso_display):.2f}x faster\n")


if __name__ == "__main__":
    run_benchmark()
