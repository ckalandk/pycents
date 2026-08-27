from decimal import Decimal

from pycents import Money, RoundingMode, UnroundedMoney

items = [
    {"name": "item1", "price": "249.99", "discount": "0.15"},
    {"name": "item2", "price": "119.50", "discount": "0.0"},
    {"name": "item3", "price": "389.00", "discount": "0.10"},
    {"name": "item4", "price": "12.99", "discount": "0.0"},
    {"name": "item5", "price": "89.99", "discount": "0.20"},
    {"name": "item6", "price": "199.95", "discount": "0.05"},
    {"name": "item7", "price": "149.00", "discount": "0.0"},
    {"name": "item8", "price": "24.50", "discount": "0.0"},
    {"name": "item9", "price": "34.99", "discount": "0.125"},
    {"name": "item10", "price": "59.99", "discount": "0.0"},
]

prices = [Money.from_major(item["price"], "USD") for item in items]
prices_after_discounts = [
    mny - mny * Decimal(item["discount"])
    for mny, item in zip(prices, items, strict=True)
]

# `total` is either a `Money` or a `UnroundedMoney` instance
# You can, either supply a rounding mode via the keyword argument `rounding`
# to get a Money instance

total = Money.sum(prices_after_discounts, rounding=RoundingMode.UP)
assert isinstance(total, Money)

print(total)  # Output: USD 1221.14
# If you don't provide a rounding mode the result will be an
# `UnroundedMoney` instance if there is at least one `UnroundedMoney`
# instance in the provided list, or a `Money` object otherwise

total = Money.sum(prices_after_discounts)
assert isinstance(total, UnroundedMoney)

# At this stage you can carry on with any remainding calculation
# or round the result to get a `Money` instance
final_price = total.round()
print(final_price)  # Output: USD 1221.14
