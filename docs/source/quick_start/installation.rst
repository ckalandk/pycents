============
Installation
============

PyCents supports Python **3.12** and later.

The core package has minimal dependencies and requires typing_extensions
for Python 3.12 compatibility.

Install from PyPI
-----------------

.. code-block:: bash

    pip install pycents


Optional formatting backends
----------------------------

PyCents provides a locale agnostic lightweight core implementation for formatting money.
Locale-aware currency formatting is available through optional formatting backends.

You can install the backends individually or install all of them at once.

Babel
^^^^^

To use the ``babel`` backend

.. code-block:: bash

    pip install babel

Or if you want to install both pycents and babel at once

.. code-block:: bash

    pip install pycents[babel]

ICU (PyICU)
^^^^^^^^^^^

To use the ICU formatting backend:

.. code-block:: bash

    pip install pyicu

PyICU is a Python extension module that wraps the ICU C++ libraries. Unlike
Babel, installing PyICU may require additional platform-specific steps,
particularly on Windows and some Linux distributions.

Both backends
^^^^^^^^^^^^^

To install both locale-aware formatting backends:

.. code-block:: bash

    pip install "pycents[i18n]"

The i18n extra installs PyCents along Babel and PyICU.

.. note::

    The examples above use ``pip``. The same PyCents extras can be used with
    other Python package managers. For example, with ``uv``:

    .. code-block:: bash

        uv add "pycents[babel]"
        uv add "pycents[pyicu]"
        uv add "pycents[i18n]"


Installing PyICU
----------------

PyICU is more difficult to install than Babel because it contains native
code and depends on the ICU libraries.

Linux
^^^^^

On many Linux distributions, PyICU can be installed directly from the
distribution's package manager.

For Debian/Ubuntu:

.. code-block:: bash

    sudo apt install python3-icu

Alternatively, if you want PyICU installed into your Python environment,
install the ICU development libraries first:

.. code-block:: bash

    sudo apt install pkg-config libicu-dev
    pip install PyICU

Other Linux distributions provide PyICU and/or ICU through their respective
package managers. Consult your distribution's package documentation if the
commands above do not apply.

Windows
^^^^^^^

PyICU can be more difficult to build from source on Windows because it is a
native extension that depends on ICU.

Pre-built Windows wheels are available from the
`cgohlke/pyicu-build GitHub repository <https://github.com/cgohlke/pyicu-build/releases>`_.

Download the wheel corresponding to your Python version and architecture.

For example:

.. code-block:: text

    cp312 = CPython 3.12
    cp313 = CPython 3.13
    win_amd64 = 64-bit Windows
    win_arm64 = ARM64 Windows
    win32 = 32-bit Windows

For a 64-bit CPython 3.12 installation, you would select a wheel similar to:

.. code-block:: text

    pyicu-<version>-cp312-cp312-win_amd64.whl

Then install the downloaded wheel:

.. code-block:: bash

    pip install path\to\pyicu-<version>-cp312-cp312-win_amd64.whl

.. note::

    The wheel must match both your Python version and Windows architecture.
    You can check your Python version with ``python --version`` and your
    interpreter architecture with:

    .. code-block:: bash

        python -c "import platform; print(platform.architecture()[0])"

You can verify the core installation with:

.. code-block:: bash

    python -c "import pycents; print(pycents.__version__)"

If you installed an optional formatting backend, you can also verify its
availability by importing it directly:

.. code-block:: bash

    python -c "import babel; print(babel.__version__)"

or:

.. code-block:: bash

    python -c "import icu; print(icu.ICU_VERSION)"

Next steps
----------

Continue with the :doc:`quickstart`.
