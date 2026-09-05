from pycents.currency import Currency
from pycents.money import Money, UnroundedMoney

from .provider import ExchangeRateProvider

__all__ = ["CcyConverter"]


class CcyConverter:
    def __init__(self, provider: ExchangeRateProvider):
        self.exchange_provider = provider

    def convert(self, amount: Money, *, term: Currency | str) -> UnroundedMoney:
        if isinstance(term, str):
            term = Currency.from_code(term)
        if amount.currency == term:
            return UnroundedMoney(amount)
        rate = self.exchange_provider.get_exchange_rate(amount.currency, term)
        return amount * rate.factor
