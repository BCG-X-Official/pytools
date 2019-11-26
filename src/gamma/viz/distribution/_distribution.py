"""
Core implementation of :mod:`gamma.viz.distribution`
"""

import logging
from abc import ABC, abstractmethod
from typing import *

import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from gamma.viz import Drawer, DrawStyle, MatplotStyle

__all__ = ["ECDFStyle", "ECDFMatplotStyle", "ECDFDrawer"]

log = logging.getLogger(__name__)

DEFAULT_COLOR_OUTLIER = "orange"
DEFAULT_COLOR_FAR_OUTLIER = "purple"

DEFAULT_IQR_MULTIPLE = 1.5
DEFAULT_IQR_MULTIPLE_FAR = 3.0


class _XYSeries(NamedTuple):
    """
    Series of x and y coordinates for plotting; x and y values are held in two
    separate lists of the same length.
    """

    x: Sequence[float]
    y: Sequence[float]


class _Ecdf(NamedTuple):
    """
    Three sets of coordinates for plotting an ECDF: inliers, outliers, and far
    outliers.
    """

    inliers: _XYSeries
    outliers: _XYSeries
    far_outliers: _XYSeries


class ECDFStyle(DrawStyle, ABC):
    """
    The base drawing style for ECDFs
    """

    @abstractmethod
    def _draw_ecdf(
        self, ecdf: _Ecdf, x_label: str, iqr_multiple: float, iqr_multiple_far: float
    ) -> None:
        pass


class ECDFMatplotStyle(ECDFStyle, MatplotStyle):
    """
    Plot an ECDF as a Matplotlib plot.

    :param ax: optional axes object to draw on; if `Null` use pyplot's current axes
    :param color_non_outlier: the color for non outlier points (default: blue)
    :param color_outlier: the color for outlier points (default: orange)
    :param color_far_outlier: the color for far outlier points (default: red)
    """

    def __init__(
        self,
        *,
        ax: Optional[Axes] = None,
        color_outlier: str = DEFAULT_COLOR_OUTLIER,
        color_far_outlier: str = DEFAULT_COLOR_FAR_OUTLIER,
        **kwargs,
    ):
        super().__init__(ax=ax, **kwargs)
        self._color_outlier = color_outlier
        self._color_far_outlier = color_far_outlier

    def _drawing_start(self, title: str) -> None:
        super()._drawing_start(title=title)

    def _draw_ecdf(
        self, ecdf: _Ecdf, x_label: str, iqr_multiple: float, iqr_multiple_far: float
    ) -> None:
        def _iqr_annotation(multiple: float) -> str:
            return f"(> {multiple:.3g} * IQR)"

        ax = self.ax
        matplotlib_kwargs = {"marker": ".", "linestyle": "none"}
        ax.plot(ecdf.inliers.x, ecdf.inliers.y, label="inlier", **matplotlib_kwargs)
        ax.plot(
            ecdf.outliers.x,
            ecdf.outliers.y,
            color=self._color_outlier,
            label=f"outlier {_iqr_annotation(multiple=iqr_multiple)}",
            **matplotlib_kwargs,
        )
        ax.plot(
            ecdf.far_outliers.x,
            ecdf.far_outliers.y,
            color=self._color_far_outlier,
            label=f"far outlier {_iqr_annotation(multiple=iqr_multiple_far)}",
            **matplotlib_kwargs,
        )

        # add axis labels and legend
        self.ax.set_xlabel(x_label)
        ax.set_ylabel("count")
        ax.legend()


class ECDFDrawer(Drawer[Sequence[float], ECDFStyle]):
    """
    Drawer for empirical cumulative density functions (ECDFs).
    """

    _STYLES = {"matplot": ECDFMatplotStyle}

    def __init__(
        self,
        style: Union[ECDFStyle, str] = "matplot",
        iqr_multiple: Optional[float] = DEFAULT_IQR_MULTIPLE,
        iqr_multiple_far: Optional[float] = DEFAULT_IQR_MULTIPLE_FAR,
        hide_far_outliers: Optional[bool] = False,
    ) -> None:
        """
        :param style: the style of the chart; either as a \
            :class:`~gamma.viz.distribution.ECDFStyle` instance, or as the name of a \
            default style. Permissible names include "matplot" for a style supporting \
            Matplotlib (default: `"matplot"`).
        :param iqr_multiple: iqr multiple to determine outliers. If `None`, then no \
            outliers and far outliers are computed (default: 1.5).
        :param iqr_multiple_far: iqr multiple to determine far outliers. If `None`, then \
            no far outliers are computed. Should be greater than `iqr_multiple` when both \
            are defined (default: 3.0).
        :param hide_far_outliers: if `True`, do not plot far outliers (default: `False`)
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

        self._iqr_multiple = iqr_multiple
        self._iqr_multiple_far = iqr_multiple_far
        self._hide_far_outliers = hide_far_outliers

    def draw(self, data: Sequence[float], title: Optional[str] = None) -> None:
        """
        Draw the chart.
        :param data: the data to draw
        :param title: the title of the chart (optional; defaults to "ECDF"; if arg \
            `data` is a series then the default title will include name of the series)
        """
        if title is None:
            if hasattr(data, "name"):
                title = f"ECDF: {data.name}"
            else:
                title = "ECDF"
        super().draw(data=data, title=title)

    @classmethod
    def _get_style_dict(cls) -> Mapping[str, Type[ECDFStyle]]:
        return ECDFDrawer._STYLES

    def _draw(self, data: Sequence[float]) -> None:
        ecdf = self._ecdf(data=data)
        x_label = getattr(data, "name", "value")
        # noinspection PyProtectedMember
        self.style._draw_ecdf(
            ecdf=ecdf,
            x_label=x_label,
            iqr_multiple=self._iqr_multiple,
            iqr_multiple_far=self._iqr_multiple_far,
        )

    def _ecdf(self, data: Sequence[float]) -> _Ecdf:
        """
        Compute ECDF for scalar values.

        Return the x and y values of an empirical cumulative distribution plot of the
        values in ``data``. Outlier and far outlier points are returned in separate
        lists.

        A sample is considered an outlier if it is outside the range
        :math:`[Q_1 - iqr\\_ multiple(Q_3-Q_1), Q_3 + iqr\\_ multiple(Q_3-Q_1)]`
        where :math:`Q_1` and :math:`Q_3` are the lower and upper quartiles. The same
        is used for far outliers with ``iqr_multiple`` replaced by ``iqr_multiple_far``.

        :param data: the series of values forming our sample
        :return: x_inlier, y_inlier, x_outlier, y_outlier, x_far_outlier, \
            y_far_outlier: \
            lists of x and y coordinates for the ecdf plot for the inlier, outlier and \
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

        iqr_multiple = self._iqr_multiple
        iqr_multiple_far = self._iqr_multiple_far
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

        return _Ecdf(
            _XYSeries(x[inlier_mask], y[inlier_mask]),
            _XYSeries(x[outlier_mask], y[outlier_mask]),
            _XYSeries([], [])
            if self._hide_far_outliers
            else _XYSeries(x[far_out_mask], y[far_out_mask]),
        )
