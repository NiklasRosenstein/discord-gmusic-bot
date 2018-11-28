
import asyncio
import functools


def run_in_executor(__executor, __func, *args, **kwargs):
  loop = asyncio.get_running_loop()
  return loop.run_in_executor(__executor,
    functools.partial(__func, *args, **kwargs))


def run_iterator_in_executor(executor, iterator, async_=True):
  loop = asyncio.get_running_loop()
  return AsyncIteratorWrapper(iterator, loop, executor, async_)


class AsyncIteratorWrapper:

  def __init__(self, iterable, loop=None, executor=None, async_=True):
    self._iterator = iter(iterable)
    self._loop = loop or asyncio.get_event_loop()
    self._executor = executor
    self._async = async_

  def __aiter__(self):
    return self

  async def __anext__(self):
    def _next(iterator):
      try: return next(iterator)
      except StopIteration: raise StopAsyncIteration
    if self._async:
      return await self._loop.run_in_executor(
        self._executor, _next, self._iterator)
    else:
      return _next(self._iterator)
