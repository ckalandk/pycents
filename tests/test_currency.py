from dataclasses import astuple

import pytest

from pycents import Ccy, Currency, Xcy
from pycents.exceptions import InvalidCurrencyError


def test_currency_new_has_expected_attr():
    usd = Currency(Ccy.USD)
    assert astuple(usd) == Ccy.USD.value

    tst = Currency(Xcy.TST)
    assert astuple(tst) == Xcy.TST.value


def test_currency_init_reject_non_valid_currencies():
    with pytest.raises(TypeError, match="Expected an instance of Ccy or Xcy"):
        _ = Currency("USD")  # type: ignore


def test_currency_factory_with_str_arg():
    usd = Currency.from_code("USD")
    assert astuple(usd) == Ccy.USD.value

    tst = Currency.from_code("TST")
    assert astuple(tst) == Xcy.TST.value


def test_currency_factory_with_ccy_arg():
    usd = Currency.from_code(Ccy.USD)
    assert astuple(usd) == Ccy.USD.value

    tst = Currency.from_code(Xcy.TST)
    assert astuple(tst) == Xcy.TST.value


def test_currency_factory_raises_for_invalid_str_code():
    with pytest.raises(InvalidCurrencyError) as exc_info:
        Currency.from_code("USSD")
    assert str(exc_info.value) == "'USSD' is not a known currency code."


def test_currency_returns_same_instance_for_same_arguments():
    # Test with iso currencyies
    usd1 = Currency(Ccy.USD)
    usd2 = Currency(Ccy.USD)
    usd3 = Currency.from_code("USD")
    assert usd2 is usd1
    assert usd3 is usd1

    # Test with non-fiat currencies
    tst1 = Currency(Xcy.TST)
    tst2 = Currency(Xcy.TST)
    tst3 = Currency.from_code("TST")
    assert tst2 is tst1
    assert tst3 is tst1


def test_currency_is_iso():
    usd = Currency(Ccy.USD)
    assert usd._is_iso()

    btc = Currency(Xcy.BTC)
    assert not btc._is_iso()


def test_get_xcy_def():
    tst = Currency(Xcy.TST)
    xcy = tst._get_xcy_def()

    assert xcy == Xcy.TST


def test_get_xcy_def_reject_ccy_args():
    test = Currency(Ccy.USD)
    with pytest.raises(ValueError, match="Cannot get Xcy definition"):
        _ = test._get_xcy_def()
