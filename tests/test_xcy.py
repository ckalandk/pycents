import pytest

from pycents.exceptions import InvalidCurrencyError
from pycents.xcy import Xcy, XcyMeta


def test_xcy_register_currency(monkeypatch):
    registry = XcyMeta._registry.copy()
    original_length = len(registry)

    monkeypatch.setattr(XcyMeta, "_registry", registry)
    Xcy.register("HGC", "Holy Grail Coin", 0)
    Xcy.register("BKG", "Biggus Creditus", 2)

    assert "HGC" in Xcy
    assert "BKG" in Xcy

    assert len(registry) == original_length + 2

    xcy = Xcy.HGC
    assert xcy.ccy_code == "HGC"
    assert xcy.ccy_name == "Holy Grail Coin"
    assert xcy.minor_units == 0
    assert xcy.ccy_num_code > 1000


def test_xcy_register_already_existing_currency():
    with pytest.raises(InvalidCurrencyError):
        Xcy.register("BTC", "This is the real bitcoin", 0)


def test_xcy_del_currency(monkeypatch):
    registry = {}

    monkeypatch.setattr(XcyMeta, "_registry", registry)
    Xcy.register("HGC", "Holy Grail Coin", 0)
    Xcy.register("BKG", "Biggus Creditus", 2)

    assert "HGC" in Xcy
    assert "BKG" in Xcy

    assert len(registry) == 2

    del Xcy.BKG

    assert len(registry) == 1
    assert "HGC" in Xcy
    assert "BKG" not in Xcy


def test_xcy_getitem():
    xcy = Xcy["TST"]
    assert Xcy.TST == xcy


def test_xcy_iteration(monkeypatch):
    registry = {}
    monkeypatch.setattr(XcyMeta, "_registry", registry)

    Xcy.register("HGC", "Holy Grail Coin", 0)
    Xcy.register("BKG", "Biggus Creditus", 2)

    xcys = list(iter(Xcy))

    assert xcys == [Xcy.HGC, Xcy.BKG]


def test_xcy_raises_if_xcurrency_is_not_registered():
    with pytest.raises(AttributeError):
        _ = Xcy.SPAM

    with pytest.raises(InvalidCurrencyError):
        _ = Xcy["SPAM"]


def test_xcy_contain_dunder():
    assert not Xcy.__contains__("XXX")
    assert Xcy.__contains__(Xcy.BTC)


def test_xcy_repr():
    result = repr(Xcy.BTC)
    assert result == "Xcy.BTC"
