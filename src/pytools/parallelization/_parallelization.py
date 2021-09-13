"""
Core implementation of :mod:`pytools.parallelization`.
"""
import itertools
import logging
from abc import ABCMeta, abstractmethod
from functools import wraps
from multiprocessing import Lock
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import joblib

from ..api import AllTracker, inheritdoc, to_tuple

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = [
    "Job",
    "JobQueue",
    "JobRunner",
    "NestedQueue",
    "ParallelizableMixin",
    "SimpleQueue",
]

#
# Type variables
#

T = TypeVar("T")
T_JobRunner = TypeVar("T_JobRunner", bound="JobRunner")
T_Job_Result = TypeVar("T_Job_Result")
T_Queue_Result = TypeVar("T_Queue_Result")


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
        super().__init__()
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


class Job(Generic[T_Job_Result], metaclass=ABCMeta):
    """
    A job to be run as part of a parallelizable :class:`.JobQueue`.
    """

    @abstractmethod
    def run(self) -> T_Job_Result:
        """
        Run this job.

        :return: the result produced by the job
        """
        pass

    @classmethod
    def delayed(
        cls, function: Callable[..., T_Job_Result]
    ) -> "Callable[..., Job[T_Job_Result]]":
        """
        A decorator creating a `delayed` version of the given function which,
        if called with arguments, does not run immediately but instead returns a
        :class:`.Job` that will call the function with the given arguments.

        Once the job is run, it will call the function with the given arguments.

        :param function: a function returning the job result
        :return: the delayed version of the function
        """

        @wraps(function)
        def _delayed_function(*args, **kwargs: Any) -> Job[T_Job_Result]:
            @inheritdoc(match="""[see superclass]""")
            class _Job(Job[T_Job_Result]):
                def run(self) -> T_Job_Result:
                    """[see superclass]"""
                    return function(*args, **kwargs)

            return _Job()

        return _delayed_function


class JobQueue(Generic[T_Job_Result, T_Queue_Result], metaclass=ABCMeta):
    """
    A queue of jobs to be run in parallel, generating a collective result.

    Supports :meth:`.len` to determine the number of jobs in this queue.
    """

    #: The lock used by class :class:`.JobRunner` to prevent parallel executions of the
    #: same queue
    lock: Lock

    def __init__(self) -> None:
        self.lock = Lock()

    @abstractmethod
    def jobs(self) -> Iterable[Job[T_Job_Result]]:
        """
        Iterate the jobs in this queue.

        :return: the jobs in this queue
        """
        pass

    def on_run(self) -> None:
        """
        Called by :meth:`.JobRunner.run` when starting to run the jobs in this queue.

        Does nothing by default; overload as required to initialize the queue before
        each run.
        """

    @abstractmethod
    def aggregate(self, job_results: List[T_Job_Result]) -> T_Queue_Result:
        """
        Called by :meth:`.JobRunner.run` to aggregate the results of all jobs once they
        have all been run.

        :param job_results: list of job results, ordered corresponding to the sequence
            of jobs generated by method :meth:`.jobs`
        :return: the aggregated result of running the queue
        """
        pass

    @abstractmethod
    def __len__(self) -> int:
        pass


class JobRunner(ParallelizableMixin):
    """
    Runs job queues in parallel and aggregates results.
    """

    @classmethod
    def from_parallelizable(
        cls: Type[T_JobRunner], parallelizable: ParallelizableMixin
    ) -> T_JobRunner:
        """
        Create a new :class:`JobRunner` using the parameters of the given parallelizable
        object.

        :param parallelizable: the parallelizable instance whose parameters to use
            for the job runner
        :return: the new job runner
        """
        cls: Type[T_JobRunner]
        return cls(
            n_jobs=parallelizable.n_jobs,
            shared_memory=parallelizable.shared_memory,
            pre_dispatch=parallelizable.pre_dispatch,
            verbose=parallelizable.verbose,
        )

    def run_jobs(self, jobs: Iterable[Job[T_Job_Result]]) -> List[T_Job_Result]:
        """
        Run all given jobs in parallel.

        :param jobs: the jobs to run in parallel
        :return: the results of all jobs
        """
        with self._parallel() as parallel:
            return parallel(joblib.delayed(lambda job: job.run())(job) for job in jobs)

    def run_queue(self, queue: JobQueue[Any, T_Queue_Result]) -> T_Queue_Result:
        """
        Run all jobs in the given queue, in parallel.

        :param queue: the queue to run
        :return: the result of all jobs, aggregated using method
            :meth:`.JobQueue.aggregate`
        """

        with queue.lock:

            # notify the queue that we're about to run it
            queue.on_run()

            results = self.run_jobs(queue.jobs())

            if len(results) != len(queue):
                raise AssertionError(
                    f"Number of results ({len(results)}) does not match length of "
                    f"queue ({len(queue)}): check method {type(queue).__name__}.__len__"
                )

            return queue.aggregate(job_results=results)

    def run_queues(
        self, queues: Iterable[JobQueue[Any, T_Queue_Result]]
    ) -> List[T_Queue_Result]:
        """
        Run all jobs in the given queues, in parallel.

        :param queues: the queues to run in parallel
        :return: the result of all jobs in all queues, aggregated per queue using method
            :meth:`.JobQueue.aggregate`
        """

        queues: Sequence[JobQueue[T_Queue_Result]] = to_tuple(
            queues, element_type=JobQueue, arg_name="queues"
        )

        try:
            for queue in queues:
                queue.lock.acquire()

            # notify the queues that we're about to run them
            for queue in queues:
                queue.on_run()

            with self._parallel() as parallel:
                results: List[T_Job_Result] = parallel(
                    joblib.delayed(lambda job: job.run())(job)
                    for queue in queues
                    for job in queue.jobs()
                )

        finally:
            for queue in queues:
                queue.lock.release()

        queues_len = sum(len(queue) for queue in queues)
        if len(results) != queues_len:
            raise AssertionError(
                f"Number of results ({len(results)}) does not match length of "
                f"queues ({queues_len}): check method __len__() of the queue class(es)"
            )

        # split the results into a list for each queue
        queue_ends = list(itertools.accumulate(len(queue) for queue in queues))
        return [
            queue.aggregate(results[first_job:last_job])
            for queue, first_job, last_job in zip(queues, [0, *queue_ends], queue_ends)
        ]

    def _parallel(self) -> joblib.Parallel:
        # Generate a :class:`joblib.Parallel` instance using the parallelization
        # parameters of ``self``.
        return joblib.Parallel(**self._parallel_kwargs)


@inheritdoc(match="""[see superclass]""")
class SimpleQueue(
    JobQueue[T_Job_Result, T_Queue_Result],
    Generic[T_Job_Result, T_Queue_Result],
    metaclass=ABCMeta,
):
    """
    A simple queue, running a given list of jobs.
    """

    #: The jobs run by this queue.
    _jobs: Tuple[T_Job_Result, ...]

    def __init__(self, jobs: Iterable[Job[T_Job_Result]]) -> None:
        """
        :param jobs: jobs to be run by this queue in the given order
        """
        super().__init__()
        self._jobs = to_tuple(jobs, element_type=Job, arg_name="jobs")

    def jobs(self) -> Iterable[Job[T_Job_Result]]:
        """[see superclass]"""
        return self._jobs

    def __len__(self) -> int:
        return len(self._jobs)


@inheritdoc(match="""[see superclass]""")
class NestedQueue(JobQueue[T_Job_Result, List[T_Job_Result]], Generic[T_Job_Result]):
    """
    Runs all jobs in a given list of compatible queues and returns their results as a
    flat list.
    """

    #: The queues run by this queue.
    queues: Tuple[JobQueue[T_Job_Result, List[T_Job_Result]], ...]

    def __init__(
        self, queues: Sequence[JobQueue[T_Job_Result, List[T_Job_Result]]]
    ) -> None:
        """
        :param queues: queues to be run by this queue in the given order
        """
        super().__init__()
        self.queues = to_tuple(queues)

    def jobs(self) -> Iterable[Job[T_Job_Result]]:
        """[see superclass]"""
        return itertools.chain.from_iterable(queue.jobs() for queue in self.queues)

    def aggregate(self, job_results: List[T_Job_Result]) -> List[T_Job_Result]:
        """
        Return the list of job results as-is, without aggregating them any further.

        :param job_results: list of job results, ordered corresponding to the sequence
            of jobs generated by method :meth:`.jobs`
        :return: the identical list of job results
        """
        return job_results

    def __len__(self) -> int:
        return sum(len(queue) for queue in self.queues)


__tracker.validate()
