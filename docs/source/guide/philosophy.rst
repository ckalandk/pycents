==================
PyCents Philosophy
==================

PyCents follows the principles of :pep:`20` and favors simple, explicit,
readable Python.

In particular:

* Beautiful is better than ugly.
* Explicit is better than implicit.
* Simple is better than complex.
* Complex is better than complicated.
* Readability counts.

These principles guide the design of the library:

* Convenience at the boundaries; invariants in the core.

Core constructors accept only the strong, canonical types on which the
internal invariants depend. Convenience methods may accept more convenient
representations, such as strings, but their role is only to validate and
convert those values before delegating to the core constructor. This keeps
construction logic in one place and makes the core types the gateway through
which valid objects are created.

* Don't invent abstractions when Python already has a good one.

Prefer the standard library and established Python idioms over custom
abstractions when they already solve the problem well.

* Prefer familiarity over novelty.

When an established Python design fits the problem, use it. Familiar
interfaces make a library easier to understand, use, and maintain.

* Rely on the type checker

Use static typing to enforce as much of the API contract as possible.
Add runtime validation only where it is necessary to enforce constraints
that cannot be expressed or reliably enforced by the type system,
particularly at public boundaries where inputs may come from untyped sources.
