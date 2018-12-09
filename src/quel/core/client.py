

from .event import Event, EventType, MessageEvent, set_event
from .utils import async_partial

import discord


def prepare_ready(client):
  return Event(EventType.ready, client)


def prepare_message(client, message):
  return MessageEvent(client, message)


#def prepare_error(event_method, *args, **kwargs):
#  return Event(EventType.error, event_method=event_method, args=args, kwargs=kwargs)


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
    self.__handlers.append(handler)

  async def dispatch_event(self, event):
    with set_event(event):
      for handler in self.__handlers:
        if await handler():
          return

  def __getattr__(self, name):
    return getattr(self.__client, name)
