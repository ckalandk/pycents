===================
Currency Conversion
===================

Currency conversion in PyCents is built around the
:class:`~pycents.conversion.ExchangeRate` class. An exchange rate that
drives every currency conversion.

Before discussing exchange-rate providers, it is useful to understand
``ExchangeRate`` itself.

The ExchangeRate Class
======================

An ExchangeRate represents a specific exchange-rate observation.
In order to identify that observation, the following information is essential:

* base currency — the currency being priced.
* quote currency — the currency in which the price is expressed.
* timestamp or date — when the rate was listed or otherwise associated with the observation.
* rate type — the kind of rate being represented, such as a reference rate,
  mid-market rate, bid rate, or ask rate.

These four pieces of information form the identity of the rate observation.

PyCents explicitly maps these details into the ``ExchangeRate`` dataclass.
The ``base``, ``quote``, and decimal ``rate`` properties handle the raw conversion math.
The metadata—like the timestamp, provider, and rate type is bundled together
into the ``info`` attribute using an ``ExchangeRateInfo`` object.

For reference we expose here a simplified version of both classes:

.. code-block:: python

    @dataclass
    class ExchangeRate:
        base: Currency
        quote: Currency
        rate: Decimal
        info: ExchangeRateInfo | None

.. code-block:: python

    @dataclass
    class ExchangeRateInfo:
        provider: str
        ratetype: str
        asof: date | datetime
        metadata: Mapping[str, Any]

.. note::

    ``ExchangeRate`` instances are immutable and can therefore be safely
    shared between threads.

ExchangeRate Information and Metadata
-------------------------------------

Given the provider, base currency, quote currency, timestamp, and rate type,
the rate should be identifiable and, in principle, obtainable again from the provider.

For example:

.. code-block:: text

    Provider:    ECB
    Base:        EUR
    Quote:       USD
    Timestamp:   2026-09-11
    Rate type:   reference rate

Together, these identify the particular EUR/USD reference rate published by the ECB
for that observation.

Metadata
~~~~~~~~

``ExchangeRateInfo.metadata`` is intended for additional information that is relevant
to the specific rate observation.

As a rule of thumb:

Metadata should contain information that is essential for reconstructing the ExchangeRate,
or that are meaningfully associated with the rate obsevation.

Metadata should therefore not be used as a general-purpose dump of information exposed
by the provider.

For example, metadata may contain:

.. code-block:: text

    {
        "source_url": "...",
        "raw_response": "...",
        "market": "...",
        "instrument": "...",
    }

On the other hand, provider information that does not contribute to identifying or
reconstructing the observation should generally not be stored in ``ExchangeRateInfo.metadata``.
Those belong to provider-level information rather.

Cross Exchange Rate & Rate Inversion
------------------------------------

Before reading this section, readers are advised to read
`Cross Exchange Rate: Formula, Quote Inversion & Bid-Ask Construction <https://ryanoconnellfinance.com/fx-cross-rates/>`_,
which provides a concise explanation of quote inversion and cross-rate
calculation.

The terminology used here follows that article. A **vehicle/pivot currency**,
is the currency shared by the two exchange rates used to derive a cross rate.
For example, in EUR/USD and USD/CAD, USD is the vehicle/pivot currency and the
resulting cross rate is EUR/CAD.

In Pycents, two operations are particularly
important:

* Inversion changes the direction of a rate. If a rate represents
  A/B, its inverse represents B/A and its numerical value is the
  reciprocal.
* Cross-rate derivation combines two compatible rates through a
  common vehicle/pivot currency. For example,

.. math::

    EUR/USD \times USD/CAD = EUR/CAD

when the pair orientations are compatible.

Pycents provides these operations directly on :class:`ExchangeRate`.

Inverting a rate
~~~~~~~~~~~~~~~~

An :class:`ExchangeRate` can be inverted with :meth:`ExchangeRate.invert`:

.. code-block:: python

    from pycents.conversion import ExchangeRate
    from decimal import Decimal

    eur_usd = ExchangeRate.from_string("EUR/USD = 1.1516")
    usd_eur = rate.invert()

    assert usd_eur.base.ccy_code == "USD"
    assert usd_eur.quote.ccy_code == "EUR"
    assert usd_eur.rate == 1 / eur_usd.rate

    assert usd_eur.info == eur_usd.info

If rate represents EUR/USD, inverse represents USD/EUR.
The numerical rate is the reciprocal of the original rate.

Inversion also preserves the information attached to the original
``ExchangeRate`` unchanged. This includes its :attr:`ExchangeRate.info`,
if present.

This behavior might be indesirable when the ratetype of
the rate being inversed is a *bid* or *ask*. Pycents does not assign any predefined
meaning to ratetype. A provider may use values such as "bid",
"ask", "mid", or "blended", but these values are opaque to
``ExchangeRate``. Consequently, :meth:`ExchangeRate.invert` does not
attempt to interpret or modify ratetype, it just perform a dumb mathematical
inversion!

When working with market bid/ask quotes, ``invert()`` should not be
used as a way to obtain the corresponding inverse market quote.

For a two-sided FX quote, the bid and ask sides are reversed when the
quote is inverted:

.. math::

    (A/B)_{bid}^{-1} = (B/A)_{ask}

    \qquad

    (A/B)_{ask}^{-1} = (B/A)_{bid}

In practice, users working with bid/ask data should therefore request
the appropriate quote from their provider rather than blindly calling
:meth:`ExchangeRate.invert`. Alternatively, you can include the
information needed to construct the inverse rate when retrieving the rate.

For example, a provider could return:

.. code-block:: text

    USD/EUR bid = 0.8557
    USD/EUR ask = 0.8552

You could then construct the rate as follow:

.. code-block:: python

    rate = ExchangeRate(
        Currency.from_code("USD"),
        Currency.from_code("EUR"),
        Decimal('0.8557'),
        info = ExchangeRateInfo(
            provider="FastForex",
            ratetype="bid",
            metadata={"ask": Decimal('0.8552')},
        )
    )

Notice how we retained the corresponding ask needed for correct financial inversion.

Then, rather than doing:

.. code-block:: python

    inverse = rate.invert()

You can use the stored counterpart directly:

.. code-block:: python

    from pycents.conversion import ExchangeRate, ExchangeRateInfo

    inverse = ExchangeRate.from_pair(
        "EUR",
        "USD",
        1 / rate.info.metadata["ask"], # Or 1 / rate.info.ask
        info=ExchangeRateInfo(
            provider=rate.info.provider,
            ratetype="bid",
            metadata={
                "ask": Decimal(1) / rate.rate,
            },
        )
    )

Cross-rate derivation
~~~~~~~~~~~~~~~~~~~~~

Two compatible :class:`ExchangeRate` objects can be multiplied to
derive a cross rate.

For example, given:

.. code-block:: python

    eur_usd = ...
    usd_cad = ...

multiplying them gives the corresponding EUR/CAD rate:

.. code-block:: python

    eur_cad = eur_usd * usd_cad

The multiplication is valid when the two rates are compatible: the
quote currency of the first rate must match the base currency of the
second. Thus:

Note that the resulting rate is a derived rate and does not carry the information
of either source rate. Its :attr:`ExchangeRate.info` is therefore
`None`.

Inspecting the derivation
~~~~~~~~~~~~~~~~~~~~~~~~~

Although a cross-derived rate has no attached information, its
construction can still be inspected through the :attr:`ExchangeRate.lineage`
property.

``lineage`` returns a tuple containing the :class:`ExchangeRate` objects
used to derive the rate. Note however that the sources are returned as
a flattened lineage, rather than as a tree of intermediate derivations.

.. code-block:: python

    # Assuming here that eur_usd, usd_cad and cad_jpy
    # are obtained directly from a provider and we need
    # to cross-derive eur_jpy
    eur_cad = eur_usd * usd_cad
    eur_jpy = eur_cad * cad_jpy

    eur_jpy.lineage
    # (eur_usd, usd_cad, cad_jpy)

This makes it possible to trace a derived rate back to the rates from
which it was calculated.

Pycents also provides :meth:`ExchangeRate.is_cross` to determine whether
a rate was obtained through cross-rate derivation:

.. code-block:: python

   eur_cad.is_cross()
   # True

Combining rate inversion and cross-rate derivation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to derive a rate between two non-vehicule currencies,
that are both quoted against the same base currency: for example assuming you already have
USD/EUR and USD/CAD and you want to derive EUR/CAD. To get the EUR/CAD rate
you need to multiply the inverse rate of the USD/EUR by the USD/CAD:

.. code-block:: python

    usd_eur = ...
    usd_cad = ...

    eur_cad = usd_eur.invert() * usd_cad

Serializing and deserializing exchange rates
--------------------------------------------

:class:`ExchangeRate` provides :meth:`ExchangeRate.as_dict` and
:meth:`ExchangeRate.from_dict` for converting an exchange rate to and
from a dictionary representation.

This is useful when exchange rates need to be stored or transmitted.

To serialize an exchange rate:

.. code-block:: python

    data = rate.as_dict()

For example:

.. code-block:: python

    {
        'base': 'EUR',
        'term': 'USD',
        'rate': '1.1515',
        'info': {
            'provider': 'ECB',
            'ratetype': 'reference',
            'timestamp': '2026-09-19',
            }
    }

The exchange rate can later be reconstructed with:

.. code-block:: python

    restored = ExchangeRate.from_dict(data)

The resulting object contains the same currencies, rate, and associated
information as the original.

For storage or transmission as JSON, the mapping returned by
:meth:`ExchangeRate.as_dict` can be passed to the standard :mod:`json`
module:

.. code-block:: python

    import json

    data = rate.as_dict()

    with open("rate.json", "w") as file:
        json.dump(data, file, indent=2)

The rate can then be restored with:

.. code-block:: python

    with open("rate.json") as file:
        data = json.load(file)

    rate = ExchangeRate.from_dict(data)


Cross-derived rates
~~~~~~~~~~~~~~~~~~~

When an :class:`ExchangeRate` was obtained through cross-rate derivation,
its source rates are included in the serialized representation under
``"sources"``. The complete derivation lineage is therefore preserved
and reconstructed when the rate is deserialized.

For example, a cross-derived rate such as:

.. code-block:: python

   eur_cad = eur_usd * usd_cad

is serialized together with the source rates used to derive it.

.. note::

   ``ExchangeRate.as_dict()`` returns a mapping suitable for
   serialization, but it does not impose JSON restrictions on
   :attr:`ExchangeRateInfo.metadata`. If metadata contains objects that
   are not supported by JSON, a custom serialization strategy is needed
   for those values.

Constructing an ExchangeRate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An :class:`ExchangeRate` can be constructed directly from its components,
or with one of the convenience constructors.

The :meth:`ExchangeRate.from_pair` class method accepts a currency pair in
"BASE/QUOTE" form and the corresponding exchange-rate factor:

.. code-block:: python

    from decimal import Decimal

    rate = ExchangeRate.from_pair("USD/EUR", "0.875")
    rate = ExchangeRate.from_pair("USD/EUR", Decimal("0.875"))

The currencies are validated and converted to :class:`Currency` instances automatically.

An optional :class:`ExchangeRateInfo` can be supplied to associate context with the rate:

.. code-block:: python

    rate = ExchangeRate.from_pair(
        "USD/EUR",
        "0.875",
        info=ExchangeRateInfo(...),
    )

For a compact string representation, use :meth:`ExchangeRate.from_string`:

.. code-block:: python

    rate = ExchangeRate.from_string(
        "USD/EUR=0.875",
        info=ExchangeRateInfo(...) # Optional
    )

This is useful, for example, when constructing an exchange rate from a string read from a file.

Both = and : are accepted as separators, as well as whitespace:

.. code-block:: python

    ExchangeRate.from_string("USD/EUR = 0.875")
    ExchangeRate.from_string("USD/EUR: 0.875")
    ExchangeRate.from_string("USD/EUR 0.875")

Exchange Rate Provider:
=======================

In pycents, an exchange-rate provider is any object that implements
the :class:`ExchangeRateProvider` protocol.

The provider is responsible for obtaining an ``ExchangeRate`` for a given pair of currencies.
It may obtain rates from a remote service, a local database, a file, or any other source.

The :class:`ExchangeRateProvider` protocol defines the interface that providers must implement:

.. code-block:: python

    class ExchangeRateProvider(Protocol):
        def get_rate(
            self,
            base: Currency,
            quote: Currency,
            /,
            *,
            asof: date | None = None,
            **kwargs: Any,
        ) -> ExchangeRate:
            ...

pycents ships with two providers: :class:`FixedRateProvider`, which stores rates locally,
and :class:`DefaultProvider`, which obtains rates from an external source.

FixedRateProvider class
-----------------------

Create a provider and optionally give it a name:

.. code-block:: python

    from pycents.conversion import FixedRateProvider

    fixed_rates = FixedRateProvider("My Rates")

Rates can be added directly using a currency pair and rate:

.. code-block:: python

    fixed_rates.add_rate("EUR", "USD", "1.1515")
    fixed_rates.add_rate("EUR", "CAD", "1.8188")

Alternatively, an existing :class:`ExchangeRate` can be added:

.. code-block:: python

    fixed_rates.add_rate(
        ExchangeRate.from_pair("EUR/USD", "1.1515")
    )

This can be useful when rates are stored in a file. For example, suppose rates.txt contains:

.. code-block:: text

    EUR/USD=1.1515
    EUR/CAD=1.8188
    GBP/USD=1.3472

The rates can be loaded into the provider as follows:

.. code-block:: python

    with open("rates.txt") as file:
        for line in file:
            if line.strip():
                fixed_rates.add_rate(ExchangeRate.from_string(line))

Once populated, the provider can be passed to :meth:`Money.exchange_to`:

.. code-block:: python

    money = Money.from_major("100", "EUR")
    converted = money.exchange_to("USD", provider=fixed_rates)

FixedRateProvider uses the rates exactly as supplied. It does not fetch rates from an
external service or derive missing rates through inversion or cross-rate calculations.

`DefaultProvider`
-----------------

:class:`DefaultProvider` retrieves exchange-rate data through the `Frankfurter API`_.
By default, it uses the European Central Bank (ECB) as its upstream provider.

This is the provider used automatically by :meth:`Money.exchange_to` when no provider is supplied:

.. code-block:: python

    money.exchange_to("USD")


This is equivalent to explicitly creating a `DefaultProvider` configured to use the ECB:

.. code-block:: python

    provider = DefaultProvider("ECB")
    money.exchange_to("USD", provider=provider)

Choosing an upstream provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The upstream provider can be selected when constructing ``DefaultProvider``.
Frankfurter supports multiple upstream providers; the complete list, including
the provider keys required by the API, is available from its `provider list`_.

For example:

.. code-block:: python

    provider = DefaultProvider("AMCM")

The provider key must be supplied when selecting an upstream provider.

Using Frankfurter's default provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The upstream provider is optional:

.. code-block:: python

    provider = DefaultProvider()

In this case, `DefaultProvider` does not select a specific upstream provider.
Instead, Frankfurter determines the source of the rates. Frankfurter returns a
blended rate in this case.

Rate derivation
~~~~~~~~~~~~~~~

Frankfurter itself supports operations such as rate inversion and cross-rate
derivation. ``DefaultProvider``, however, does not rely on Frankfurter to
perform these operations.

Instead, ``DefaultProvider`` retrieves the available rates and performs
inversion and cross-rate derivation itself. This keeps these operations under
the control of ``pycents`` and allows the resulting :class:`ExchangeRate` to
retain its derivation information.

.. _Frankfurter API: https://api.frankfurter.dev/
.. _provider list: https://api.frankfurter.dev/v2/providers

Writing a Custom Provider
-------------------------

To create a custom exchange-rate provider, implement the
:class:`ExchangeRateProvider` protocol.

The protocol intentionally has a minimal interface: a provider must implement
only :meth:`ExchangeRateProvider.get_rate`.

For a complete example of a provider implementation, see the
:class:`DefaultProvider` source code.
