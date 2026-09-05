from dataclasses import dataclass


@dataclass
class ExchangeRateContext:
    """This empty for now, but it can be used to provide additional
    context for exchange rate fetching in the future.
    Users could still subclass this class to provide additional context
    for exchange rate calculations if needed.
    """

    pass
