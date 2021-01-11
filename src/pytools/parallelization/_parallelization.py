"""
Core implementation of :mod:`pytools.parallelization`.
"""
import logging
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar, Union

import joblib

from ..api import AllTracker

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = ["ParallelizableMixin"]


#
# Type variables
#

T = TypeVar("T")


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class ParallelizableMixin:
    """
    Mix-in class that supports parallelizing one or more operations using joblib.
    """

    def __init__(
        self,
        *,
        n_jobs: Optional[int] = None,
        shared_memory: Optional[bool] = None,
        pre_dispatch: Optional[Union[str, int]] = None,
        verbose: Optional[int] = None,
        **kwargs,
    ) -> None:
        """
        :param n_jobs: number of jobs to use in parallel;
            if ``None``, use joblib default (default: ``None``)
        :param shared_memory: if ``True``, use threads in the parallel runs; if
            ``False``, use multiprocessing (default: ``False``)
        :param pre_dispatch: number of batches to pre-dispatch;
            if ``None``, use joblib default (default: ``None``)
        :param verbose: verbosity level used in the parallel computation;
            if ``None``, use joblib default (default: ``None``)
        """
        super().__init__(**kwargs)
        #: Number of jobs to use in parallel; if ``None``, use joblib default.
        self.n_jobs = n_jobs

        #: If ``True``, use threads in the parallel runs;
        #: if ``False``, use multiprocessing.
        self.shared_memory = shared_memory

        #: Number of batches to pre-dispatch; if ``None``, use joblib default.
        self.pre_dispatch = pre_dispatch

        #: Verbosity level used in the parallel computation;
        #: if ``None``, use joblib default.
        self.verbose = verbose

        self._parallel_kwargs = {
            name: value
            for name, value in [
                ("n_jobs", n_jobs),
                ("require", "sharedmem" if shared_memory else None),
                ("pre_dispatch", pre_dispatch),
                ("verbose", verbose),
            ]
            if value is not None
        }

    def _parallel(self) -> joblib.Parallel:
        """
        Generate a :class:`joblib.Parallel` instance using the parallelization
        parameters of ``self``.

        :meta public:
        :return: the new :class:`joblib.Parallel` instance
        """
        return joblib.Parallel(**self._parallel_kwargs)

    @staticmethod
    def _delayed(
        function: Callable[..., T]
    ) -> Callable[..., Tuple[Callable[..., T], Tuple, Dict[str, Any]]]:
        """
        Decorate the given function for delayed execution.

        Convenience method preventing having to import :mod:`joblib`;
        defers to function :func:`joblib.delayed`.

        :meta public:
        :param function: the function to be delayed
        :return: the delayed function
        """
        return joblib.delayed(function)


__tracker.validate()
