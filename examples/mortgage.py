from decimal import Decimal

from pycents import Money

house_price = Money.from_major(400_000, "USD")
down_payment = Money.from_major(80_000, "USD")
annual_rate = Decimal("0.0655")  # 6.55%
terms = 360

principal_loan = house_price - down_payment


def monthly_payment(
    principal: Money, monthly_rate: Decimal, payments: int = 1
) -> Money:
    """Monthly payment for a fixed-rate amortizing mortgage"""
    exp = (1 + monthly_rate) ** payments
    coef = (monthly_rate * exp) / (exp - 1)
    return (principal * coef).round()


print(monthly_payment(principal_loan, annual_rate / 12))
