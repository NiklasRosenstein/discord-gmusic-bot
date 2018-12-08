
import asyncio
import concurrent
import requests

from .asyncio_utils import run_in_executor, run_iterator_in_executor


def expose_property(func, member_name):
  def getter(self):
    return getattr(func(self), member_name)
  def setter(self):
    setattr(func(self), member_name)
  def deleter(self):
    delattr(func(self), member_name)
  return property(getter, setter, deleter)


class Session:

  def __init__(self, session=None, executor=None):
    self._session = session or requests.Session()
    self._executor = executor

  auth = expose_property(lambda self: self._session, 'auth')
  verify = expose_property(lambda self: self._session, 'verify')
  headers = expose_property(lambda self: self._session, 'headers')
  cookies = expose_property(lambda self: self._session, 'cookies')

  async def request(self, *args, **kwargs):
    return Response(await run_in_executor(self._executor,
      self._session.request, *args, **kwargs), kwargs.get('stream', False))

  async def delete(self, *args, **kwargs):
    return await self.request('DELETE', *args, **kwargs)

  async def get(self, *args, **kwargs):
    return await self.request('GET', *args, **kwargs)

  async def post(self, *args, **kwargs):
    return await self.request('POST', *args, **kwargs)

  async def put(self, *args, **kwargs):
    return await self.request('PUT', *args, **kwargs)


class Response:

  def __init__(self, request, stream):
    self._request = request
    self._stream = stream

  def __str__(self):
    return str(self._request)

  def __getattr__(self, attr_name):
    return getattr(self._request, attr_name)

  @property
  def content(self):
    if self._stream:
      return run_in_executor(None, lambda: self._request.content)
    else:
      async def future(): return self._request.content
      return future()

  @property
  def text(self):
    if self._stream:
      return run_in_executor(None, lambda: self._request.text)
    else:
      async def future(): return self._request.text
      return future()

  @property
  def history(self):
    return [Response(x, False) for x in self._request.history]

  def iter_content(self, *args, **kwargs):
    it = self._request.iter_content(*args, **kwargs)
    return run_iterator_in_executor(None, it, async_=self._stream)

  def iter_lines(self, *args, **kwargs):
    it = self._request.iter_lines(*args, **kwargs)
    return run_iterator_in_executor(None, it, async_=self._stream)

  def json(self):
    if self._stream:
      return run_in_executor(None, lambda: self._request.json())
    else:
      async def future(): return self._request.json()
      return future()


async def request(*args, **kwargs):
  executor = kwargs.pop('executor', None)
  response = await run_in_executor(executor, requests.request, *args, **kwargs)
  return Response(response, kwargs.get('stream', False))


async def delete(*args, **kwargs):
  return await request('DELETE', *args, **kwargs)


async def get(*args, **kwargs):
  return await request('GET', *args, **kwargs)


async def post(*args, **kwargs):
  return await request('POST', *args, **kwargs)


async def put(*args, **kwargs):
  return await request('PUT', *args, **kwargs)
