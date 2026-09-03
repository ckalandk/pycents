===========
Quick Start
===========

This guide introduces the most common operations you'll perform with PyCents.

Currency
========

Currencies are represented by the ``Currency`` class.
A ``Currency`` instance can hold either an **ISO 4217** currency
or a custom currency.

There are two ways to construct a ``Currency`` instance

* **Using the constructor**: pass a member of ``Ccy`` for ISO 4217 currencies
  or ``Xcy`` for custom currencies.

.. code-block:: python

    >>> from pycents import Currency, Ccy

    >>> usd = Currency(Ccy.USD)
    >>> usd
    Currency(ccy_code='USD')
    >>> bitcoin = Currency(Xcy.BTC)
    >>> bitcoin
    Currency(ccy_code='BTC')


.. note::

    `Xcy` comes with a selection of popular cryptocurrencies pre-registered,
    including Bitcoin and Ethereum, so they can be used directly without
    any additional setup.
    For information on registering your own custom currencies,
    see the :ref:`Custom Currencies <custom_currency>`..

Creating money
==============

Create money from minor units (The currency smallest unit e.g cents):

.. code-block:: python

    >>> from pycents import Money, Currency

    >>> wallet = Money(1250, Currency.from_code("USD"))
    >>> wallet.as_minors
    1250
    >>> wallet.as_majors
    Decimal('12.50')
    >>> bitcoins = Money(259, Currency.from_code("BTC"))
    >>> bitcoins.as_minors
    259

`wallet` represents a value of 1250 cents in USD.

.. note::
    A `Money` amount is stored internally as an integer number of minor
    currency units. Use `as_majors` and `as_minors` when you need to
    access the amount explicitly in either unit.

Or from major units:

.. code-block:: python

    >>> from decimal import Decimal

    >>> salary = Money.from_major(Decimal("3500.75"), "USD")
    >>> salary.as_majors
    Decimal('3500.75')
    >>> salary = Money.from_major("3500.75", "USD")
    >>> print(salary)
    USD 3500.75
    >>> salary = Money.from_major(2000, "EUR")
    >>> print(salary)
    EUR 2000

If the amount has more fractional digits than the currency supports,
an explicit rounding mode must be provided.

.. code-block:: python

    >>> from pycents import Money, RoundingMode

    >>> final_price = Money.from_major("19.175", "USD")
    ...
    ValueError: Amount 19.175 has more fractional digits than the USD minor units: 2.
    Specify a rounding mode to convert it to a valid monetary amount.

    >>> final_price = Money.from_major("19.175", "USD", rounding=RoundingMode.DOWN)
    >>> print(final_price)
    USD 19.17

.. note::
    The **minor unit** of a currency is its smallest fractional subdivision.
    In everyday language, it is what we call "cents", "penny",...
    In the ISO 4217 standard, the minor unit is represented by an **exponent**,
    which simply means how many decimal places are required to represent that
    fractional unit.


High-precision money
====================

Sometimes you need to track values much smaller than a currency's
official minor unit, such as pricing a single API call at $0.0000167.
For high-precision or intermediate calculations that should not be rounded,
use ``UnroundedMoney``.

.. code-block:: python

    from pycents import Money, UnroundedMoney
    price_per_million_api_call = Money.from_major(1.67, "USD") # 167 cents
    price_per_api_call = price_per_million_api_call / 1_000_000
    assert isinstance(price_per_api_call, UnroundedMoney)
    print(price_per_api_call)
    # [Output] USD 0.0000167


``UnroundedMoney`` bypasses the strict minor-unit rounding rules, but works
seamlessly alongside the standard ``Money`` class.
You can safely mix them in calculations to accumulate highly precise fractions,
and round the final total back to standard ``Money`` when it is time to charge your customer.

Think of it this way:

* ``Money`` is a finalized, quantized value ready for the real world.
* ``UnroundedMoney`` is an intermediate, high-precision mathematical state.

.. important::

    You rarely need to instantiate ``UnroundedMoney`` directly. As shown above,
    standard ``Money`` objects automatically convert to ``UnroundedMoney`` when
    multiplied/divided by Decimals. But if you ever need to construct
    an ``UnroundedMoney`` instance directly, use ``from_major`` method.
    See the example below:

.. code-block:: python

    from decimal import Decimal
    from pycents import Money, UnroundedMoney, RoundingMode

    gas_price_per_gallon = UnroundedMoney.from_major(Decimal("4.0656"), "USD")
    volume = Decimal("12.345") # gallons
    subtotal = gas_price_per_gallon * volume # USD 50.189832
    # At this stage subtotal is still an `UnroundedMoney` instance
    assert isinstance(subtotal, UnroundedMoney)
    # Getting the final price
    total = subtotal.round(RoundingMode.HALF_UP)

    # `total` is a valid monetary amount
    assert isinstance(total, Money)

    print(total)
    # [Output] USD 50.19

Arithmetic Operations
=====================

Addition
--------

Adding two ``Money`` objects produces another ``Money`` instance.

.. code-block:: python

    income = Money.from_major(2500, "USD")
    bonus = Money.from_major(500, "USD")

    total = income + bonus

Subtraction
-----------

Subtracting values is equally straightforward:

.. code-block:: python

    remaining = total - Money.from_major(250, "USD")

.. warning::

    Attempting to combine monetary amounts with different currencies
    raises a `CurrencyMismatchError` exception.


Multiplication and division
---------------------------

Multiplication and division are somehow different.
Multiplying a ``Money`` instance by an integer produces another ``Money`` object.

.. code-block:: python

    >>> price = Money.from_major("19.99", "USD")
    >>> items = 20
    >>> total = price * 20
    >>> assert isinstance(total, Money)
    >>> print(total)
     USD 399.80

If the factor of the multiplication is a ``Decimal``, the result
of the operation will be an instance of ``UnroundedMoney``.

.. code-block:: python

    >>> from pycents import Money, UnroundedMoney

    >>> price = Money.from_major("19.99", "USD")
    >>> vat = (price * Decimal("0.20"))
    >>> assert isinstance(vat, UnroundedMoney)

``UnroundedMoney`` object retain the full precision of arithmetic operations.
No implicit rounding is performed. Users should call ``round()`` at the end
of the arithmetic pipeline to convert the ``UnroundedMoney`` object to a
``Money`` instance.

``round`` uses the half-even rounding policy by default,
you may use another rounding policy available through the enum ``RoundingMode``:

.. code-block:: python

    >>> from pycents import Money, RoundingMode
    >>> cost_per_month = Money.from_major("26.99", "USD")

    >>> days_used = 17
    >>> prorated_cost = (cost_per_month * days_used) / Decimal('30')
    >>> print(prorated_cost)
    USD 15.29433333333333333333333333
    >>> print(prorated_cost.round(RoundingMode.DOWN))
    USD 15.29

Allocation
==========

Allocation is best explained through an example.
A company has three departments, each occupying a different amount of office space.
The company receives a monthly rent bill of 100,000 USD, which must be allocated
among the departments according to the area each department occupies.

Department A occupies 1,000 square feet, Department B occupies 2,000 square feet,
and Department C occupies 3,000 square feet.

This is an example of proportional allocation. **PyCents** provide utility
functions through the module ``pycents.allocation`` to perform proportional
allocation without ever loosing a penny in the process.

.. code-block:: python

    >>> from pycents import allocation as alloc
    >>> from pycents import Money

    >>> rent = Money.from_major(100_000, "USD")
    >>> ratios = [1000, 2000, 3000]

    >>> allocation_result = alloc.allocate(rent, ratios)

    >>> print(", ".join(str(share) for share in allocation_result))
    USD 16666.67, USD 33333.33, USD 50000.00


.. note::

    The function ``allocate`` use the **Hamilton** apportionment strategy to distribute
    the leftover cents. See :ref:`Allocation <guide-allocation>`..
    for a detailed breakdown.

Formatting
==========

PyCents provide rich options for formatting ``Money`` and ``UnroundedMoney`` objects.
it ships with a standard locale-agnostic formatter which is available
right out of the box.

Locale-aware formatting is also available through optional formatting backends.

.. code-block:: python

    >>> price = Money.from_major("2.99", "USD")
    >>> print(f"{price}")
    USD 2.99
    >>> print(f"{price:h}")  # Hide the currency
    2.99
    >>> price = Money.from_major(29990005, "USD")
    >>> print(f"{price:c}")  # Print in compact format
    USD 30.0M
    >>> print(f"{price:.3c}")  # Retain 3 decimals
    USD 29.990M
    >>> print(f"{price:.3c~}") # Trim trailing zeros
    USD 29.99M
    >>> print(f"{price:hc}")  # Hide currency symbol and use compact format
    30.0M
    >>> price = -price
    >>> print(f"{price:a}")  # Use accounting format
    (USD 29,990,005.00)

.. _format-specification:

The format specification are parsed according to this grammar:

.. code-block:: text

    money-format ::= money-spec string-format
    money-spec ::= [display] [compact-prec] [compact] [accounting] [ungroup] [trim]

    display      ::= h | i | n
    compact-prec ::= .integer
    compact      ::= c
    accounting   ::= a
    ungroup      ::= u
    trim         ::= ~

Display options:
----------------

* **h**: Hide the currency symbol.
* **i**: Display the ISO 4217 currency code.
* **n**: Display the currency name.
* **.integer**: Specify the number of fractional digits to display
  when using compact notation (for example, ``.2c`` renders as ``1.25M`` instead of ``1.2M``).
* **c**: Use compact notation (for example, ``1.2M``).
* **a**: Display negative amounts using accounting notation
  (for example, ``(123.45)`` instead of ``-123.45``).
* **u**: Disable digit grouping
  (for example, ``1000000`` instead of ``1,000,000``).
* **~**: Trim insignificant trailing zeros
  (e.g ``3.5`` instead of ``3.50``)

Localized Money Formatting
-------------------------------

Localized formatting is provided through optional backends. ``PyCents`` supports
both `Babel <https://babel.pocoo.org/>`_ and `pyicu <https://pypi.org/project/pyicu/>`_.

.. warning::

    Before using any of the following examples, ensure that ``babel`` or ``pyicu``
    is properly installed.

Choosing a formatter
^^^^^^^^^^^^^^^^^^^^

You may choose any available backend formatter by simply calling ``use_backend``
function from the ``formatting`` module.

.. code-block:: python

    from pycents import Money, formatting
    formatting.use_backend("babel") # other options are: 'icu' or 'std' (the default)

    money = Money.from_major(2600, "USD")
    print(f"{money}")  # Output: $2600

By default, ``babel`` or ``icu`` use the host environment to determine
the locale to use, see the following example on how to explicitly choose a locale:

.. code-block:: python

    from pycents import Money, formatting

    formatting.use_backend("babel")
    formatting.basicConfig(locale="fr_FR")

    money = Money.from_major(2600, "USD")
    print(f"{money}") # --> 2 600,00 $US

.. caution::

    Locale configuration should be done after backend selection.

Next steps
==========

Continue with the :doc:`User Guide </guide/index>` for a detailed explanation of:

* Creating money
* Arithmetic
* Allocation
* Advanced Formatting
