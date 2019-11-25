"""
Text styles for the Gamma visualization library
"""

import logging
import sys
from abc import ABC
from typing import TextIO

from ._viz import DrawStyle

log = logging.getLogger(__name__)

__all__ = ["TextStyle"]


class TextStyle(DrawStyle, ABC):
    """
    Plain text drawing style.

    :param width: the maximum width available to render the text, defaults to 80
    :param out: the output stream this style instance writes to, or `stdout` if \
      `None` is passed (defaults to `None`)
    """

    def __init__(self, out: TextIO = None, width: int = 80, **kwargs) -> None:
        super().__init__(**kwargs)

        if width <= 0:
            raise ValueError(
                f"arg width expected to be positive integer but is {width}"
            )
        self._out = sys.stdout if out is None else out
        self._width = width

    def _drawing_start(self, title: str) -> None:
        """
        Write the title to :attr:`.out`.
        """
        print(title, file=self.out)

    @property
    def out(self) -> TextIO:
        """
        The output stream this style instance writes to.
        """
        return self._out

    @property
    def width(self) -> int:
        """
        The maximum width of the text to be produced.
        """
        return self._width
