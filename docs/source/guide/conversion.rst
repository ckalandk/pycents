===================
Currency Conversion
===================

ExchangeRate Information and Metadata
=====================================

An ExchangeRate represents a specific exchange-rate observation.
In order to identify that observation, the following information is essential:

* base currency — the currency being priced.
* quote currency — the currency in which the price is expressed.
* timestamp — when the rate was listed or otherwise associated with the observation.
* rate type — the kind of rate being represented, such as a reference rate,
  mid-market rate, bid rate, or ask rate.

These four pieces of information form the identity of the rate observation.

Conceptually:

Given the provider, base currency, quote currency, timestamp, and rate type,
the rate should be identifiable and, in principle, obtainable again from the provider.

For example:

Provider:    ECB
Base:        EUR
Quote:       USD
Timestamp:   2026-09-11
Rate type:   reference rate

Together, these identify the particular EUR/USD reference rate published by the ECB
for that observation.

Metadata
--------

ExchangeRateInfo.metadata is intended for additional information that is relevant
to reproducing or understanding the specific rate observation.

As a rule of thumb:

Metadata should contain information that is essential for reconstructing the ExchangeRate,
or that meaningfully facilitates its reconstruction.

Metadata should therefore not be used as a general-purpose dump of information exposed
by the provider.

For example, metadata may contain:

{
    "source_url": "...",
    "series_code": "...",
    "market": "...",
    "instrument": "...",
}

when such information is necessary to identify the exact provider data series or
makes it significantly easier to retrieve the same observation again.

On the other hand, provider information that does not contribute to identifying or
reconstructing the observation should generally not be stored in ExchangeRateInfo.metadata.
Examples include a provider's complete list of supported currencies, publication history,
or other general characteristics of the provider.

Those belong to provider-level information rather than to the individual ExchangeRate.

Provider Information vs. Rate Information

It is useful to distinguish between two different questions:

Provider information:

What is this provider or dataset?

Exchange-rate information:

Which exact observation does this ExchangeRate represent, and what information is needed to reproduce it?

For example, a provider may have general information such as its name, supported currencies, or historical coverage. Such information describes the provider, not a particular exchange-rate observation.

By contrast:

base
quote
timestamp
rate type

identify the individual observation and therefore belong directly to the ExchangeRate and its associated ExchangeRateInfo.

Why this distinction matters

Different providers may publish multiple rates for the same currency pair and date. For example:

USD/EUR — 2026-09-11

bid        = ...
ask        = ...
mid-market = ...

The base currency, quote currency, and timestamp alone would therefore not uniquely identify the observation. The rate type is also required.

Likewise, some providers may require additional provider-specific information to identify the exact data series. Such information is an appropriate use of metadata.

The goal is not to store everything that the provider tells us. The goal is to preserve enough information to answer:

"What exact rate is this, and how could I obtain the same rate again?"

This keeps ExchangeRate self-contained while avoiding unnecessary duplication of provider-level information.
