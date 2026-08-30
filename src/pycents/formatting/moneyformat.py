from __future__ import annotations

import re
from dataclasses import replace

from pycents.exceptions import InvalidFormatSpecError

from ..protocols import MonetaryAmount
from .base_formatter import BaseFormatter
from .formatspec import DisplayOpts, FormatSpec
from .std_formatter import StdFormatter

_map_symbol: dict[str, DisplayOpts] = {"h": "hidden", "i": "iso", "n": "name"}


class MoneyFormatter:
    _FORMAT_SPEC_PATTERN = re.compile(
        r"^(?P<display>[hin])?"
        r"(?:\.(?P<precision>\d+))?"
        r"(?P<compact>c)?"
        r"(?P<accounting>a)?"
        r"(?P<group_sep>u)?"
        r"(?P<trim>~)?"
        r"(?P<rest>.*)$"
    )

    def __init__(
        self,
        formatter: BaseFormatter | None = None,
    ) -> None:
        self.backend_formatter = formatter if formatter else StdFormatter()

    def _parse(self, fmt_spec: str) -> tuple[FormatSpec | None, str]:
        match = self._FORMAT_SPEC_PATTERN.fullmatch(fmt_spec)

        assert match is not None

        if match["precision"] is not None and match["compact"] is None:
            raise InvalidFormatSpecError(
                "Formatting precision is locked to the currency's ISO standard."
                "Custom precision is only supported in compact mode (e.g., '.2c')."
            )
        if all(
            match[key] is None
            for key in [
                "display",
                "compact",
                "precision",
                "group_sep",
                "accounting",
                "trim",
            ]
        ):
            return None, match["rest"]

        return FormatSpec(
            compact=match["compact"] is not None,
            compact_precision=(
                int(match["precision"]) if match["precision"] is not None else None
            ),
            accounting=match["accounting"] is not None,
            ccy_display=(
                self.backend_formatter._default_spec.ccy_display
                if match["display"] is None
                else _map_symbol[match["display"]]
            ),
            group_separator=match["group_sep"] is None,
            trim_trailing_zeros=match["trim"] is not None,
        ), match["rest"]

    def format(self, money: MonetaryAmount, format_spec: str) -> str:
        spec, rest = self._parse(format_spec)
        if spec is None:
            spec = replace(self.backend_formatter._default_spec)

        if spec.compact and spec.compact_precision is None:
            spec.compact_precision = (
                self.backend_formatter._default_spec.compact_precision
            )

        str_money = self.backend_formatter.format(
            money.to_decimal(),
            money.currency,
            spec,
        )
        try:
            result = format(str_money, rest)
        except ValueError:
            raise InvalidFormatSpecError(
                f"Unknown format code '{rest}' for object of type 'Money'"
            ) from None
        return result
