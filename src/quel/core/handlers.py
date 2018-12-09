
from .event import EventType, event

import asyncio
import re


class Command:

  def __init__(self, func, regex, preconditions=None, case_sensitive=False):
    assert asyncio.iscoroutinefunction(func)
    self.func = func
    self.regex = re.compile(regex, 0 if case_sensitive else re.I)
    self.preconditions = preconditions or []

  async def __call__(self):
    if event.type == EventType.message and event.message.author != event.client.user:
      for precond in self.preconditions:
        if not precond():
          return False
      match = self.regex.match(event.text)
      if match is not None:
        await self.func(*match.groups())
        return True
    return False


def command(client, *args, **kwargs):
  def decorator(func):
    client.add_handler(Command(func, *args, **kwargs))
    return func
  return decorator


def on(client, event_type):
  if isinstance(event_type, str):
    event_type = getattr(EventType, event_type)
  def decorator(func):
    assert asyncio.iscoroutinefunction(func)
    async def handler():
      if event.type == event_type:
        return await func()
    client.add_handler(handler)
    return func
  return decorator
