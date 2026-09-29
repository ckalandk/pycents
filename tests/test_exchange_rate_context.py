from datetime import UTC, datetime
from types import MappingProxyType

import pytest

from pycents.conversion import ExchangeRateInfo


class TestExchangeRateInfo:
    def test_initialization_and_defaults(self):
        ctx = ExchangeRateInfo(provider="ECB", ratetype="SPOT")

        assert ctx.provider == "ECB"
        assert ctx.ratetype == "SPOT"
        assert isinstance(ctx.asof, datetime)
        assert ctx.asof.tzinfo is UTC
        assert isinstance(ctx.metadata, MappingProxyType)
        assert len(ctx.metadata) == 0

    def test_full_initialization(self):
        dt = datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)
        ctx = ExchangeRateInfo(
            provider="ECB",
            ratetype="SPOT",
            asof=dt,
            metadata={"batch_id": "12345", "feed": "XML"},
        )

        assert ctx.asof == dt
        assert dict(ctx.metadata) == {"batch_id": "12345", "feed": "XML"}
        assert isinstance(ctx.metadata, MappingProxyType)

    def test_as_dict_serializes_correctly(self):
        dt = datetime(2026, 9, 8, 15, 30, 0, tzinfo=UTC)
        ctx = ExchangeRateInfo(
            provider="Bloomberg",
            ratetype="IMMEDIATE",
            asof=dt,
            metadata={"latency_ms": "42", "node": "eu-west-1"},
        )

        expected = {
            "provider": "Bloomberg",
            "ratetype": "IMMEDIATE",
            "asof": "2026-09-08T15:30:00+00:00",
            "metadata": {
                "latency_ms": "42",
                "node": "eu-west-1",
            },
        }
        assert ctx.as_dict() == expected

    def test_as_dict_without_metadata(self):
        dt = datetime(2026, 9, 8, 15, 30, 0, tzinfo=UTC)
        ctx = ExchangeRateInfo(provider="Bloomberg", ratetype="IMMEDIATE", asof=dt)

        expected = {
            "provider": "Bloomberg",
            "ratetype": "IMMEDIATE",
            "asof": "2026-09-08T15:30:00+00:00",
        }
        assert ctx.as_dict() == expected

    def test_from_dict_deserializes_correctly(self):
        data = {
            "provider": "Reuters",
            "ratetype": "EOD",
            "asof": "2026-09-08T23:59:59+00:00",
            "metadata": {
                "batch_id": "999",
                "status": "verified",
            },
        }

        ctx = ExchangeRateInfo.from_dict(data)

        assert ctx.provider == "Reuters"
        assert ctx.ratetype == "EOD"
        assert ctx.asof == datetime(2026, 9, 8, 23, 59, 59, tzinfo=UTC)
        assert dict(ctx.metadata) == {"batch_id": "999", "status": "verified"}
        assert isinstance(ctx.metadata, MappingProxyType)

    def test_from_dict_missing_core_fields_raises_key_error(self):
        data = {
            "provider": "Reuters",
            # missing ratetype and asof
            "batch_id": "999",
        }

        with pytest.raises(KeyError):
            ExchangeRateInfo.from_dict(data)

    def test_from_dict_invalid_asof_raises_value_error(self):
        data = {
            "provider": "Reuters",
            "ratetype": "EOD",
            "asof": "Not-A-Real-asof",
        }

        with pytest.raises(ValueError):
            ExchangeRateInfo.from_dict(data)
