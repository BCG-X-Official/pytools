"""
Core implementation of :mod:`pytools.viz.distribution`.
"""

import logging
from typing import Iterable, Optional, Sequence, Type, Union

import numpy as np
import pandas as pd

from .. import Drawer, MatplotStyle
from .base import ECDF, ECDFStyle, XYSeries
from pytools.api import AllTracker, inheritdoc

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = [
    "ECDFMatplotStyle",
    "ECDFDrawer",
]


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class ECDFMatplotStyle(ECDFStyle, MatplotStyle):
    """
    Draws ECDF plots using `matplotlib`.
    """

    def _draw_ecdf(
        self, ecdf: ECDF, x_label: str, iqr_multiple: float, iqr_multiple_far: float
    ) -> None:
        def _iqr_annotation(multiple: float) -> str:
            return f"(> {multiple:.3g} * IQR)"

        ax = self.ax
        colors = self.colors
        matplotlib_kwargs = {"marker": ".", "linestyle": "none"}
        ax.plot(
            ecdf.inliers.x,
            ecdf.inliers.y,
            color=colors.status_ok,
            label="inlier",
            **matplotlib_kwargs,
        )
        ax.plot(
            ecdf.outliers.x,
            ecdf.outliers.y,
            color=colors.status_warning,
            label=f"outlier {_iqr_annotation(multiple=iqr_multiple)}",
            **matplotlib_kwargs,
        )
        ax.plot(
            ecdf.far_outliers.x,
            ecdf.far_outliers.y,
            color=colors.status_critical,
            label=f"far outlier {_iqr_annotation(multiple=iqr_multiple_far)}",
            **matplotlib_kwargs,
        )

        # add axis labels and legend
        ax.set_xlabel(x_label, color=colors.foreground)
        ax.set_ylabel("count", color=colors.foreground)
        ax.legend()


@inheritdoc(match="[see superclass]")
class ECDFDrawer(Drawer[Sequence[float], ECDFStyle]):
    """
    Drawer for empirical cumulative density functions (ECDFs), highlighting
    outliers using Tukey's outlier test.

    The drawer highlights samples as `outliers` or `far outliers`.

    A sample is considered an outlier if it is outside the range
    :math:`[q_1 - m * \\mathit{iqr}, q_3 + m * \\mathit{iqr}]`
    where :math:`q_1` and :math:`q_3` are the lower and upper quartiles,
    :math:`\\mathit{iqr} = q3 - q1` is the `inter-quartile range (IQR)`, and
    :math:`m` is the `IQR multiple`.

    By convention, common values for :math:`m` are :math:`m = 1.5` for outliers,
    and :math:`m = 3` for far outliers.
    """

    #: iqr multiple to determine outliers;
    #: if ``None``, then no outliers and far outliers are computed
    iqr_multiple: Optional[float]

    #: iqr multiple to determine far outliers;
    #: if ``None``, then no far outliers are computed, otherwise
    #: must be greater than ``iqr_multiple``
    iqr_multiple_far: Optional[float]

    #: if ``True``, do not plot far outliers
    hide_far_outliers: bool

    def __init__(
        self,
        style: Optional[Union[ECDFStyle, str]] = None,
        iqr_multiple: Optional[float] = 1.5,
        iqr_multiple_far: Optional[float] = 3.0,
        hide_far_outliers: bool = False,
    ) -> None:
        """
        :param iqr_multiple: iqr multiple to determine outliers; if ``None``, then no
            outliers and far outliers are computed.
        :param iqr_multiple_far: iqr multiple to determine far outliers; if ``None``,
            then no far outliers are computed, otherwise must be greater than
            `iqr_multiple`.
        :param hide_far_outliers: if ``True``, do not plot far outliers
            (default: ``False``)
        """
        super().__init__(style=style)

        if iqr_multiple_far:
            if not iqr_multiple:
                raise ValueError(
                    "arg iqr_multiple must be defined if arg iqr_multiple_far is "
                    "defined"
                )
            if iqr_multiple_far <= iqr_multiple:
                raise ValueError(
                    f"arg iqr_multiple={iqr_multiple} must be smaller than "
                    f"arg iqr_multiple_far={iqr_multiple_far}"
                )

        self.iqr_multiple = iqr_multiple
        self.iqr_multiple_far = iqr_multiple_far
        self.hide_far_outliers = hide_far_outliers

    __init__.__doc__ = Drawer.__init__.__doc__ + __init__.__doc__

    def draw(self, data: Sequence[float], *, title: Optional[str] = None) -> None:
        """
        Draw the ECDF.

        :param data: the data to draw
        :param title: the title of the chart (optional; defaults to ``"ECDF"``; if arg
            `data` is a :class:`~.Series` or any other class with a `name`
            attribute, then the default title will include the name)
        """
        if title is None:
            if hasattr(data, "name"):
                title = f"ECDF: {data.name}"
            else:
                title = "ECDF"
        super().draw(data=data, title=title)

    @classmethod
    def get_style_classes(cls) -> Iterable[Type[ECDFStyle]]:
        """[see superclass]"""
        return [
            ECDFMatplotStyle,
        ]

    def _draw(self, data: Sequence[float]) -> None:
        ecdf = self._ecdf(data=data)
        x_label = getattr(data, "name", "value")
        # noinspection PyProtectedMember
        self.style._draw_ecdf(
            ecdf=ecdf,
            x_label=x_label,
            iqr_multiple=self.iqr_multiple,
            iqr_multiple_far=self.iqr_multiple_far,
        )

    def _ecdf(self, data: Sequence[float]) -> ECDF:
        """
        Compute ECDF for scalar values.

        Return the x and y values of an empirical cumulative distribution plot of the
        values in arg `data`. Outlier and far outlier points are returned in separate
        lists.

        :param data: the series of values forming our sample
        :return: x_inlier, y_inlier, x_outlier, y_outlier, x_far_outlier,
            y_far_outlier:
            lists of x and y coordinates for the ecdf plot for the inlier, outlier and
            far outlier points.
        """

        # x-data for the ECDF: x
        if isinstance(data, pd.Series):
            data = data.values
        if not isinstance(data, np.ndarray):
            data = np.array(data)
        x = np.sort(data[~np.isnan(data)])

        # Number of data points: n
        n = len(x)

        # y-data for the ECDF: y
        y = np.arange(1, n + 1)

        iqr_multiple = self.iqr_multiple
        iqr_multiple_far = self.iqr_multiple_far
        if iqr_multiple:
            # outliers
            q1, q3 = np.percentile(x, [25, 75])

            iqr = q3 - q1
            out_lower = q1 - iqr_multiple * iqr
            out_upper = q3 + iqr_multiple * iqr
            inlier_mask = (x >= out_lower) & (x <= out_upper)

            if iqr_multiple_far:
                far_out_lower = q1 - iqr_multiple_far * iqr
                far_out_upper = q3 + iqr_multiple_far * iqr
                outlier_mask = (
                    (~inlier_mask) & (x >= far_out_lower) & (x <= far_out_upper)
                )
                far_out_mask = ~(inlier_mask | outlier_mask)
            else:
                outlier_mask = ~inlier_mask
                far_out_mask = []

        else:
            inlier_mask = slice(None)
            outlier_mask = []
            far_out_mask = []

        return ECDF(
            inliers=XYSeries(x=x[inlier_mask], y=y[inlier_mask]),
            outliers=XYSeries(x=x[outlier_mask], y=y[outlier_mask]),
            far_outliers=(
                XYSeries(x=[], y=[])
                if self.hide_far_outliers
                else XYSeries(x=x[far_out_mask], y=y[far_out_mask])
            ),
        )


__tracker.validate()
