from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Self


@dataclass(frozen=True, slots=True)
class ExchangeRateInfo:
    provider: str
    ratetype: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        core_keys = {"provider", "ratetype", "timestamp"}
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
        base = {
            "provider": self.provider,
            "ratetype": self.ratetype,
            "timestamp": self.timestamp.isoformat(),
        }
        return {**base, **self.metadata}

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> Self:
        core_keys = {"provider", "ratetype", "timestamp"}
        provider = data["provider"]
        ratetype = data["ratetype"]
        timestamp = datetime.fromisoformat(data["timestamp"])
        metadata = {k: data[k] for k in data.keys() - core_keys}

        return cls(
            provider=provider, ratetype=ratetype, timestamp=timestamp, metadata=metadata
        )
