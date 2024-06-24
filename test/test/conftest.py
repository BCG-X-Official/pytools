import logging

import pytest

from pytools.parallelization import Job

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


@pytest.fixture
def jobs() -> list[Job[int]]:
    # generate jobs using a class

    class TestJob(Job[int]):
        def __init__(self, x: int) -> None:
            self.x = x

        def run(self) -> int:
            return self.x

    return [TestJob(i) for i in range(8)]


@pytest.fixture
def jobs_delayed() -> list[Job[int]]:
    # generate jobs using class function Job.delayed
    def plus_2(x: int) -> int:
        return x + 2

    return [Job.delayed(plus_2)(i) for i in range(4)]
