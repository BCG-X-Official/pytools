"""
Configuration file for the Sphinx documentation builder.

Receives majority of configuration from pytools conf_base.py
"""

import os
import sys

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            os.pardir,
            os.pardir,
            os.pardir,
            "pytools",
            "sphinx",
            "base",
        )
    ),
)

from conf_base import set_config

# ----- custom configuration -----

set_config(
    globals(),
    project="pytools",
    modules=["pytools"],
    html_logo="_static/gamma_pytools_logo.png",
)
