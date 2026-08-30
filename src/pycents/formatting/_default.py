"""
Default formatting configuration.

This module provides the global formatter used by Money.__format__ and
implements an API heavily inspired by Python's logging module.

No, I didn't honor the tradition by naming the formatter accessor `getFormatter()`.
PEP 8 won.:-)
"""

import contextvars
from collections.abc import Callable, Generator
from contextlib import contextmanager
from copy import deepcopy
from typing import Any, TypeVar

from pycents.rounding import RoundingMode

from ..protocols import MonetaryAmount
from .base_formatter import BaseFormatter
from .formatspec import DisplayOpts
from .moneyformat import MoneyFormatter
from .std_formatter import StdFormatter


class _FormatContext:
    def __init__(
        self,
        backend_formatter: BaseFormatter,
        locale: str | None = None,
        numbering_system: str | None = None,
    ) -> None:
        self.mny_fmt = MoneyFormatter(backend_formatter)
        if locale is not None:
            self.mny_fmt.backend_formatter.locale = locale
        if numbering_system is not None:
            self.mny_fmt.backend_formatter.numbering_system = numbering_system

    @property
    def backend_formatter(self) -> BaseFormatter:
        return self.mny_fmt.backend_formatter

    @property
    def compact(self) -> bool:
        return self.backend_formatter._default_spec.compact

    @compact.setter
    def compact(self, value: bool) -> None:
        self.backend_formatter._default_spec.compact = value

    @property
    def compact_prec(self) -> int:
        result = self.backend_formatter._default_spec.compact_precision
        assert result
        return result

    @compact_prec.setter
    def compact_prec(self, value: int) -> None:
        self.backend_formatter._default_spec.compact_precision = value

    @property
    def accounting(self) -> bool:
        return self.backend_formatter._default_spec.accounting

    @accounting.setter
    def accounting(self, value: bool) -> None:
        self.backend_formatter._default_spec.accounting = value

    @property
    def display(self) -> str:
        return self.backend_formatter._default_spec.ccy_display

    @display.setter
    def display(self, value: DisplayOpts) -> None:
        self.backend_formatter._default_spec.ccy_display = value

    @property
    def group_separator(self) -> bool:
        return self.backend_formatter._default_spec.group_separator

    @group_separator.setter
    def group_separator(self, value: bool) -> None:
        self.backend_formatter._default_spec.group_separator = value

    @property
    def rounding(self) -> RoundingMode:
        return self.backend_formatter._rounding

    @rounding.setter
    def rounding(self, value: RoundingMode) -> None:
        self.backend_formatter._rounding = value


_active_context: contextvars.ContextVar[_FormatContext | None] = contextvars.ContextVar(
    "active_context", default=None
)


@contextmanager
def local_format(
    locale: str | None = None, numbering_system: str | None = None
) -> Generator[_FormatContext]:
    local_backend = deepcopy(_default.backend_formatter)

    ctx = _FormatContext(local_backend, locale, numbering_system)
    token = _active_context.set(ctx)
    try:
        yield ctx
    finally:
        _active_context.reset(token)


def _create_icu_formatter() -> BaseFormatter:  # pragma: no cover
    """Creates a PyICU-based currency formatter.

    Returns:
        BaseFormatter: An instance of the ICU formatter.

    Raises:
        ImportError: If the 'PyICU' package is not installed in the environment.
    """
    try:
        from .pyicu import IcuFormatter

        return IcuFormatter()
    except ImportError:
        raise ImportError("The 'icu' backend requires the PyICU package.") from None


def _create_babel_formatter() -> BaseFormatter:  # pragma: no cover
    """Creates a Babel-based currency formatter.

    Returns:
        BaseFormatter: An instance of the Babel formatter.

    Raises:
        ImportError: If the 'babel' package is not installed in the environment.
    """
    try:
        from .babel import BabelFormatter

        return BabelFormatter()
    except ImportError:
        raise ImportError("The 'babel' backend requires the babel package.") from None


_BACKENDS = {
    "std": lambda: StdFormatter(),
    "icu": _create_icu_formatter,
    "babel": _create_babel_formatter,
}

_default = MoneyFormatter(formatter=StdFormatter())


def format(money: MonetaryAmount, format_spec: str) -> str:
    """Formats a money-like object using the globally configured formatter.

    Args:
        money: The monetary value to format.
        format_spec: The format specification string.

    Returns:
        str: The formatted monetary string.
    """
    ctx = _active_context.get()

    if ctx is not None:
        return ctx.mny_fmt.format(money, format_spec)

    return _default.format(money, format_spec)


def basicConfig(
    *,
    locale: str | None = None,
    numbering_system: str = "latn",
) -> None:
    """Configures the global default formatter.

    This function sets up the root formatting preferences for all Money objects
    that rely on default formatting.

    Args:
        locale: The locale string to apply to the active backend
            (e.g., "en_US", "fr_FR"). Defaults to None (keeps current locale).
        rounding (RoundingMode, optional): The rounding mode to use when formatting
            money strings in compact format. Defaults to RoundingMode.HALF_EVEN.
    """
    if locale is not None:
        _default.backend_formatter.locale = locale
    _default.backend_formatter.numbering_system = numbering_system


def get_formatter() -> BaseFormatter:
    """Retrieves the globally active backend formatter instance.

    Returns:
        BaseFormatter: The current backend formatter driving the formatting logic.
    """
    return _default.backend_formatter


def available_backends() -> list[str]:
    """Lists the names of all registered formatter backends.

    Returns:
        list[str]: An alphabetically sorted list of backend names.
    """
    return list(sorted(_BACKENDS))


def current_backend() -> str:
    """Retrieves the name of the currently active formatting backend.

    Returns:
        str: The name of the backend class (e.g., 'std', 'icu'...).
    """
    return _default.backend_formatter.__class__.__name__


def use_backend(backend_formatter: BaseFormatter | str) -> None:
    """Sets the global formatting backend.

    Changes the engine used to format monetary objects globally. You can pass either
    the string name of a registered backend or a custom instance of a BaseFormatter.

    Args:
        backend_formatter (BaseFormatter | str): The registered name of the backend
            (e.g., 'icu', 'std') or a direct BaseFormatter instance to use.

    Raises:
        ValueError: If a string is provided but it doesn't match any registered backend.
        TypeError: If a non-string is provided that is not a subclass of BaseFormatter.
    """
    if isinstance(backend_formatter, str):
        try:
            _default.backend_formatter = _BACKENDS[backend_formatter]()
        except KeyError as exc:
            raise ValueError(
                f"Unknown formatter backend {backend_formatter!r}. "
                f"Available backends: {', '.join(available_backends())}"
            ) from exc
        return
    if not isinstance(backend_formatter, BaseFormatter):
        raise TypeError("backend_formatter must be a BaseFormatter instance.")

    _default.backend_formatter = backend_formatter


def register_backend(name: str, factory_function: Callable[[], BaseFormatter]) -> None:
    """Registers a new formatting backend factory under a given name.

    Args:
        name: The unique string identifier for the backend.
        factory_function: A zero-argument callable
            that produces a new instance of a BaseFormatter.

    Raises:
        ValueError: If the provided factory_function is not callable
        or the name is already registered.
    """
    if not callable(factory_function):
        raise ValueError("The factory_function must be callable.")
    if name in _BACKENDS:
        raise ValueError(f"A backend named '{name}' is already registered.")
    _BACKENDS[name] = factory_function


T = TypeVar("T", bound=BaseFormatter)


def register(name: str | None = None, **kwargs: Any) -> Callable[[type[T]], type[T]]:
    """Decorator to register a custom BaseFormatter class as a formatting backend.

    This decorator automatically adds the target class to the list of available
    backends. The factory function created will instantiate the class using any
    keyword arguments provided here.

    Args:
        name: The name to register the backend under.
            If not provided, defaults to the lowercase name of the class.
        **kwargs: Additional keyword arguments to pass to the class constructor
            when the backend is instantiated.

    Returns:
        Callable[[type[T]], type[T]]: The class decorator.

    Example:
        @register(name="custom", locale="en_GB")
        class CustomFormatter(BaseFormatter):
            ...
    """

    def inner_decorator(cls: type[T]) -> type[T]:
        _name = name if name is not None else cls.__name__.lower()
        register_backend(_name, lambda: cls(**kwargs))
        return cls

    return inner_decorator
