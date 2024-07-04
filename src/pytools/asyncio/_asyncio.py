"""
Implementation of asyncio-related utilities
"""

from __future__ import annotations

import asyncio
import logging
import sys
from asyncio import Queue
from collections.abc import (
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Coroutine,
    Iterable,
    Iterator,
)
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar, cast

log = logging.getLogger(__name__)

__all__ = [
    "aenumerate",
    "arun",
    "async_flatten",
    "iter_async_to_sync",
    "iter_sync_to_async",
    "unpack_exception_group",
]

#
# Type variables
#

T = TypeVar("T")


#
# Python 3.10 compatibility
#

if sys.version_info < (3, 11):
    from typing import Generic

    class ExceptionGroup(Exception, Generic[T]):
        """
        Placeholder for the ExceptionGroup class, which is available from Python 3.11.
        """

        exceptions: list[Exception] = []

    class TaskGroup:
        """
        Placeholder for the TaskGroup class, which is available from Python 3.11.
        """

        def __aenter__(self) -> Any:
            pass

        def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
            pass

else:
    from asyncio import TaskGroup

#
# Constants
#

# Sentinel to indicate the end of processing
_END = "End"


#
# Functions
#


async def iter_async_to_sync(async_iterable: AsyncIterable[T]) -> Iterator[T]:
    """
    Materialize an asynchronous iterator as a list to enable synchronous iteration.

    :param async_iterable: an async iterator
    :return: the iterated elements as a list
    """
    return iter([product async for product in async_iterable])


async def iter_sync_to_async(iterable: Iterable[T]) -> AsyncIterator[T]:
    """
    Convert a synchronous iterator to an asynchronous iterator.

    :param iterable: a synchronous iterator
    :return: an async iterator
    """
    for product in iterable:
        yield product


async def aenumerate(
    async_iterable: AsyncIterable[T], start: int = 0
) -> AsyncIterator[tuple[int, T]]:
    """
    Asynchronous version of :func:`enumerate`.

    :param async_iterable: an asynchronous iterable
    :param start: the starting index (default: 0)
    :return: an asynchronous iterator of tuples containing the index and the element
    """
    i = start
    async for product in async_iterable:
        yield i, product
        i += 1


def async_flatten(
    async_iter_of_iters: AsyncIterable[AsyncIterable[T]],
) -> AsyncIterator[T]:
    """
    Flatten an asynchronous iterator of asynchronous iterators into a single
    asynchronous iterator, returning the elements in the order they are produced.

    :param async_iter_of_iters: an asynchronous iterator of asynchronous iterators
    :return: an asynchronous iterator
    """

    return _async_flatten_310(async_iter_of_iters)


async def _async_flatten_310(
    async_iter_of_iters: AsyncIterable[AsyncIterable[T]],
) -> AsyncIterator[T]:
    queue: Queue[T] = asyncio.Queue()

    async def _process_nested(async_iter: AsyncIterable[T]) -> None:
        async for _value in async_iter:
            await queue.put(_value)

    async def _producer() -> None:
        try:

            # Wait for all tasks to complete, propagating any exceptions.
            await asyncio.gather(
                *[
                    asyncio.create_task(_process_nested(async_iter))
                    async for async_iter in async_iter_of_iters
                ]
            )
        finally:
            # Signal the end of processing by putting a sentinel value in the queue.
            await queue.put(cast(T, _END))

    # start a new producer task to process the nested iterators
    producer_task = asyncio.create_task(_producer())

    # Then wait for the iterators to add their values to the queue
    while True:
        value = await queue.get()
        if value is _END:
            break
        yield value

    # Wait for the producer task to complete
    await producer_task


async def _async_flatten_311(
    async_iter_of_iters: AsyncIterable[AsyncIterable[T]],
) -> AsyncIterator[T]:
    queue: Queue[T] = asyncio.Queue()

    async def _process_nested(async_iter: AsyncIterable[T]) -> None:
        async for _value in async_iter:
            await queue.put(_value)

    async def _producer() -> None:
        # Coroutine to process each nested iterator as concurrently as possible,
        # using a task group to manage the processing of each nested iterator.

        async with TaskGroup() as producer_tg:
            async for async_iter in async_iter_of_iters:
                producer_tg.create_task(_process_nested(async_iter))

        # The task group will complete when all nested iterators have been processed.
        # We then signal the end of processing by putting a sentinel value in the queue.
        await queue.put(cast(T, _END))

    # start a new producer task to process the nested iterators
    async with TaskGroup() as tg:
        # Start processing the nested iterators concurrently
        tg.create_task(_producer())

        # Then wait for the iterators to add their values to the queue
        while True:
            value = await queue.get()
            if value is _END:
                break
            yield value


def arun(coroutine: Coroutine[Any, Any, T]) -> T:
    """
    Runs a coroutine and returns the result once ready.

    If there is no event loop running, creates a new event loop in the current thread.
    If there is an event loop running, creates a new event loop in a new thread.

    :param coroutine: the coroutine to run
    :return: the result of the Awaitable once it has completed
    :raises Exception: if the coroutine raises a single exception
    :raises ExceptionGroup: if the coroutine raises multiple exceptions
    """

    # Define a function that runs the event loop and executes the awaitable
    # This internal function is where the action happens, so we also add type hints here
    def _run_event_loop(loop: asyncio.AbstractEventLoop, awaitable: Awaitable[T]) -> T:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(awaitable)

    # Get the current event loop, if it exists
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # There is no running loop. Run the coroutine in the current thread.
        log.debug(
            "arun: creating a new event loop in the current thread to run "
            f"coroutine {coroutine.__qualname__}()"
        )
        try:
            return asyncio.run(coroutine)
        except ExceptionGroup as e:
            # One or more coroutines raised exceptions. These exceptions are combined
            # into a (possibly nested) ExceptionGroup, which we catch here.
            # Traverse the nested exception groups to find the first atomic
            # sub-exception.
            exception_group = e
    else:
        # Create a new event loop to run the coroutine in a new thread
        log.debug(
            "arun: creating a new event loop in a new thread to run coroutine "
            f"{coroutine.__qualname__}()"
        )
        new_loop = asyncio.new_event_loop()

        try:
            # Use ThreadPoolExecutor to run the event loop in a new thread
            with ThreadPoolExecutor() as executor:
                # Schedule the execution of the coroutine in the new event loop,
                # and return the result once the coroutine has completed
                return executor.submit(_run_event_loop, new_loop, coroutine).result()
        except ExceptionGroup as e:
            # One or more coroutines raised exceptions. These exceptions are combined
            # into a (possibly nested) ExceptionGroup, which we catch here.
            # Traverse the nested exception groups to find the first atomic
            # sub-exception.
            exception_group = e

    atomic_exceptions = list(unpack_exception_group(exception_group))
    if len(list(atomic_exceptions)) == 1:
        # If there is only one atomic exception, raise it directly
        raise atomic_exceptions[0]
    else:
        # If there are multiple atomic exceptions, raise the exception group
        raise exception_group


def unpack_exception_group(exception_group: ExceptionGroup[Any]) -> Iterator[Exception]:
    """
    Unpack an :class:`ExceptionGroup` to yield its atomic exceptions.

    :param exception_group: the exception group to unpack
    :return: a generator of atomic exceptions
    """
    for exception in exception_group.exceptions:
        if isinstance(exception, ExceptionGroup):
            yield from unpack_exception_group(exception)
        else:
            yield exception
