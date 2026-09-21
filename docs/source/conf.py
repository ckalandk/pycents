# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import re
import sys
from pathlib import Path

html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "/")


root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "src"))

project = "PyCents"
copyright = "2026, Khaled Kessoum"
author = "Khaled Kessoum"

# Copied verbatim from hypothesis conf.py
_d = {}
_init_file = root.joinpath("src", "pycents", "__init__.py")

init_content = _init_file.read_text(encoding="utf-8")

version_match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init_content, re.M)

if version_match:
    version = version_match.group(1)
    release = version
else:
    raise RuntimeError("Unable to find __version__ string in pycents/__init__.py")

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx_design",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

# Napoleon settings for Google Style
napoleon_google_docstring = True
napoleon_numpy_docstring = False

# Optional: Tell Napoleon to use Sphinx's nice "admonition" styling
# for Note and Warning blocks in your docstrings.
napoleon_use_admonition_for_notes = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
}

autodoc_member_order = "bysource"
autosummary_generate = True
templates_path = ["_templates"]
exclude_patterns = []

html_theme = "furo"

html_theme_options = {
    "light_logo": "logo-light.svg",
    "dark_logo": "logo-dark.svg",
}

html_static_path = ["_static"]
