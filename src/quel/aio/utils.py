
import asyncio
import functools


def async_partial(func, *pargs, **pkwargs):
  assert asyncio.iscoroutinefunction(func), func
  @functools.wraps(func)
  async def wrapper(*args, **kwargs):
    kwargs.update(pkwargs)
    return await func(*(pargs + args), **kwargs)
  return wrapper


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


class local:

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
    if name.startswith('_local__'):
      object.__setattr__(self, name, value)
    else:
      self.__get_dict()[name] = value

  def __delattr__(self, name):
    data = self.__get_dict()
    try:
      del data[name]
    except KeyError:
      raise AttributeError(name)
