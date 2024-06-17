"""
Implementation of ``HTMLStyle``.
"""

from __future__ import annotations

import logging
import sys
from abc import ABCMeta
from io import StringIO
from typing import Any, Generic, TextIO, TypeVar, cast

from ..api import appenddoc, inheritdoc
from ._notebook import is_running_in_notebook
from ._viz import ColoredStyle
from .color import ColorScheme, RgbColor

log = logging.getLogger(__name__)

__all__ = [
    "HTMLStyle",
]
#
# Type variables
#

T_ColorScheme = TypeVar("T_ColorScheme", bound=ColorScheme)


#
# Classes
#


@inheritdoc(match="[see superclass]")
class HTMLStyle(ColoredStyle[T_ColorScheme], Generic[T_ColorScheme], metaclass=ABCMeta):
    """
    Abstract base class for styles for rendering output as HTML.

    Supports color schemes, and is able to display output in a notebook (if running in
    one), ``stdout``, or a given output stream.
    """

    #: The output stream this style instance writes to; or ``None`` if output should
    #: be displayed in a Jupyter notebook
    out: TextIO | None

    #: Whether the output should be displayed in a Jupyter notebook
    _send_to_notebook: bool = False

    @appenddoc(to=ColoredStyle.__init__)
    def __init__(
        self, *, colors: T_ColorScheme | None = None, out: TextIO | None = None
    ) -> None:
        """
        :param out: the output stream this style instance writes to; if ``None`` and
            running in a Jupyter notebook, output will be displayed in the notebook,
            otherwise it will be written to ``stdout``
        """
        super().__init__(colors=colors)

        if out is None:  # pragma: no cover
            if is_running_in_notebook():
                self.out = StringIO()
                self._send_to_notebook = True
            else:
                self.out = sys.stdout
                self._send_to_notebook = False
        else:
            self.out = out
            self._send_to_notebook = False

    @classmethod
    def get_default_style_name(cls) -> str:
        """[see superclass]"""
        return "html"

    @staticmethod
    def rgb_to_css(rgb: RgbColor) -> str:
        """
        Convert an RGB color to its CSS representation in the form ``rgb(r,g,b)``,
        where ``r``, ``g``, and ``b`` are integers in the range 0-255.

        :param rgb: the RGB color
        :return: the CSS representation of the color
        """
        rgb_0_to_255 = ",".join(str(int(luminance * 255)) for luminance in rgb)
        return f"rgb({rgb_0_to_255})"

    def start_drawing(self, *, title: str, **kwargs: Any) -> None:
        """[see superclass]"""
        super().start_drawing(title=title, **kwargs)

        # we start a section, setting the colors
        print(
            '<style type="text/css"></style>'
            f'<div style="'
            f"color:{self.rgb_to_css(self.colors.foreground)};"  # noqa: E702
            f"background-color:{self.rgb_to_css(self.colors.background)};"  # noqa: E702
            "display:inline-block;"
            f'">',
            file=self.out,
        )

        # print the title
        print(self.render_title(title=title), file=self.out)

    def finalize_drawing(self, **kwargs: Any) -> None:
        """[see superclass]"""
        super().finalize_drawing()
        # we close the section
        print("</div>", file=self.out)

        # if we are in a notebook, display the HTML
        if self._send_to_notebook:
            from IPython.display import HTML, display

            display(HTML(cast(StringIO, self.out).getvalue()))

    # noinspection PyMethodMayBeStatic
    def render_title(self, title: str) -> str:
        """
        Render the title of the drawing as HTML.

        :param title: the title of the drawing
        :return: the HTML code of the title
        """
        return f"<h2>{title}</h2>"
