from dataclasses import astuple

import pytest

from pycents import Ccy, Currency, Xcy
from pycents.exceptions import InvalidCurrencyError


def test_currency_new_has_expected_attr():
    usd = Currency(Ccy.USD)
    assert astuple(usd) == Ccy.USD.value


def test_currency_factory_with_str_arg():
    usd = Currency.from_code("USD")
    assert astuple(usd) == Ccy.USD.value


def test_currency_factory_with_ccy_arg():
    usd = Currency.from_code(Ccy.USD)
    assert astuple(usd) == Ccy.USD.value


def test_currency_custom_xcy():
    btc = Currency(Xcy.BTC)
    assert btc.ccy_code == Xcy.BTC.ccy_code

    other = Currency.from_code("BTC")
    assert other is btc


def test_currency_factory_raises_for_invalid_str_code():
    with pytest.raises(InvalidCurrencyError) as exc_info:
        Currency.from_code("USSD")
    assert str(exc_info.value) == "'USSD' is not a known currency code."


def test_currency_returns_same_instance_for_same_arguments():
    usd1 = Currency(Ccy.USD)
    usd2 = Currency(Ccy.USD)
    usd3 = Currency.from_code("USD")
    assert usd2 is usd1
    assert usd3 is usd1


def test_currency_is_iso():
    usd = Currency(Ccy.USD)
    assert usd._is_iso()

    btc = Currency(Xcy.BTC)
    assert not btc._is_iso()


def test_get_xcy_def():
    btc = Currency(Xcy.BTC)
    xcy = btc._get_xcy_def()

    assert type(xcy) is Xcy
