from datetime import UTC, datetime
from types import MappingProxyType

import pytest

from pycents.conversion import ExchangeRateInfo


class TestExchangeRateInfo:
    def test_initialization_and_defaults(self):
        ctx = ExchangeRateInfo(provider="ECB", ratetype="SPOT")

        assert ctx.provider == "ECB"
        assert ctx.ratetype == "SPOT"
        assert isinstance(ctx.timestamp, datetime)
        assert ctx.timestamp.tzinfo is UTC
        assert isinstance(ctx.metadata, MappingProxyType)
        assert len(ctx.metadata) == 0

    def test_full_initialization(self):
        dt = datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)
        ctx = ExchangeRateInfo(
            provider="ECB",
            ratetype="SPOT",
            timestamp=dt,
            metadata={"batch_id": "12345", "feed": "XML"},
        )

        assert ctx.timestamp == dt
        assert dict(ctx.metadata) == {"batch_id": "12345", "feed": "XML"}
        assert isinstance(ctx.metadata, MappingProxyType)

    def test_as_dict_serializes_correctly(self):
        dt = datetime(2026, 9, 8, 15, 30, 0, tzinfo=UTC)
        ctx = ExchangeRateInfo(
            provider="Bloomberg",
            ratetype="IMMEDIATE",
            timestamp=dt,
            metadata={"latency_ms": "42", "node": "eu-west-1"},
        )

        expected = {
            "provider": "Bloomberg",
            "ratetype": "IMMEDIATE",
            "timestamp": "2026-09-08T15:30:00+00:00",
            "latency_ms": "42",
            "node": "eu-west-1",
        }
        assert ctx.as_dict() == expected

    def test_as_dict_without_metadata(self):
        dt = datetime(2026, 9, 8, 15, 30, 0, tzinfo=UTC)
        ctx = ExchangeRateInfo(provider="Bloomberg", ratetype="IMMEDIATE", timestamp=dt)

        expected = {
            "provider": "Bloomberg",
            "ratetype": "IMMEDIATE",
            "timestamp": "2026-09-08T15:30:00+00:00",
        }
        assert ctx.as_dict() == expected

    def test_from_dict_deserializes_correctly(self):
        data = {
            "provider": "Reuters",
            "ratetype": "EOD",
            "timestamp": "2026-09-08T23:59:59+00:00",
            "batch_id": "999",
            "status": "verified",
        }

        ctx = ExchangeRateInfo.from_dict(data)

        assert ctx.provider == "Reuters"
        assert ctx.ratetype == "EOD"
        assert ctx.timestamp == datetime(2026, 9, 8, 23, 59, 59, tzinfo=UTC)
        assert dict(ctx.metadata) == {"batch_id": "999", "status": "verified"}
        assert isinstance(ctx.metadata, MappingProxyType)

    def test_from_dict_missing_core_fields_raises_key_error(self):
        data = {
            "provider": "Reuters",
            # missing ratetype and timestamp
            "batch_id": "999",
        }

        with pytest.raises(KeyError):
            ExchangeRateInfo.from_dict(data)

    def test_from_dict_invalid_timestamp_raises_value_error(self):
        data = {
            "provider": "Reuters",
            "ratetype": "EOD",
            "timestamp": "Not-A-Real-Timestamp",
        }

        with pytest.raises(ValueError):
            ExchangeRateInfo.from_dict(data)

    def test_key_collision_behavior_in_as_dict(self):
        metadata = {"provider": "HACKED"}

        with pytest.raises(ValueError, match="Metadata cannot contain reserved keys:"):
            _ = ExchangeRateInfo(provider="ECB", ratetype="", metadata=metadata)

    def test_getattr(self):
        dt = datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)
        ctx = ExchangeRateInfo(
            provider="ECB",
            ratetype="SPOT",
            timestamp=dt,
            metadata={"batch_id": "12345", "feed": "XML"},
        )
        assert ctx.batch_id == "12345"
        assert ctx.feed == "XML"
        assert ctx.ratetype == "SPOT"

        with pytest.raises(AttributeError):
            _ = ctx.frequency
