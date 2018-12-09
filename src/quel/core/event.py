
import enum
import functools


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


from .utils import async_local_proxy
event, get_event, set_event = async_local_proxy()


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
