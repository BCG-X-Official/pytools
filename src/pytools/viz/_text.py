"""
Text styles for the GAMMA visualization library.
"""

import logging
import sys
from abc import ABCMeta
from typing import Optional, TextIO

from ..api import AllTracker, inheritdoc
from ._viz import DrawingStyle

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = ["TextStyle"]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


@inheritdoc(match="[see superclass]")
class TextStyle(DrawingStyle, metaclass=ABCMeta):
    """
    Base class of drawing styles producing plain text output.
    """

    #: The output stream this style instance writes to.
    out: TextIO

    #: The maximum width of the text to be produced.
    width: int

    def __init__(self, out: Optional[TextIO] = None, width: int = 80, **kwargs) -> None:
        """
        :param width: the maximum width available to render the text, defaults to 80
        :param out: the output stream this style instance writes to
            (defaults to :obj:`sys.stdout`)
        """

        super().__init__(**kwargs)

        if width <= 0:
            raise ValueError(
                f"arg width expected to be positive integer but is {width}"
            )
        self.out = sys.stdout if out is None else out
        self.width = width

    @classmethod
    def get_default_style_name(cls) -> str:
        """[see superclass]"""
        return "text"

    def start_drawing(self, title: str, **kwargs) -> None:
        """
        Write the title to :attr:`.out`.

        :param title: the title of the drawing
        """
        print(f"{f' {title} ':*^{self.width}s}", file=self.out)


__tracker.validate()
