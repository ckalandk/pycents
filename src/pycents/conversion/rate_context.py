from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from types import MappingProxyType
from typing import Any, Self


@dataclass(frozen=True, slots=True)
class ExchangeRateInfo:
    """Describes the provenance and additional information of an exchange rate.

    Attributes:
        provider: Name of the exchange-rate provider.
        ratetype: Type or classification of the rate,
            such as ``"mid"`` or ``"reference"``.
        asof: Date or timestamp to which the exchange rate applies.
            Defaults to the current UTC time.
        metadata: Additional provider-specific information.
            Keys ``"provider"``, ``"ratetype"``, and ``"asof"`` are reserved and
            cannot be used in metadata. Metadata is exposed both through the
            ``metadata`` mapping and as attributes on the instance.
            For example, a metadata entry ``{"source": "ECB"}`` can be accessed as
            ``info.source``.
    """

    provider: str
    ratetype: str
    asof: date | datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        core_keys = {"provider", "ratetype", "asof"}
        collisions = core_keys & self.metadata.keys()
        if collisions:
            bad_keys = ", ".join(sorted(collisions))
            raise ValueError(f"Metadata cannot contain reserved keys: {bad_keys}")
        if isinstance(self.metadata, dict):
            object.__setattr__(self, "metadata", MappingProxyType(self.metadata))

    def __getattr__(self, name: str) -> Any:
        if name in self.metadata:
            return self.metadata[name]
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def as_dict(self) -> dict[str, str]:
        """Serialize the exchange-rate information to a dictionary.

        Returns: A dictionary containing the provider, rate type, ISO-formatted
            timestamp, and metadata entries.
        """
        base = {
            "provider": self.provider,
            "ratetype": self.ratetype,
            "timestamp": self.asof.isoformat(),
        }
        return {**base, **self.metadata}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        core_keys = {"provider", "ratetype", "timestamp"}
        provider = data["provider"]
        ratetype = data["ratetype"]
        timestamp = datetime.fromisoformat(data["timestamp"])
        metadata = {k: data[k] for k in data.keys() - core_keys}

        return cls(
            provider=provider, ratetype=ratetype, asof=timestamp, metadata=metadata
        )
