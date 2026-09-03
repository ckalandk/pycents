====================
Money and Currencies
====================

The ``Money`` class represents a monetary amount expressed in a specific ISO 4217 currency
or a custom currency.

A ``Money`` instance combines two pieces of information:

* a monetary amount represented internally as an ``int`` number of
  **minor units** (for example, cents)
* a currency represented by a ``Currency`` instance.

So before diving into ``Money`` inner working, let's pick up where we left off
in the :doc:`Quickstart</quick_start/quickstart>` and take a closer look at currencies.


Currency
========

The ``Currency`` class represents a currency used by ``Money``. A currency can be
either an ISO 4217 currency or a custom currency.

Internally, ``pycents`` maintains two collections of currency definitions:

* ``Ccy`` contains the currencies defined by ISO 4217.
* ``Xcy`` contains custom currencies registered by the user.

Although ``Ccy`` is a regular Python enum, ``Xcy`` is an enum-like class implemented
by pycents. Both provide a type-safe way of referring to a currency definition.

Users are generally **not expected to interact directly with ``Ccy`` or ``Xcy``**.
They serve two purposes: they provide a database-like collection of available
currency definitions, and they provide a strongly typed argument for constructing
``Currency`` instances.

Creating a Currency
-------------------

A Currency can be constructed by passing a member of ``Ccy`` or ``Xcy``:

.. code-block:: python

    >>> from pycents import Currency, Ccy, Xcy

    >>> euro = Currency(Ccy.EUR)
    >>> bitcoin = Currency(Xcy.BTC)

The constructor deliberately does not accept a string currency code,

.. code-block:: python

    >>> Currency("EUR")
    TypeError: ...

This is intentional. ``Currency`` constructors are strongly typed and are designed
to accept currency definitions rather than arbitrary values.

.. note::

    This is a recurring theme in ``pycents``, almost all constructors are strongly
    typed and convenient constructions are offered through classmethods

When convenient construction from a currency code is desired, use
:meth:`Currency.from_code` instead:

.. code-block:: python

    >>> euro = Currency.from_code("EUR")
    >>> bitcoin = Currency.from_code("BTC")

``Currency.from_code`` accepts either a currency definition or a string code:

.. code-block:: python

    Currency.from_code(Ccy.EUR)
    Currency.from_code(Xcy.BTC)
    Currency.from_code("EUR")
    Currency.from_code("BTC")

Currency information
--------------------

A ``Currency`` instance exposes the information associated with its currency
definition.

For example:

.. code-block:: python

    >>> euro.ccy_code
    'EUR'
    >>> euro.ccy_name
    'Euro'
    >>> euro.minor_units
    2
    >>> euro.ccy_num_code
    978

For a custom currency such as Bitcoin:

.. code-block:: python

    >>> bitcoin.ccy_code
    'BTC'
    >>> bitcoin.ccy_name
    'Bitcoin'
    >>> bitcoin.minor_units
    8
    >>> bitcoin.symbol
    '₿'

The main attributes are:

* ``ccy_code``

The currency code. For ISO 4217 currencies this is the standard three-letter
ISO code. For custom currencies it is the code assigned when the currency is
registered.

* ``ccy_name``

The name of the currency.

* ``minor_units``

The number of decimal places used to represent the currency's minor units.

* ``ccy_num_code``

An integer numeric code associated with the currency. For ISO 4217 currencies
this is the ISO numeric code. Custom currencies are also assigned a unique
numerical code.

.. note::

    Currency instances are immutable and cached internally.

.. _custom_currency:

Custom currencies
-----------------

Custom currencies are stored in ``Xcy``. Several cryptocurrencies are registered
by default, but applications can also register their own currencies.

A custom currency is registered with :meth:`Xcy.register`:

.. code-block:: python

    >>> from pycents import Xcy, Money, formatting

    >>> Xcy.register(
    ...     code="HGC",
    ...     name="Holy Grail Coin",
    ...     minor_units=2,
    ...     symbol="🍷",
    ... )
    >>> formatting.use_backend("babel")
    >>> mny = Money.from_major("2000", "HGC")
    >>> print(f"{mny}")
    🍷2,000.00

Once registered, the currency can be accessed through ``Xcy`` just like an enum
member:

.. code-block:: python

    >>> Xcy.HGC
    Xcy.HGC

It can also be accessed using subscription syntax:

.. code-block:: python

    >>> Xcy["HGC"]
    Xcy.HGC

The ``in`` operator can be used to check whether a currency is registered:

.. code-block:: python

    >>> "BTC" in Xcy
    True
    >>> Xcy.HGC in Xcy
    True
    >>> "XYZ" in Xcy
    False

``Xcy`` is also iterable:

.. code-block:: python

    >>> for xcy in Xcy:
    ...     print(xcy)
    Xcy.BTC
    Xcy.ETH
    Xcy.EHG
    ...

Overriding Custom Currency Definition
-------------------------------------

Registering a currency with a code that is already present in ``Xcy`` or ``Ccy``
**raises an exception**.

.. code-block:: python

    >>> from pycents import Xcy

    >>> Xcy.register(
    ...     code="BTC",
    ...     name="Genuine bitcoin",
    ...     minor_units=8,
    ...     symbol="₿",
    ... )

    InvalidCurrencyError: 'BTC' is already defined


If you want to provide currency metadata localized to a particular
language or domain for an already registered currency, the only way around
is to delete it an register it again under different name.

.. code-block:: python

    >>> from pycents import Xcy

    >>> del Xcy.BTC

    >>> Xcy.register(
    ...     code="BTC",
    ...     name="подлинный биткоин",
    ...     minor_units=8,
    ...     symbol="₿",
    ... )

Money
=====

``Money`` is the central class of **PyCents**. A ``Money`` instance is always
associated with a specific currency and stores its amount internally as an
integer number of minor units. For example, $12.50 is represented as 1250 minor units of USD.

**Money instance represents amounts that can be expressed exactly using the currency's
standard minor unit.** This a fundamental invariant of the ``Money`` class and is maintained
throughout the Money API. For example, USD has a minor unit of two decimal places,
so ``Money`` can represent $12.34 but not $12.345!

For higher precision calculations, ``Money`` provides a companion class called ``UnroundedMoney``.
This class is used to represent amounts that cannot be expressed exactly using the currency's
standard minor unit. For example, multiplying $12.34 by 1.5 yields $18.525, which cannot be represented
exactly using USD's two decimal places. In this case, the result is an ``UnroundedMoney`` instance.

Creating money
--------------

From minor units using ``Money`` constructor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Creating a ``Money`` instance using the constructor requires an integer
amount expressed in minor units and a Currency instance.

.. code-block:: python

    from pycents import Money, Currency, Ccy
    >>> price = Money(1999, Currency(Ccy.USD))
    >>> print(price)
    USD 19.99
    >>> price = Money(1999, Currency.from_code("BTC"))
    >>> print(price)
    BTC 0.00001999

From minor units using ``Money.from_minor`` factory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This factory method is equivalent to calling the Money constructor after
resolving the currency from its code.

Unlike the constructor, ``from_minor()`` accepts a currency code as a
string in addition to a ``Ccy`` or ``Xcy`` instance.

.. code-block:: python

    from pycents import Money, Currency, Ccy
    >>> price = Money.from_minor(1999, Ccy.USD)
    >>> print(price)
    USD 19.99
    >>> price = Money.from_minor(1999, "BTC")
    >>> print(price)
    BTC 0.00001999

From major units
^^^^^^^^^^^^^^^^

Use ``Money.from_major()`` when constructing money in major units from decimal values.
This method accepts either an ``int``, ``str`` or a ``Decimal``.

.. code-block:: python

    >>> from decimal import Decimal

    >>> salary = Money.from_major(
    ...     Decimal("3500.75"),
    ...     "USD",
    ... )
    >>> salary = Money.from_major("3500.75", "USD")
    >>> salary = Money.from_major(3500, "USD")
    >>> print(salary)
    USD 3500.75


The value is converted to minor units according to the currency's
number of decimal places.

The class method ``from_major`` accepts an optional third keyword argument that
specifies the rounding mode to apply when the monetary amount has more fractional digits
than the currency supports. If omitted, an exception is raised when the amount cannot
be represented exactly in minor units.

The Rounding Policies are provided through the enum ``RoundingMode``
from the ``pycents.rounding`` package. See :doc:`/guide/rounding`.

.. code-block:: python

    # USD Supports only two fractional digits
    >>> from pycents.rounding import RoundingMode

    >>> price = Money.from_major("150.756", "USD")
    ...
    ValueError: Cannot represent 150.756 USD in minor units...

    >>> price = Money.from_major("150.754", "USD", rounding=RoundingMode.DOWN)
    >>> print(price)
    USD 150.75


ZERO Monetary amount
^^^^^^^^^^^^^^^^^^^^

Whenever you need a `Money` instance with zero amount, prefer using
the classmethod `zero` to enable caching

.. code-block:: python

    from pycents import Money, Currency

    # zero1 will be cached internally
    zero1 = Money.zero("USD")

    # using from_major with a zero amount, will return
    # the cached value if present
    zero2 = Money.from_major(0, "USD")
    assert zero2 is zero1

    # Using Money Constructor bypasses the cache
    zero3 = Money(0, Currency.from_code("USD"))
    assert zero3 is not zero1

Creating UnroundedMoney
-----------------------

In most cases, you do not need to construct an ``UnroundedMoney`` instance
directly. It is produced automatically when an arithmetic operation on
Money results in an amount with more fractional digits than the
currency's standard minor unit.

For example, multiplying $12.35 by 1.5 produces $18.512.
The result is represented as an ``UnroundedMoney`` because the intermediate
result is not required to satisfy the two-decimal-place invariant of USD.

.. code-block:: python

    >>> from decimal import Decimal
    >>> from pycents import Money, UnroundedMoney

    >>> price = Money.from_major("12.35", "USD")
    >>> result = price * Decimal("1.5")

    >>> isinstance(result, UnroundedMoney)
    True
    >>> result.as_majors
    Decimal('18.512')

An ``UnroundedMoney`` retains the full precision of the calculation and does
not perform implicit rounding. When the calculation is complete, use
``round()`` to convert it back to a Money instance:

.. code-block:: python

    >>> total = result.round()
    >>> isinstance(total, Money)
    True
    >>> total.as_majors
    Decimal('18.51')

Constructing UnroundedMoney directly
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can construct an UnroundedMoney directly when you already have a
high-precision amount expressed in major currency units. Use
``  UnroundedMoney.from_major() for this purpose.

.. code-block:: python

    >>> price = UnroundedMoney.from_major("12.345", "USD")
    >>> price.as_majors
    Decimal('12.345')

Unlike ``Money.from_major()``, ``UnroundedMoney.from_major()`` does not require
the amount to conform to the currency's standard minor unit and does not
perform rounding.

The resulting value remains an ``UnroundedMoney`` until it is explicitly
rounded:

.. code-block:: python

    >>> price.round()
    Money(1235, 'USD')
    >>> price.round().as_majors
    Decimal('12.35')
    >>> price.round(rounding=RoundingMode.DOWN).as_majors
    Decimal('12.34')

As the example above shows, you can specify a rounding mode when calling ``round()``.

.. note::
    You can also explicitly convert standard ``Money`` to ``UnroundedMoney``
    by passing it directly to the constructor: ``UnroundedMoney(my_money)``

Arithmetic
----------

``PyCents`` categorizes arithmetic operations into two types:

* **Minor-Unit arithmetic operations**
* **Sub-Unit arithmetic operations**


Minor-Unit arithmetics
^^^^^^^^^^^^^^^^^^^^^^

Operations whose results amount natively fit inside the standard
currency's minor units. This type of operations produce a ``Money`` instance.

.. note::

    Some operations naturally yield a valid amount; for example,
    adding $19.12 and $15.12 yields $34.24, which already satisfies the "USD"
    currency minor units without needing any rounding.


List of all the Minor-Unit operations
"""""""""""""""""""""""""""""""""""""

* **Addition/Subtraction**

  Adding/Subtracting two ``Money`` objects are Minor-Unit operations:

  .. code-block:: python

      >>> salary = Money.from_major(2500, "USD")
      >>> bonus = Money.from_major("50.55", "USD")
      >>> total = salary + bonus
      >>> assert type(total) is Money

      >>> price = Money.from_major("12.99", "USD")
      >>> discount = Money.from_major(2, "USD")
      >>> final_price = price - discount
      >>> assert type(final_price) is Money


* **Multiplication by an integer factor**

  Multiplying a ``Money`` instance by an ``int`` returns another ``Money`` instance.

  .. code-block:: python

      >>> unit_price = Money.from_major(12.99, "USD")
      >>> number_of_items = 15
      >>> total_price = unit_price * number_of_items
      >>> assert type(total_price) is Money

* **Negation**

  .. code-block:: python

      >>> -balance

  returns a new ``Money`` instance with the opposite sign.

* **abs**

.. code-block:: python

    >>> mny = Money.from_major("-299", "USD")
    >>> print(abs(mny))
    USD 299.00

Sub-Unit arithmetics
^^^^^^^^^^^^^^^^^^^^

Operations that introduce fractional minor units and preserve sub-unit precision.

This type of operations does not produce an actual ``Money`` instance. ``PyCents``
uses a special type ``UnroundedMoney`` to hold the result of this type of operations,
maintaining the full precision of the calculation while ignoring completely
the currency's standard minor units.

Consider for example the case where we have a salary of **$1500.45**, and we need to apply
a bonus of **30%**. Multiplying **1500.45** by **1.3** yields **1950.585** which has more
fractional digits than the **USD** currency supports. In simple terms, **1950.585** is not
a valid ISO **USD** monetary amount!

In order to get an actual valid money, you need to call a special method on an ``UnroundedMoney``
instance, namely: ``round()``. Either by supplying a **rounding mode** as an argument, or use
the default rounding mode **round half even**.

.. code-block:: python

    >>> salary = Money.from_major("1500.45", "USD")
    >>> bonified_salary = (salary * Decimal("1.3")).round() # round half even
    >>> print(bonified_salary)
    USD 1950.58

Arithmetic rules:
^^^^^^^^^^^^^^^^^

Arithmetic operations work according to this rules
(we'll abbreviate UnroundedMoney to Unrounded):

.. code-block:: text

    Money +/- Money = Money
    Money +/- Unrounded = Unrounded
    Unrounded +/- Unrounded = Unrounded
    Money * IntegerFactor = Money
    Money * DecimalFactor = Unrounded
    Money / Factor = Unrounded
    Money / Money = Decimal
    Unrounded * factor = Unrounded

PyCents does not impose when rounding should occur, the appropriate rounding
points are determined by the application's business.

When no intermediate rounding is required, postponing ``round()`` until the end
of the calculation preserves the maximum available precision. However, this is
not always desirable. For example, cryptocurrency and blockchain systems
typically perform monetary arithmetic using integers representing the smallest
unit of a currency, such as wei for Ethereum. Any fractional smallest units
produced by an intermediate operation cannot be represented and are therefore
discarded.

To emulate such integer-based cryptocurrency arithmetic with **PyCents**,
``round()`` with an appropriate rounding mode, must be explicitly applied at every intermediate steps that
might produce and ``Unrounded`` results. For example, an
18-decimal WAD calculation that truncates after every operation can be
simulated by calling ``round(RoundingMode.DOWN)`` after each operation.

Decimal precision and implicit rounding
---------------------------------------

``PyCents`` does not perform implicit rounding at the library level.
However, arithmetic involving ``UnroundedMoney``, which uses Python's ``Decimal`` internally,
is still subject to the active decimal context.
In particular, the context's precision can cause ``Decimal`` operations
to round their results implicitly.

This is especially important when working with currencies that have a
large number of decimal places, such as cryptocurrencies whose smallest
units may correspond to 18 or more decimal places.
In such cases, the default ``Decimal`` precision can be exhausted much more
easily than it would be with conventional fiat currencies.

A typical example is when the result of an operation yield an amount
with infinite decimals. Consider the following case:

.. code-block:: python

    from decimal import Decimal

    mny = Money(10, Currency.from_code("USD"))
    unr = mny / Decimal(3)

The exact decimal expansion of ``10 / 3`` is infinite. Because ``Decimal`` arithmetic
is performed under a finite precision context, the result must be rounded
according to the active context. This rounding happens inside ``Decimal``
itself and is therefore invisible to ``pycents``.

The only thing you can do in this situation is controlling
the rounding mode used by Python or increasing the precision of the active Decimal context, if yo
think that the final result could be affected by the new precision.

.. code-block:: python

    from pycents import Money, Currency
    from pycents.rounding import RoundingMode, as_decimal_rounding
    from decimal import Decimal, localcontext

    mny = Money(10, Currency.from_code("USD"))
    with localcontext() as ctx:
        ctx.rounding = as_decimal_rounding(RoundingMode.UP)
        factor = Decimal(3)
        unr = mny / factor
        print(unr)

Controlling Decimal precision
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When working with custom currencies that require a large number
of decimal places, you should consider increasing the precision
of the active Decimal context.

For example:

.. code-block:: python

    from decimal import getcontext
    from pycents import Money

    # Increase the precision of the current Decimal context
    getcontext().prec = 80
    # Ethereum supports up to 18 decimals
    mny = Money.from_minor(34990000000000000005, "ETH")
    ...

Alternatively, you can limit the increased precision to a specific
section of code by using ``decimal.localcontext()``:

.. code-block:: python

    from decimal import Decimal, localcontext

    with localcontext() as ctx:
        ctx.prec = 100
        ...

Detecting implicit rounding
^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can configure the Decimal context to raise an exception
whenever an operation would require rounding under the active Decimal context:

.. code-block:: python

    from decimal import Decimal, Inexact, localcontext

    mny = Money(100, Currency.from_code("USD"))

    with localcontext() as ctx:
        ctx.traps[Inexact] = True
        # Raises decimal.Inexact because 100 / 3
        # cannot be represented exactly.
        unr = mny / Decimal(3)

This is in my opinion often the safest approach.
Instead of silently accepting a rounded intermediate result,
the calculation fails immediately and gives you the opportunity
to decide how the operations should be handled.

You can then either:

* **Choose an explicit rounding policy** when the operation yields
  result with infinitely many decimals. Alternatively, you can increase the Decimal precision
  if you think that the final result could be affected by the new precision.

* **Increase the Decimal precision** when the operation is finite but
  requires more digits than the default ``Decimal`` context precision.

Avoid Floating-Point Numbers
----------------------------

When working with monetary values, **never use Python `float` to represent an amount**.

PyCents accepts exact numeric representations for monetary amounts:

* `int` when the value is an integer;
* `str` representing an exact decimal number;
* `Decimal` for decimal arithmetic.

For example:

.. code-block:: python

    from decimal import Decimal
    from pycents import Money

    Money.from_major("10.50", "EUR")
    Money.from_major(Decimal("10.50"), "EUR")
    Money.from_major(10, "EUR")


Avoid passing a `float`:

.. code-block:: python

    Money.from_major(10.50, "EUR")  # Don't do this

Floating-point arithmetic is inherently imprecise. Using `float` in scientific
calculation is perfectly valid, but not in financial applications where every
cent must be accounted for.

.. code-block:: python

    >>> 0.1 + 0.2
    0.30000000000000004


``PyCents`` does not reject `float` values at runtime. However, its type annotations
deliberately do not include `float`, so a static type checker such as **mypy** or
**Pyright** will report an error when a float is passed to an API expecting an
exact monetary value.

This is intentional: ``PyCents`` relies on the type system to help prevent
accidental use of floating-point numbers while avoiding unnecessary runtime restrictions.

.. attention::

    **Rule of thumb:** if a number represents money, use
    `int`, `str`, or `Decimal` — **never `float`**.

Bulk summation
--------------

If you find yourself doing a lot of summation inside a tight loop, consider
using `Money.sum` classmethod to perform a bulk summation which is more efficient
then a loop.

.. code-block:: python

    from decimal import Decimal
    from pycents import Money, UnroundedMoney, RoundingMode

    items = [
        {"name": "item1", "price": "249.99", "discount": "0.15"},
        {"name": "item2", "price": "119.50", "discount": "0.0"},
        {"name": "item3", "price": "389.00", "discount": "0.10"},
        {"name": "item4", "price": "12.99", "discount": "0.0"},
        {"name": "item5", "price": "89.99", "discount": "0.20"},
        {"name": "item6", "price": "199.95", "discount": "0.05"},
        {"name": "item7", "price": "149.00", "discount": "0.0"},
        {"name": "item8", "price": "24.50", "discount": "0.0"},
        {"name": "item9", "price": "34.99", "discount": "0.125"},
        {"name": "item10", "price": "59.99", "discount": "0.0"},
    ]

    prices = [Money.from_major(item["price"], "USD") for item in items]
    prices_after_discounts = [
        mny - mny * Decimal(item["discount"]) for mny, item in zip(prices, items)
    ]

    # `total` is either a `Money` or a `UnroundedMoney` instance
    # You can, either supply a rounding mode via the keyword argument `rounding`
    # to get a Money instance

    total = Money.sum(prices_after_discounts, rounding=RoundingMode.UP)
    assert isinstance(total, Money)

    print(total) # Output: USD 1221.14
    # If you don't provide a rounding mode the result will be an
    # `UnroundedMoney` instance if there is at least one `UnroundedMoney`
    # instance in the provided list, or a `Money` object otherwise

    total = Money.sum(prices_after_discounts)
    assert isinstance(total, UnroundedMoney)

    # At this stage you can carry on with any remainding calculation
    # or round the result to get a `Money` instance
    final_price = total.round()
    print(final_price) # Output: USD 1221.14

Comparison
----------

Money/Unrounded objects support the standard comparison operators.

.. code-block:: python

    >>> wallet > savings
    >>> wallet == savings
    >>> wallet <= savings

Comparisons are only valid between identical currencies.
Attempting to compare different currencies raises ``MismatchCurrencyError``.

.. warning::

    You cannot directly compare ``Money`` and ``UnroundedMoney`` objects, doing
    so will raise a ``TypeError`` exception. You need to convert the Unrounded object
    to a ``Money`` instance before trying to compare them.

Miscellaneous
--------------

Serialization
^^^^^^^^^^^^^

When interacting with APIs, databases, or JSON payloads, you often need to
serialize and deserialize money objects. ``pycents`` provides ``as_dict()``
and ``from_dict()`` for this exact purpose.

.. code-block:: python

    >>> price = Money.from_major("199.99", "USD")
    >>> data = price.as_dict()
    >>> print(data)
    {'amount': 19999, 'currency': 'USD'}

    >>> restored = Money.from_dict(data)
    >>> assert price == restored

Boolean Evaluation
^^^^^^^^^^^^^^^^^^

``Money`` and ``UnroundedMoney`` instances evaluate to ``False`` if their amount is zero,
and ``True`` otherwise.

.. code-block:: python

    >>> wallet = Money.zero("USD")
    >>> if not wallet:
    ...     print("Wallet is empty!")
    Wallet is empty!

Hashability
^^^^^^^^^^^

Both ``Money`` and ``UnroundedMoney`` are immutable and fully hashable.
Their hash is computed based on their amount and currency.

.. code-block:: python

    >>> price_1 = Money.from_major("10.00", "USD")
    >>> price_2 = Money.from_major("15.00", "USD")
    >>> price_3 = Money.from_major("10.00", "USD")

    >>> unique_prices = {price_1, price_2, price_3}
    >>> len(unique_prices)
    2

Design guarantees
-----------------

Data Integrity & Representation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* **Strict Minor-Unit Invariant:** A ``Money`` object is guaranteed to hold an amount
  that can be expressed *exactly* in the currency's minor units. It is impossible
  for a ``Money`` instance to hide fractional minor units.
* **Zero Floating-Point Tolerance:** pycents strictly forbids the use of Python's
  float type both internally and at the API boundary.
  All amounts are backed by exact numeric types (int and Decimal),
* **Immutability and Thread-Safety:** Both ``Money`` and ``UnroundedMoney`` are strictly
  immutable. Modifying an amount always returns a new instance, making ``pycents``
  inherently thread-safe and safe to share across asynchronous boundaries or cache.

Mathematical Correctness
^^^^^^^^^^^^^^^^^^^^^^^^

* **Algebraic Consistency:** Addition and subtraction are mathematically exact;
  the set of ``Money`` values forms a commutative group under addition ``(Money, +)``.
* **Identity Preservation:** Sub-Unit arithmetic operations (multiplication and
  division) preserve standard algebraic identities, such as:

  - ``(money * a) * b == money * (a * b)``
  - ``((money / a) * a).round() == money``

  *Provided the operands remain within the practical precision limits of Python's
  active ``Decimal`` context.*
* **No Implicit Intermediate Rounding:** Sub-unit operations immediately yield an
  ``UnroundedMoney`` instance. Precision is retained indefinitely until the developer
  makes an explicit decision to call ``.round()``.

Runtime & Type Safety (Fail-Fast)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* **Strict Currency Isolation:** Adding, subtracting,
  or comparing amounts of different currencies is prohibited.
  Any such attempt immediately raises a ``CurrencyMismatchError``.
* **Protection against precision loss:** Attempting to create a ``Money`` instance
  from a high-precision decimal (e.g., ``Money.from_major("10.125", "USD")``) without
  explicitly providing a ``RoundingMode`` will raise a ``ValueError`` rather than
  silently guessing the rounding strategy.
* **Static Type Enforcement:** The API heavily leverages Python's type hinting to
  reject unsafe types (like ``float``) at the static analysis level, ensuring tools
  like ``mypy`` or ``pyright`` catch errors before runtime.
