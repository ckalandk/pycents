from collections.abc import Hashable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from types import MappingProxyType
from typing import Any, NotRequired, Self, TypedDict


class ExchangeRateInfoData(TypedDict):
    provider: str
    ratetype: str
    asof: str
    metadata: NotRequired[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class ExchangeRateInfo:
    """Describes the provenance and additional information of an exchange rate.

    Attributes:
        provider: Name of the exchange-rate provider.
        ratetype: Type or classification of the rate,
            such as ``"mid"`` or ``"reference"``.
        asof: Date or timestamp to which the exchange rate applies.
            Defaults to the current UTC time.
        metadata: Additional rate-specific information.
            Keys ``"provider"``, ``"ratetype"``, and ``"asof"`` are reserved and
            cannot be used in metadata. Metadata is exposed both through the
            ``metadata`` mapping and as attributes on the instance.
            For example, a metadata entry ``{"source_url": "www.ecb.eu"}`` can be
            accessed as ``info.source_url``.
    """

    provider: str
    ratetype: str
    asof: date | datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, Hashable] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(self.metadata))

    def as_dict(self) -> ExchangeRateInfoData:
        """Serialize the exchange-rate information to a dictionary.

        Returns: A dictionary containing the provider, rate type, ISO-formatted
            timestamp, and metadata entries.
        """
        base: ExchangeRateInfoData = {
            "provider": self.provider,
            "ratetype": self.ratetype,
            "asof": self.asof.isoformat(),
        }

        if self.metadata:
            base["metadata"] = dict(self.metadata)

        return base

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        raw = data["asof"]
        asof = datetime.fromisoformat(raw) if "T" in raw else date.fromisoformat(raw)
        return cls(
            provider=data["provider"],
            ratetype=data["ratetype"],
            asof=asof,
            metadata=data.get("metadata", {}),
        )
