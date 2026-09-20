# Contributing

Thank you for your interest in contributing to PyCents.

## Getting Started

Clone the repository:

```bash
git clone https://github.com/ckalandk/pycents.git
cd pycents
```

PyCents uses [uv](https://docs.astral.sh/uv/) for dependency management.
Sync the development environment with all optional dependencies:

```bash
uv sync --all-extras
```

On Windows, **PyICU must be installed manually**. See the
[installation guide](https://pycents.readthedocs.io/en/latest/quick_start/installation.html)
for instructions.

## Running Tests

Run the test suite with:

```bash
uv run pytest -v -m "not slow"
```

This is the recommended command for normal development.

Some Babel and PyICU tests run across all available locales and can take
considerably longer. These tests are marked as `slow` and should only be run
occasionally.

To run the complete test suite:

```bash
uv run pytest -v
```

## Before Contributing

Please read the
[PyCents philosophy](https://pycents.readthedocs.io/en/latest/guide/philosophy.html)
before making changes. It describes the principles that guide the design and
implementation of the project.

That's it. Keep changes focused, simple, and consistent with the existing
codebase.
