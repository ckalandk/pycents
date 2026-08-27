import timeit


# Mock Currency for speed
class MockCurrency:
    __slots__ = ("ccy_code",)

    def __init__(self, code):
        self.ccy_code = code


USD = MockCurrency("USD")


# OPTION A: Cache in zero() classmethod only
class MoneyA:
    __slots__ = ("_amount", "_currency")
    _zero_cache = {}

    def __init__(self, amount: int, currency: MockCurrency):
        self._amount = amount
        self._currency = currency

    @classmethod
    def zero(cls, currency: MockCurrency):
        code = currency.ccy_code
        if code not in cls._zero_cache:
            cls._zero_cache[code] = cls(0, currency)
        return cls._zero_cache[code]

    def __sub__(self, other):
        return MoneyA(self._amount - other._amount, self._currency)


# OPTION B: Cache in __new__, NO __init__
class MoneyB:
    __slots__ = ("_amount", "_currency")
    _zero_cache = {}

    def __new__(cls, amount: int, currency: MockCurrency):
        if amount == 0:
            code = currency.ccy_code
            if code not in cls._zero_cache:
                instance = super().__new__(cls)
                object.__setattr__(instance, "_amount", 0)
                object.__setattr__(instance, "_currency", currency)
                cls._zero_cache[code] = instance
            return cls._zero_cache[code]

        instance = super().__new__(cls)
        object.__setattr__(instance, "_amount", amount)
        object.__setattr__(instance, "_currency", currency)
        return instance

    @classmethod
    def zero(cls, currency: MockCurrency):
        return cls(0, currency)

    def __sub__(self, other):
        return MoneyB(self._amount - other._amount, self._currency)


# THE BENCHMARK
if __name__ == "__main__":
    # Prime the caches
    MoneyA.zero(USD)
    MoneyB.zero(USD)

    # Setup vars for subtraction test
    mA1 = MoneyA(10, USD)
    mA2 = MoneyA(10, USD)
    mB1 = MoneyB(10, USD)
    mB2 = MoneyB(10, USD)

    runs = 1_000_000

    print(f"Running benchmarks ({runs} iterations each)...\n")

    # TEST 1: Explicit Zero
    t_zero_A = timeit.timeit(lambda: MoneyA.zero(USD), number=runs)
    t_zero_B = timeit.timeit(lambda: MoneyB.zero(USD), number=runs)
    print("--- Scenario 1: Explicit Money.zero() ---")
    print(f"Option A (Cache in zero):  {t_zero_A:.4f}s")
    print(f"Option B (Cache in __new__): {t_zero_B:.4f}s\n")

    # TEST 2: Computed Zero (Math)
    t_sub_A = timeit.timeit(lambda: mA1 - mA2, number=runs)
    t_sub_B = timeit.timeit(lambda: mB1 - mB2, number=runs)
    print("--- Scenario 2: Computed Zero (mny - mny) ---")
    print(f"Option A (Cache in zero):   {t_sub_A:.4f}s")
    print(f"Option B (Cache in __new__):     {t_sub_B:.4f}s\n")

    # TEST 3: Normal Instantiation
    t_norm_A = timeit.timeit(lambda: MoneyA(100, USD), number=runs)
    t_norm_B = timeit.timeit(lambda: MoneyB(100, USD), number=runs)
    print("--- Scenario 3: Normal Instantiation (Money(100)) ---")
    print(f"Option A (__init__):       {t_norm_A:.4f}s")
    print(f"Option B (__new__):        {t_norm_B:.4f}s\n")
