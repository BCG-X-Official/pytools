"""
Core implementation of :mod:`pytools.parallelization`
"""
import logging
from typing import *

import joblib

log = logging.getLogger(__name__)


#
# exported names
#




#
# type variables
#

T = TypeVar("T")


#
# class definitions
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
        :param n_jobs: number of jobs to use in parallel; \
            if ``None``, use joblib default (default: ``None``).
        :param shared_memory: if ``True`` use threads in the parallel runs. If ``False`` \
            use multiprocessing (default: ``False``).
        :param pre_dispatch: number of batches to pre-dispatch; \
            if ``None``, use joblib default (default: ``None``).
        :param verbose: verbosity level used in the parallel computation; \
            if ``None``, use joblib default (default: ``None``).
        """
        super().__init__(**kwargs)
        #: number of jobs to use in parallel; if ``None``, use joblib default
        self.n_jobs = n_jobs

        #: shared_memory: if ``True`` use threads in the parallel runs.
        #: If ``False``, use multiprocessing
        self.shared_memory = shared_memory

        #: pre_dispatch: number of batches to pre-dispatch; if ``None``, use joblib default
        self.pre_dispatch = pre_dispatch

        #: verbosity level used in the parallel computation; if ``None``, use joblib default
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
        return joblib.Parallel(**self._parallel_kwargs)

    @staticmethod
    def _delayed(
        function: Callable[..., T]
    ) -> Callable[..., Tuple[Callable[..., T], List, Mapping]]:
        return joblib.delayed(function)
