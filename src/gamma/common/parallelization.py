"""
Parallelization support based on the `joblib` package.
"""
import logging
from typing import *

import joblib

log = logging.getLogger(__name__)

# noinspection PyShadowingBuiltins
_T = TypeVar("_T")


class ParallelizableMixin:
    """
    Mix-in class indicating the ability to parallelize one or more operations using
    joblib.

    :param n_jobs: number of jobs to _rank_learners in parallel (default: 1).
    :param shared_memory: if `True` use threads in the parallel runs. If `False` \
        use multiprocessing (default: `True`).
    :param verbose: verbosity level used in the parallel computation (default: 0).
    """

    def __init__(
        self, *, n_jobs: int = 1, shared_memory: bool = True, verbose: int = 0, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.n_jobs = n_jobs
        self.shared_memory = shared_memory
        self.verbose = verbose

    def _parallel(self) -> joblib.Parallel:
        return joblib.Parallel(
            n_jobs=self.n_jobs,
            require="sharedmem" if self.shared_memory else None,
            verbose=self.verbose,
        )

    @staticmethod
    def _delayed(
        function: Callable[..., _T]
    ) -> Callable[..., Tuple[Callable[..., _T], List, Mapping]]:
        return joblib.delayed(function)
