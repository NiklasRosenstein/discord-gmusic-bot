

from .utils import async_partial, async_local_proxy

import asyncio
import discord
import enum
import functools
import weakref

event, get_event, set_event = async_local_proxy()


class EventType(enum.Enum):
  ready = 0
  message = 1
  error = 2


class Event:

  def __init__(self, type, client, **kwargs):
    self.type = type
    self.client = client
    vars(self).update(kwargs)


class MessageEvent(Event):

  def __init__(self, client, message):
    super().__init__(EventType.message, client, message=message, text=message.content)

  async def reply(self, *args, **kwargs):
    return await self.message.channel.send(*args, **kwargs)


def propagate_event(func):
  """
  Wraps a coroutine function so that it will have the same event object as
  the one that is assigned at the time that this function is called. Useful
  if you need to use #asyncio.run_coroutine_threadsafe() but want to maintain
  the #event state.
  """

  ev_obj = get_event()
  @functools.wraps(func)
  async def wrapper(*args, **kwargs):
    with set_event(ev_obj):
      return await func(*args, **kwargs)
  return wrapper


def prepare_ready(client):
  return Event(EventType.ready, client)


def prepare_message(client, message):
  return MessageEvent(client, message)


#def prepare_error(event_method, *args, **kwargs):
#  return Event(EventType.error, event_method=event_method, args=args, kwargs=kwargs)


class EventHandler:

  _client = None

  @property
  def client(self):
    return None if self._client is None else self._client()

  def added_to_client(self, client):
    self._client = weakref.ref(client)

  async def handle_event(self):
    return False


class EventMultiplexer(EventHandler):

  def __init__(self):
    members = (getattr(type(self), k) for k in dir(type(self)))
    self.handlers = [x for x in members if isinstance(x, MemberEventHandler)]
    self.handlers.sort(key=lambda x: x.order_index)

  async def handle_event(self):
    for handler in self.handlers:
      if await handler.handle_event(self):
        return True
    return False


class MemberEventHandler:

  _current_order_index = 0

  def __init__(self, func):
    assert asyncio.iscoroutinefunction(func)
    self.func = func
    self.order_index = MemberEventHandler._current_order_index
    MemberEventHandler._current_order_index += 1

  def __get__(self, instance, owner):
    if instance is None:
      return self
    @functools.wraps(self.func)
    async def wrapper(*args, **kwargs):
      return await self.func(instance, *args, **kwargs)
    return wrapper

  @classmethod
  def decorate(cls, *args, **kwargs):
    def decorator(func):
      return cls(func, *args, **kwargs)
    return decorator

  async def handle_event(self, instance):
    raise NotImplementedError


class Client:
  """
  A wrapper for the #discord.Client class. Actually creates the discord Client
  only when it is supposed to run to circumvent some asyncio unfinished
  business errors when it is not actually run.
  """

  def __init__(self):
    self.__client = None
    self.__handlers = []

  def run(self, *args, **kwargs):
    self.__client = discord.Client()
    for name, value in globals().items():
      if name.startswith('prepare_'):
        async def dispatcher(prepare, *args, **kwargs):
          event = prepare(self, *args, **kwargs)
          return await self.dispatch_event(event)
        dispatcher.__name__ = 'on_' + name[len('prepare_'):]
        self.__client.event(async_partial(dispatcher, value))
    return self.__client.run(*args, **kwargs)

  def add_handler(self, handler):
    assert isinstance(handler, EventHandler)
    handler.added_to_client(self)
    self.__handlers.append(handler)

  async def dispatch_event(self, event):
    with set_event(event):
      for handler in self.__handlers:
        if await handler.handle_event():
          return

  def __getattr__(self, name):
    return getattr(self.__client, name)
