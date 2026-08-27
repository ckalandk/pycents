from collections.abc import Iterator

from pycents.exceptions import InvalidCurrencyError


class XcyMeta(type):
    """An enum like meta class to hold custom currency registry"""

    _registry: dict[str, Xcy] = {}

    def register(
        cls, code: str, name: str, minor_units: int, symbol: str = "", num_code: int = 0
    ) -> None:
        # TODO num_code should be unique for each currency,
        # check num_code availability before registering a custom currency
        code_upper = code.upper()
        cls._registry[code_upper] = Xcy(code_upper, name, minor_units, symbol, num_code)

    def __getattr__(cls, name: str) -> Xcy:
        if name in cls._registry:
            return cls._registry[name]
        raise AttributeError(f"Custom currency '{name}' not registered in Xcy.")

    def __getitem__(cls, name: str) -> Xcy:
        if name in cls._registry:
            return cls._registry[name]
        raise InvalidCurrencyError(f"Custom currency '{name}' not registered in Xcy.")

    def __contains__(cls, name: Xcy | str) -> bool:
        if isinstance(name, Xcy):
            xcy_code = name.ccy_code
        else:
            xcy_code = name
        return xcy_code.upper() in cls._registry

    def __iter__(cls) -> Iterator[str]:
        return iter(cls._registry.keys())


class Xcy(metaclass=XcyMeta):
    def __init__(
        self,
        code: str,
        name: str,
        minor_units: int,
        symbol: str = "",
        num_code: int = 0,
    ) -> None:
        self.ccy_code = code
        self.ccy_name = name
        self.minor_units = minor_units
        self.symbol = symbol
        self.ccy_num_code = num_code

    def __repr__(self) -> str:
        return f"Xcy(code='{self.ccy_code}')"
