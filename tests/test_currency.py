from dataclasses import astuple

import pytest

from pycents import Ccy, Currency
from pycents.exceptions import InvalidCurrencyError


@pytest.fixture
def attributes():
    def make_tuple(ccy):
        return astuple(ccy)

    return make_tuple


def test_currency_new_has_expected_attr(attributes):
    dollar = Currency(Ccy.USD)
    assert dollar.ccy_code == Ccy.USD.ccy_code
    assert dollar.ccy_name == Ccy.USD.ccy_name
    assert dollar.symbol == ""
    assert dollar.is_iso
    assert dollar.minor_units == Ccy.USD.minor_units
    assert dollar.ccy_num_code == Ccy.USD.ccy_num_code


def test_currency_factory_with_str_arg(attributes):
    dollar = Currency.from_code("USD")
    assert dollar.ccy_code == Ccy.USD.ccy_code
    assert dollar.ccy_name == Ccy.USD.ccy_name
    assert dollar.symbol == ""
    assert dollar.is_iso
    assert dollar.minor_units == Ccy.USD.minor_units
    assert dollar.ccy_num_code == Ccy.USD.ccy_num_code


def test_currency_factory_with_ccy_arg(attributes):
    dollar = Currency.from_code(Ccy.USD)
    assert dollar.ccy_code == Ccy.USD.ccy_code
    assert dollar.ccy_name == Ccy.USD.ccy_name
    assert dollar.symbol == ""
    assert dollar.is_iso
    assert dollar.minor_units == Ccy.USD.minor_units
    assert dollar.ccy_num_code == Ccy.USD.ccy_num_code


def test_currency_factory_raises_for_invalid_str_code():
    with pytest.raises(InvalidCurrencyError) as exc_info:
        Currency.from_code("USSD")
    assert str(exc_info.value) == "'USSD' is not a known currency code."


def test_currency_returns_same_instance_for_same_arguments():
    dollar1 = Currency(Ccy.USD)
    dollar2 = Currency(Ccy.USD)
    dollar3 = Currency.from_code("USD")
    assert dollar2 is dollar1
    assert dollar3 is dollar1
