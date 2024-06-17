"""
Implementation of ``is_running_in_notebook``.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

__all__ = [
    "is_running_in_notebook",
]


def is_running_in_notebook() -> bool:
    """
    Check if the code is running in a notebook like Jupyter or Colab.

    Useful to determine whether to display plots inline or not.

    :return: whether the code is running in a Jupyter notebook
    """
    # make sure we're in a proper notebook, not running from a shell
    try:
        # get the shell
        # noinspection PyUnresolvedReferences
        shell: str = get_ipython().__class__.__name__  # type: ignore[name-defined]

        # check if we're in a notebook
        return shell == "ZMQInteractiveShell"
    except NameError:
        # check for the presence of the "google.colab" module
        try:
            # noinspection PyUnresolvedReferences
            import google.colab  # noqa: F401

            return True
        except ImportError:
            # we're not in a notebook
            return False
