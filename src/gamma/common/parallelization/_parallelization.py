"""
Core implementation of :mod:`gamma.common.parallelization`
"""
import logging
from typing import *

import joblib

log = logging.getLogger(__name__)


#
# exported names
#

__all__ = ["ParallelizableMixin"]


#
# type variables
#

T = TypeVar("T")


#
# class definitions
#


class ParallelizableMixin:
    """
    Mix-in class indicating the ability to parallelize one or more operations using
    joblib.
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
            if `None`, use joblib default (default: `None`).
        :param shared_memory: if `True` use threads in the parallel runs. If `False` \
            use multiprocessing (default: `False`).
        :param pre_dispatch: number of batches to pre-dispatch; \
            if `None`, use joblib default (default: `None`).
        :param verbose: verbosity level used in the parallel computation; \
            if `None`, use joblib default (default: `None`).
        """
        super().__init__(**kwargs)
        self.n_jobs = n_jobs
        self.shared_memory = shared_memory
        self.pre_dispatch = pre_dispatch
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
