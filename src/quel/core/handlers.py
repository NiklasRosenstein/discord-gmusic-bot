
from .client import MemberEventHandler, EventType, event

import re


class Command(MemberEventHandler):

  def __init__(self, func, regex, preconditions=None, case_sensitive=False):
    super().__init__(func)
    self.regex = re.compile(regex, 0 if case_sensitive else re.I)
    self.preconditions = preconditions or []

  async def handle_event(self, instance):
    if event.type == EventType.message and event.message.author != event.client.user:
      for precond in self.preconditions:
        if not precond():
          return False
      match = self.regex.match(event.text)
      if match is not None:
        await self.func(instance, *match.groups())
        return True
    return False


class On(MemberEventHandler):

  def __init__(self, func, event_type):
    super().__init__(func)
    if isinstance(event_type, str):
      event_type = getattr(EventType, event_type)
    assert isinstance(event_type, EventType)
    self.event_type = event_type

  async def handle_event(self, instance):
    if event.type == self.event_type:
      result = await self.func(instance)
      if result is None:
        result = True
      return result
    return False


command = Command.decorate
on = On.decorate
