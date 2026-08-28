from dataclasses import dataclass
from typing import Literal

DisplayOpts = Literal["hidden", "symbol", "iso", "name"]


@dataclass(slots=True)
class FormatSpec:
    ccy_display: DisplayOpts = "symbol"

    compact: bool = False
    compact_precision: int | None = 1
    accounting: bool = False
    group_separator: bool = True
    trim_trailing_zeros: bool = False

    def update(
        self,
        display: DisplayOpts | None = None,
        compact: bool | None = None,
        compact_precision: int | None = None,
        accounting: bool | None = None,
        group_separator: bool | None = None,
        trim_trailing_zeros: bool | None = None,
    ) -> None:
        """Safely updates attributes only if a value is provided."""
        if compact is not None:
            self.compact = compact
        if compact_precision is not None:
            self.compact_precision = compact_precision
        if accounting is not None:
            self.accounting = accounting
        if display is not None:
            self.ccy_display = display
        if group_separator is not None:
            self.group_separator = group_separator
        if trim_trailing_zeros is not None:
            self.trim_trailing_zeros = trim_trailing_zeros
