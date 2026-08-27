from . import allocation, formatting
from .currency import Ccy, Currency, Xcy
from .exceptions import (
    BackendConfigurationError,
    CurrencyMismatchError,
    InvalidFormatSpecError,
    PyCentsError,
)
from .money import Money, UnroundedMoney
from .rounding import RoundingMode

__version__ = "1.1.0"

Xcy.register("TST", "Test Coin", 2, "¤", 1000)
Xcy.register("BTC", "Bitcoin", 8, "₿", 1001)
Xcy.register("ETH", "Ethereum", 18, "Ξ", 1002)
Xcy.register("USDT", "Tether", 6, "₮", 1003)
Xcy.register("USDC", "USD Coin", 6, "$", 1004)
Xcy.register("SOL", "Solana", 9, "◎", 1005)
Xcy.register("XRP", "XRP", 6, "✕", 1006)
Xcy.register("DOGE", "Degocoin", 8, "Ð", 1007)

__all__ = [
    # Core domain modeles
    "Money",
    "UnroundedMoney",
    "Currency",
    "Ccy",
    "Xcy",
    "RoundingMode",
    # Submodules
    "allocation",
    "formatting",
    # Excpetions
    "PyCentsError",
    "InvalidFormatSpecError",
    "CurrencyMismatchError",
    "BackendConfigurationError",
]
