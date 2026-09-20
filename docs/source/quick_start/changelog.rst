=========
Changelog
=========

All notable changes to this project will be documented in this file.

Version 1.3.0 — 2026-09-20
==========================

Added
-----

Currency
~~~~~~~~

* Added :meth:`Currency.from_country` classmethod to map ISO 3166-1
  country codes to their primary ISO 4217 currencies.

Currency Conversion
~~~~~~~~~~~~~~~~~~~

* Added exchange-rate based currency conversion through
  :meth:`Money.exchange_to`.
* Added the :class:`ExchangeRate` type for representing exchange rates
  between currencies.
* Added :class:`ExchangeRateInfo` for associating provider, rate type,
  timestamp, and additional information with an exchange rate.
* Added the :class:`ExchangeRateProvider` protocol for defining
  exchange-rate providers.
* Added :class:`DefaultProvider` for obtaining exchange rates from
  external providers.
* Added :class:`FixedRateProvider` for supplying and managing fixed
  exchange rates.
* Added support for exchange-rate inversion and cross-rate derivation.
* Added serialization and deserialization of exchange rates, including
  the source lineage of derived rates.
* Added support for selecting the upstream provider used by
  :class:`DefaultProvider`.

Documentation
~~~~~~~~~~~~~

* Added a comprehensive guide for currency conversion and exchange-rate
  providers.
* Documented exchange-rate construction, inversion, cross-rates,
  serialization, and custom providers.
* Expanded the API documentation for the conversion functionality.
* Documented the project's design philosophy and implementation
  principles.

Testing
~~~~~~~

* Added extensive tests for currency conversion and exchange-rate
  providers.
* Expanded test coverage for exchange-rate construction, derivation,
  serialization, and provider behavior.


Version 1.2.0 — 2026-09-03
==========================

I am happy to announce that **PyCents** added support for crypto and
custom currencies.

Features
--------

Custom Currencies
~~~~~~~~~~~~~~~~~

* Added the `Xcy` enum-like class for cryptocurrencies and custom
  currencies.
* Added pre-registered definitions for popular cryptocurrencies.
* Added custom currency registration through `Xcy.register`.
* Integrated custom currencies seamlessly with the locale-aware
  formatting engine.

Money API
~~~~~~~~~~

* Added `as_majors` and `as_minors` properties as the preferred API
  for accessing major and minor unit amounts. The existing
  `to_decimal()` and `minor_units` APIs are deprecated.
* Updated `Money.from_major` to require an explicit rounding mode when
  rounding is necessary.
* Added `from_minor` factory method to construct `Money` instances
  from minor units.
* Promoted `UnroundedMoney` to a public API type for representing
  intermediate, high-precision monetary calculations.
* Added `UnroundedMoney.from_major()` for constructing unrounded
  amounts from major currency units. The existing
  `UnroundedMoney.from_decimal()` API is deprecated.
* Added `as_majors` property to `UnroundedMoney` to access the stored
  monetary amount in major units.

Documentation
~~~~~~~~~~~~~~

* Improved the documentation and added a guide for using custom
  currencies.

Version 1.1.0 — 2026-08-21
==========================

Features
--------

* Added ``cash`` method to the ``Money`` class to support physical cash
  transactions.

Version 1.0.0 — 2026-08-16
==========================

Initial stable production release. PyCents public API is frozen and fully
covered by tests.
