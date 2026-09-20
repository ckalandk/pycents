from datetime import datetime
from decimal import Decimal

import pytest

from pycents import Currency
from pycents.conversion import (
    ExchangeRate,
    ExchangeRateInfo,
)
from pycents.exceptions import CurrencyMismatchError


class TestExchangeRate:
    @pytest.fixture
    def usd_eur(self) -> ExchangeRate:
        return ExchangeRate.from_pair("USD/EUR", "0.85")

    @pytest.fixture
    def eur_cad(self) -> ExchangeRate:
        return ExchangeRate.from_pair("EUR/CAD", "1.50")

    @pytest.fixture
    def cad_jpy(self) -> ExchangeRate:
        return ExchangeRate.from_pair("CAD/JPY", "100")

    def test_from_ratio(self):
        rate = ExchangeRate.from_pair("USD/EUR", "0.85")

        assert rate.base == Currency.from_code("USD")
        assert rate.quote == Currency.from_code("EUR")
        assert rate.rate == Decimal("0.85")
        assert rate.path == ()
        assert rate.info is None
        assert not rate.is_cross

    def test_from_ratio_accepts_supported_rate_types(self):
        assert ExchangeRate.from_pair("USD/EUR", 2).rate == Decimal("2")
        assert ExchangeRate.from_pair("USD/EUR", "2.5").rate == Decimal("2.5")
        assert ExchangeRate.from_pair(
            "USD/EUR",
            Decimal("2.75"),
        ).rate == Decimal("2.75")

    def test_from_ratio_info_is_preserved(self):
        info = ExchangeRateInfo(
            provider="ECB",
            ratetype="IMMEDIATE",
            asof=datetime.fromisoformat("2026-09-08T00:00:00+00:00"),
        )

        rate = ExchangeRate.from_pair(
            "USD/EUR",
            "0.85",
            info=info,
        )

        assert rate.info is info
        assert rate.path == ()
        assert not rate.is_cross

    @pytest.mark.parametrize(
        "expr",
        [
            "USD/EUR 0.85",
            "USD/EUR    0.85",
            "USD/EUR:0.85",
            "USD/EUR   :   0.85",
            "USD/EUR=0.85",
            "USD/EUR  =   0.85",
        ],
    )
    def test_from_string(self, expr):
        rate = ExchangeRate.from_string(expr)

        assert rate.base.ccy_code == "USD"
        assert rate.quote.ccy_code == "EUR"
        assert rate.rate == Decimal("0.85")
        assert rate.info is None
        assert rate.path == ()
        assert not rate.is_cross

    def test_from_string_preserves_context(self):
        context = ExchangeRateInfo(provider="ECB", ratetype="reference rate")
        rate = ExchangeRate.from_string("USD/EUR=0.85", info=context)

        assert rate.info is context

    def test_from_string_invalid_format_raises_error(self):
        with pytest.raises(ValueError, match="Invalid rate string format"):
            _ = ExchangeRate.from_string("USD/EUR-0.85")

    def test_negative_rates_are_rejected(self):
        with pytest.raises(
            ValueError, match="Expected a strictly positive exchage rate, got -0.85"
        ):
            _ = ExchangeRate.from_pair("USD/EUR", "-0.85")

    def test_multiplication(self, usd_eur, eur_cad):
        result = usd_eur * eur_cad

        assert result.base == usd_eur.base
        assert result.quote == eur_cad.quote
        assert result.rate == usd_eur.rate * eur_cad.rate

    def test_multiplication_creates_cross_rate(self, usd_eur, eur_cad):
        result = usd_eur * eur_cad

        assert result.is_cross
        assert result.path == (usd_eur, eur_cad)

    def test_multiplication_does_not_propagate_context(self):
        context1 = ExchangeRateInfo(
            provider="ECB",
            ratetype="IMMEDIATE",
            asof=datetime.fromisoformat("2026-09-08T00:00:00+00:00"),
        )
        context2 = ExchangeRateInfo(
            provider="Black Market",
            ratetype="FISHY",
            asof=datetime.fromisoformat("2026-09-08T00:01:00+00:00"),
        )

        usd_eur = ExchangeRate.from_pair(
            "USD/EUR",
            "0.85",
            info=context1,
        )
        eur_cad = ExchangeRate.from_pair(
            "EUR/CAD",
            "1.50",
            info=context2,
        )

        result = usd_eur * eur_cad

        assert result.info is None
        assert result.is_cross

    def test_multiplication_requires_matching_currencies(
        self,
        usd_eur,
    ):
        gbp_jpy = ExchangeRate.from_pair("GBP/JPY", "200")

        with pytest.raises(CurrencyMismatchError):
            _ = usd_eur * gbp_jpy

    def test_multiplication_with_non_exchange_rate(self, usd_eur):
        with pytest.raises(TypeError):
            _ = usd_eur * 2

    def test_lineage_of_direct_rate_is_self(self, usd_eur):
        assert usd_eur.lineage == (usd_eur,)

    def test_lineage_of_cross_rate(self, usd_eur, eur_cad):
        result = usd_eur * eur_cad

        assert result.lineage == (usd_eur, eur_cad)

    def test_nested_cross_rate_has_flat_lineage(
        self,
        usd_eur,
        eur_cad,
        cad_jpy,
    ):
        usd_cad = usd_eur * eur_cad
        usd_jpy = usd_cad * cad_jpy

        assert usd_jpy.path == (usd_cad, cad_jpy)
        assert usd_jpy.lineage == (
            usd_eur,
            eur_cad,
            cad_jpy,
        )

    def test_nested_cross_rate_remains_cross(
        self,
        usd_eur,
        eur_cad,
        cad_jpy,
    ):
        result = (usd_eur * eur_cad) * cad_jpy

        assert result.is_cross

    def test_nested_cross_rate_does_not_inherit_context(
        self,
    ):
        context = ExchangeRateInfo(
            provider="ECB",
            ratetype="IMMEDIATE",
            asof=datetime.fromisoformat("2026-09-08T00:00:00+00:00"),
        )

        usd_eur = ExchangeRate.from_pair(
            "USD/EUR",
            "0.85",
            info=context,
        )
        eur_cad = ExchangeRate.from_pair("EUR/CAD", "1.5")
        cad_jpy = ExchangeRate.from_pair("CAD/JPY", "100")

        result = (usd_eur * eur_cad) * cad_jpy

        assert result.info is None

    def test_arithmetic_is_immutable(self, usd_eur, eur_cad):
        original = usd_eur

        result = usd_eur * eur_cad

        assert usd_eur is original
        assert usd_eur.path == ()
        assert usd_eur.info is None
        assert result is not usd_eur

    def test_lineage_preserves_order(
        self,
        usd_eur,
        eur_cad,
        cad_jpy,
    ):
        result = (usd_eur * eur_cad) * cad_jpy

        assert result.lineage[0] is usd_eur
        assert result.lineage[1] is eur_cad
        assert result.lineage[2] is cad_jpy

    def test_multiplication_associativity_of_value(
        self,
        usd_eur,
        eur_cad,
        cad_jpy,
    ):
        left = (usd_eur * eur_cad) * cad_jpy
        right = usd_eur * (eur_cad * cad_jpy)

        assert left.base == right.base
        assert left.quote == right.quote
        assert left.rate == right.rate

    def test_multiplication_associativity_does_not_require_same_path(
        self,
        usd_eur,
        eur_cad,
        cad_jpy,
    ):
        left = (usd_eur * eur_cad) * cad_jpy
        right = usd_eur * (eur_cad * cad_jpy)

        assert left.lineage == right.lineage
        assert left.path != right.path

    # test inversion
    def test_invert(self, usd_eur):
        inverted = usd_eur.invert()

        assert inverted.base == usd_eur.quote
        assert inverted.quote == usd_eur.base
        assert inverted.rate == Decimal(1) / usd_eur.rate

    def test_invert_preserves_context(self):
        context = ExchangeRateInfo(
            provider="ECB",
            ratetype="IMMEDIATE",
            asof=datetime.fromisoformat("2026-09-08T00:00:00+00:00"),
        )
        rate = ExchangeRate.from_pair(
            "USD/EUR",
            "0.85",
            info=context,
        )

        inverted = rate.invert()

        assert inverted.info is context

    def test_invert_is_not_cross(self, usd_eur):
        inverted = usd_eur.invert()

        assert inverted.path == ()
        assert not inverted.is_cross

    def test_double_inversion_returns_original_state(self, usd_eur):
        # Obviously result.rate might not be equal to usd_eur.rate
        # du to Decimal finite precision, and it is specifically
        # true in this case because usd_eur.rate is equal to 0.85
        # and 1/0.85 yields a Decimal with infinitely many decimals.
        # You should never assum that 1/(1/r) == r!
        result = usd_eur.invert().invert()

        assert result.base == usd_eur.base
        assert result.quote == usd_eur.quote
        assert result.info is usd_eur.info
        assert result.path == ()

    def test_inverse_of_inverse_preserves_context_and_direct_status(self):
        context = ExchangeRateInfo(
            provider="ECB",
            ratetype="IMMEDIATE",
            asof=datetime.fromisoformat("2026-09-08T00:00:00+00:00"),
        )
        rate = ExchangeRate.from_pair(
            "USD/EUR",
            "2.5",
            info=context,
        )

        result = rate.invert().invert()

        assert result.info is context
        assert result.path == ()
        assert not result.is_cross

    def test_invert_preserve_cross_path(
        self,
        usd_eur,
        eur_cad,
    ):
        cross = usd_eur * eur_cad

        inverted = cross.invert()

        assert inverted.path == (eur_cad.invert(), usd_eur.invert())
        assert inverted.is_cross

    def test_exchange_rate_context_metadata(self):
        metadata = {"name": "Ministry", "code": "silly", "publish_cadence": "Weekly"}

        ctx = ExchangeRateInfo(provider="BBC", ratetype="one", metadata=metadata)

        usd_eur = ExchangeRate.from_pair("USD/EUR", "0.85", info=ctx)

        assert usd_eur.info is ctx
        assert usd_eur.info.metadata == metadata  # type: ignore

    def teste_exchange_rate_serialization(self):
        metadata = {"name": "Ministry", "code": "silly", "publish_cadence": "Weekly"}
        ctx = ExchangeRateInfo(
            provider="BBC",
            ratetype="one",
            asof=datetime.fromisoformat("2026-09-08T00:00:00+00:00"),
            metadata=metadata,
        )
        usd_eur = ExchangeRate.from_pair("USD/EUR", "0.85", info=ctx)
        eur_cad = ExchangeRate.from_pair("EUR/CAD", "1.16509", info=ctx)
        usd_cad = usd_eur * eur_cad

        assert usd_cad.info is None

        expected = {
            "base": "USD",
            "quote": "CAD",
            "rate": "0.9903265",
            "sources": [
                {
                    "base": "USD",
                    "quote": "EUR",
                    "rate": "0.85",
                    "info": {
                        "provider": "BBC",
                        "ratetype": "one",
                        "timestamp": "2026-09-08T00:00:00+00:00",
                        "name": "Ministry",
                        "code": "silly",
                        "publish_cadence": "Weekly",
                    },
                },
                {
                    "base": "EUR",
                    "quote": "CAD",
                    "rate": "1.16509",
                    "info": {
                        "provider": "BBC",
                        "ratetype": "one",
                        "timestamp": "2026-09-08T00:00:00+00:00",
                        "name": "Ministry",
                        "code": "silly",
                        "publish_cadence": "Weekly",
                    },
                },
            ],
        }
        assert usd_cad.as_dict() == expected

        rate = ExchangeRate.from_dict(expected)

        assert usd_cad == rate

    def test_str(self):
        rate = ExchangeRate.from_string("USD/CAD=1.6712")
        assert str(rate) == "USD/CAD = 1.6712"
