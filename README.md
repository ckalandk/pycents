<div align="center">
<img src="https://raw.githubusercontent.com/ckalandk/pycents/main/assets/logo-light.svg" alt="pycents logo"/>
<br/>
<br/>

[![Tests](https://github.com/ckalandk/pycents/actions/workflows/tests.yml/badge.svg)](https://github.com/ckalandk/pycents/actions/workflows/tests.yml)
![Python Version](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%20%20%7C%203.14-blue)
![Linter: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](https://mypy-lang.org/)
[![codecov](https://codecov.io/gh/ckalandk/pycents/graph/badge.svg?token=vOH2wc2alW)](https://codecov.io/gh/ckalandk/pycents)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

<h1>PyCents</h1>
</div>

**pycents** is a strongly typed Python library for representing and manipulating monetary
values with ISO 4217 and custom currencies, explicit rounding semantics and rich formatting options.

* **ISO 4217 & custom currencies**: built-in support for ISO 4217 currencies with standardized codes and minor-unit definitions. Custom currencies such as cryptocurrencies can be
registered at runtime. Some **popular cryptocurrencies are pre-registered and ready to use**.

* **Money uses integer minor units for exact monetary representation.**

* **Explicit rounding** — PyCents use a dual-type architecture for exact and high-precision operations:
  * `Money` The core immutable type that stores exact monetary values as integer minor units (e.g., cents).
  * `UnroundedMoney`: A high-precision type designed for complex intermediate calculations without premature rounding.
  * **Seamless Integration**: Both types work together fluidly in arithmetic. Calling `.round()` on an `UnroundedMoney` instance explicitly converts it back into standard `Money`.

## Features

* 100% Test Coverage & Property-Based Testing: Fully covered and rigorously
  verified using **Hypothesis** to guarantee mathematical invariants.
* ISO 4217 currency definitions
* Custom currency support with runtime registration
* Pre-registered popular cryptocurrencies
* Immutable `Money` type
* Precise decimal arithmetic
* Explicit rounding semantics.
* Locale-aware currency formatting
* Pluggable formatting backends
* Custom format specification

## Example

```python
from decimal import Decimal

from pycents import Money, UnroundedMoney, formatting, allocation as alloc

# Use a locale-aware formatting backend
formatting.use_backend("babel")  # Other options are: 'std'(default) and 'icu'

rent = Money.from_major(121_555, "USD")
# the '.2c' format field is for displaying in compact notation
# while retaining 2 decimals
print(f"{rent:.2c}")  # Output: $121.56K

# Apply an 8.875% municipal property tax
tax_rate = Decimal("0.08875")

# `tax` is not a Money instance!
tax = rent * tax_rate
assert isinstance(tax, UnroundedMoney)

# At the end the arithmetic pipeling, call round to get a `Money` instance
total = (rent + tax).round()

# allocate the rent among three clients according to a given ratios
shares = alloc.allocate(total, [1000, 2000, 3000])
result = ", ".join(f"{share:.2c}" for share in shares)
print("Allocated Shares:", f"[{result}]")
# Output: Allocated Shares: [$22.06K, $44.11K, $66.17K]
```

## Documentation

Documentation and API reference are available at [pycents.readthedocs.io](https://pycents.readthedocs.io/). This is still a work in progress, some guide are complete
(Quickstart, formatting and allocation) but still need to be polished.

## License

`pycents` is distributed under the MIT License.
See the [LICENSE](./LICENSE) file for details.
