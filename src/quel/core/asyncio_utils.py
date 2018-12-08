
import asyncio
import functools


def async_partial(func, *pargs, **pkwargs):
  """
  An implementation of #functools.partial() for coroutine functions.
  """

  assert asyncio.iscoroutinefunction(func), func

  @functools.wraps(func)
  async def wrapper(*args, **kwargs):
    kwargs.update(pkwargs)
    return await func(*(pargs + args), **kwargs)

  return wrapper


class _async_iterator_wrapper:

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


class async_local:
  """
  A #threading.local implementation for coroutines.
  """

  def __init__(self):
    self.__data = {}

  def __get_dict(self, task=None):
    if task is None:
      task = asyncio.Task.current_task()
    try:
      return self.__data[id(task)]
    except KeyError:
      data = self.__data[id(task)] = {}
      task.add_done_callback(lambda t: self.__data.pop(id(t)))
      return data
    finally:
      del task

  def __getattr__(self, name):
    data = self.__get_dict()
    try:
      return data[name]
    except KeyError:
      raise AttributeError(name)

  def __setattr__(self, name, value):
    if name.startswith('_async_local__'):
      object.__setattr__(self, name, value)
    else:
      self.__get_dict()[name] = value

  def __delattr__(self, name):
    data = self.__get_dict()
    try:
      del data[name]
    except KeyError:
      raise AttributeError(name)


class async_rlock(asyncio.Lock):
  """
  A reentrant lock for Python coroutines.
  """

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._task = None
    self._depth = 0

  async def acquire(self):
    if self._task is None or self._task != asyncio.Task.current_task():
      await super().acquire()
      self._task = asyncio.Task.current_task()
      assert self._depth == 0
    self._depth += 1

  def release(self):
    if self._depth > 0:
      self._depth -= 1
    if self._depth == 0:
      super().release()
      self._task = None


def flush_local(local):
  assert isinstance(local, async_local), type(local)
  t = asyncio.Task.current_task()
  local._async_local__data.pop(id(t), None)


def run_in_executor(__executor, __func, *args, **kwargs):
  """
  A shortcut for running a function in an executor. Pass `None` to
  run in the event loops main executor.
  """

  loop = asyncio.get_running_loop()
  return loop.run_in_executor(__executor,
    functools.partial(__func, *args, **kwargs))


def run_iterator_in_executor(executor, iterator, async_=True):
  """
  A helper function to run a non-asynchronous iterator in an executor.
  If *async_* is `False` the *iterator* will simply be wrapped in an
  asynchronous iterator.
  """

  loop = asyncio.get_running_loop()
  return _async_iterator_wrapper(iterator, loop, executor, async_)
