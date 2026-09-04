==========
Formatting
==========

In this section we'll dive deep into how ``PyCents`` formatting works.

All formatting is routed through the ``formatting`` module. By default,
``PyCents`` uses a locale-agnostic global formatter that produces consistent,
predictable output regardless of the host machine's environment.

You can format a ``Money`` object in two ways: indirectly via Python's built-in
string interpolation, or directly through the formatting API.

The Quick Way: String Interpolation
-----------------------------------
Because ``PyCents`` tightly integrates with Python's formatting protocol,
the most idiomatic way to display money is using standard f-strings.

.. code-block:: python

    >>> from pycents import Money

    >>> mny = Money.from_major("-2.99", "USD")
    >>> f"{mny}"
    '-USD\xa02.99'
    >>> f"{mny:ha}"
    '(2.99)'

.. tip::
    For a complete breakdown of the Format Specificatin grammar,
    please refer to the :ref:`Format Specification Grammar <format-specification>`..

Under the Hood: The Direct API
------------------------------
When you use an f-string, Python implicitly calls ``formatting.format()`` under the hood.
For advanced use cases, you can call this function directly.

.. code-block:: python

    >>> from pycents import Money, formatting

    >>> mny = Money.from_major("-2.99", "USD")
    >>> result = formatting.format(mny, "a")
    >>> result
    '(USD\xa02.99)'

The Global Formatter
--------------------
By default, the ``format`` function delegates the rendering to a globally configured formatter.
The formatting is orchestrated by the ``MoneyFormatter`` class, which is responsible for
parsing the format specification string and handing over the data to the backend formatter,
which will display the final result.

``PyCents`` ships with three fully implemented backend formatters. ``StdFormatter`` which
is a locale-agnostic formatter (the default), ``BabelFormatter`` which, as its name suggests
use ``babel`` library as backend to format money, and ``IcuFormatter`` which uses the ``PyIcu``
library.

Choosing a backend formatter is a matter of calling a simple function ``use_backend``:

.. code-block:: python

    from pycents import Money, formatting
    formatting.use_backend('babel') # Other options are 'std' (the default) and 'icu'.

    mny = Money.from_major("-2.99", "USD")
    print(f"{mny:a}") # Output: ($2.99)

.. note::

    ``babel`` and ``pyicu`` are provided as optional dependencies, installing ``PyCents``
    will not install those libraries, you must install them separately.

You can inspect the currently available backend formatters by calling
``formatting.available_backends()``.

.. code-block:: python

    >>> from pycents import formatting
    >>> backends = formatting.available_backends()
    ['babel', 'icu', 'std']

When you enable the ``babel`` or ``icu``, the backend
automatically detects your system's default locale to format the output appropriately.

If you need to explicitly set a global default locale for your application, use ``basicConfig``:

.. code-block:: python

    from pycents import formatting

    # Set the global backend and locale
    formatting.use_backend('babel')
    formatting.basicConfig(locale='fr_FR')

You can also customize the numbering system used for currency formatting
by passing the ``numbering_system`` argument to ``basicConfig``.

.. code-block:: python

    from pycents import formatting

    # Configure locale and a specific numbering system
    formatting.use_backend('babel')
    formatting.basicConfig(locale='ar_EG', numbering_system='arab')

.. note::
    **Babel Limitation:** When using the ``babel`` backend, changing the
    ``numbering_system`` will only affect the decimal and grouping symbols
    (such as commas and periods). It does not translate the actual numeric digits.
    If your application requires full digit localization, we recommend using the ``icu``
    backend instead.

Global Configuration
--------------------

Every backend formatter in ``PyCents`` possesses a ``default_spec``.
This specification is used whenever a ``Money`` object is formatted without explicit
formatting fields (e.g., ``format(mny, "")`` or ``f"{mny}"``).

You can globally override this default behavior whenever you want to enforce
a specific formatting mode (like compact notation or accounting) across your entire
application by calling ``configure()`` on the active backend.

.. code-block:: python

    from pycents import formatting

    # Configure the global default: use compact notation with 2 decimal places
    formatting.get_formatter().configure(compact=True, compact_precision=2)

    # You may also choose a rounding mode that will be applied in compact notation
    formatting.get_formatter().configure(rounding=RoundingMode.HALF_UP)

    # Now, all empty format specs will use this configuration globally
    mny = Money.from_major("1500000", "USD")
    print(f"{mny}")  # Outputs: $1.50M

.. warning::
    **Thread Safety and Global State**

    ``use_backend()``, ``basicConfig()`` and ``configure()`` mutate the global formatting state.
    They are designed to be called **exactly once** during application startup.

    **Never call these methods dynamically at runtime**
    Modifying the global configuration inside an active thread will cause race conditions,
    immediately overriding the formatting rules for all other concurrent users.

Handling Dynamic Runtime Formatting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you need to change formatting dynamically based on a runtime context,
do not mutate the global default. Instead, use the inline format specification grammar
in your f-strings or use the ``local_format`` context manager.

The ``local_format`` context manager allows you to temporarily override formatting settings,
such locale, numbering_system, precision, or compact notation for a specific block of code.
Once the block exits, the original global settings are seamlessly restored.

.. code-block:: python

    from pycents import Money, RoundingMode
    from pycents.formatting import local_format

    price = Money.from_major(1500000, "USD")

    formatting.use_backend('babel')

    with local_format(locale="de_DE") as fmt:
        fmt.rounding = RoundingMode.HALF_UP
        fmt.compact = True
        fmt.compact_prec = 3

        print(price)             # Outputs: USD 1250.00
        print(f"Total: {price}") # Output: Total: 1,5 Mio. $

Final note
-----------

**PyCents** provides complete implementations for babel and pyicu.
If you need to integrate a proprietary formatting engine, you can write a custom backend
by subclassing the ``pycents.formatting.BaseFormatter`` abstract base class.
We recommend using ``std_formatter.py`` as a reference implementation for creating
a custom backend.
