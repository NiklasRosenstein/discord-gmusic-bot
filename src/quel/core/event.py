
import enum


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
event, set_event = async_local_proxy()
