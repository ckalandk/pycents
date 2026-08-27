# exceptions.py


class PyCentsError(Exception):
    """Base exception for all pycents errors."""


class InvalidFormatSpecError(PyCentsError):
    """Raised when a money format specification is invalid."""


class CurrencyMismatchError(PyCentsError):
    """Raised when operations involve different currencies."""


class BackendConfigurationError(PyCentsError):
    """Raised when a configuration is not supported by a backend formatter."""


class InvalidCurrencyError(PyCentsError):
    """Raised when a custom currency is not registered"""
