import logging
from typing import List

from pytools.parallelization import Job, JobRunner, SimpleQueue

log = logging.getLogger(__name__)


def test_jobs(jobs: List[Job[int]], jobs_delayed: List[Job[int]]) -> None:
    assert JobRunner().run_jobs(jobs) == [0, 1, 2, 3, 4, 5, 6, 7]
    assert JobRunner(n_jobs=1).run_jobs(jobs) == [0, 1, 2, 3, 4, 5, 6, 7]
    assert JobRunner(n_jobs=-3).run_jobs(jobs) == [0, 1, 2, 3, 4, 5, 6, 7]

    assert JobRunner().run_jobs(jobs_delayed) == [2, 3, 4, 5]
    assert JobRunner(n_jobs=1).run_jobs(jobs_delayed) == [2, 3, 4, 5]
    assert JobRunner(n_jobs=-3).run_jobs(jobs_delayed) == [2, 3, 4, 5]


def test_queue(jobs: List[Job[int]], jobs_delayed: List[Job[int]]) -> None:
    class PassthroughQueue(SimpleQueue[int, List[int]]):
        def aggregate(self, job_results: List[int]) -> List[int]:
            return job_results

    queue_1 = PassthroughQueue(jobs)
    queue_2 = PassthroughQueue(jobs_delayed)

    assert JobRunner().run_queue(queue_1) == [0, 1, 2, 3, 4, 5, 6, 7]
    assert JobRunner(n_jobs=1).run_queue(queue_1) == [0, 1, 2, 3, 4, 5, 6, 7]
    assert JobRunner(n_jobs=-3).run_queue(queue_1) == [0, 1, 2, 3, 4, 5, 6, 7]

    assert JobRunner().run_queue(queue_2) == [2, 3, 4, 5]
    assert JobRunner(n_jobs=1).run_queue(queue_2) == [2, 3, 4, 5]
    assert JobRunner(n_jobs=-3).run_queue(queue_2) == [2, 3, 4, 5]

    assert list(JobRunner().run_queues([queue_1, queue_2])) == [
        [0, 1, 2, 3, 4, 5, 6, 7],
        [2, 3, 4, 5],
    ]
    assert list(JobRunner(n_jobs=1).run_queues([queue_1, queue_2])) == [
        [0, 1, 2, 3, 4, 5, 6, 7],
        [2, 3, 4, 5],
    ]
    assert list(JobRunner(n_jobs=-3).run_queues([queue_1, queue_2])) == [
        [0, 1, 2, 3, 4, 5, 6, 7],
        [2, 3, 4, 5],
    ]

    class SumQueue(SimpleQueue[int, int]):
        def aggregate(self, job_results: List[int]) -> int:
            return sum(job_results)

    queue_1_sum = SumQueue(jobs)
    queue_2_sum = SumQueue(jobs_delayed)

    assert JobRunner().run_queue(queue_1_sum) == 28
    assert JobRunner(n_jobs=1).run_queue(queue_1_sum) == 28
    assert JobRunner(n_jobs=-3).run_queue(queue_1_sum) == 28

    assert JobRunner().run_queue(queue_2_sum) == 14
    assert JobRunner(n_jobs=1).run_queue(queue_2_sum) == 14
    assert JobRunner(n_jobs=-3).run_queue(queue_2_sum) == 14

    assert list(JobRunner().run_queues([queue_1_sum, queue_2_sum])) == [28, 14]
    assert list(JobRunner(n_jobs=1).run_queues([queue_1_sum, queue_2_sum])) == [28, 14]
    assert list(JobRunner(n_jobs=-3).run_queues([queue_1_sum, queue_2_sum])) == [28, 14]
