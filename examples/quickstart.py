from decimal import Decimal

from pycents import Ccy, Money

# Constructing money amounts.
price = Money.from_major(Decimal("29.99"), "USD")
bonus = Money.from_major("5.00", Ccy.USD)
tax = Money.from_major(Decimal("2.00"), "USD")

# Arithmetic operations.
total = price + bonus - tax

# Comparisons.
assert price < total
assert price != total

# Accessing the internal representation (minor units).
print(total.as_minors)

# Converting back to major units.
print(total.as_majors)

# Currency information.
print(total._currency.ccy_code)
print(total._currency.minor_units)
print("Currency name:", total._currency.ccy_name)

# String representations.
print(total)
print(repr(total))
print(f"{total:h}")
