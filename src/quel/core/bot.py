
"""
Unified Discord bot client that creates the internal client lazily.
"""


from .asyncio_utils import async_local, async_partial, flush_local

import asyncio
import collections
import discord
import re
import weakref


ALL_EVENT_TYPES = [
  'on_ready',
  'on_resumed',
  'on_message',
  'on_message_delete',
  'on_message_edit',
  'on_reaction_add',
  'on_reaction_remove',
  'on_reaction_clear',
  'on_channel_delete',
  'on_chanel_create',
  'on_channel_update',
  'on_member_join',
  'on_member_remove',
  'on_member_update',
  'on_server_join',
  'on_server_remove',
  'on_server_update',
  'on_server_role_create',
  'on_server_role_delete',
  'on_server_role_update',
  'on_server_available',
  'on_server_unavailable',
  'on_voice_state_update',
  'on_member_ban',
  'on_typing',
  'on_group_join',
  'on_group_remove',
]


class Bot:

  def __init__(self):
    self._client = None
    self._local = async_local()
    self._handlers = []

  @property
  def client(self):
    return self._client

  def run(self, *args, **kwargs):
    self._client = discord.Client()
    for event_type in ALL_EVENT_TYPES:
      assert event_type.startswith('on_'), event_type
      handler = async_partial(self.dispatch_event, event_type[3:])
      handler.__name__ = event_type
      self._client.event(handler)
    return self._client.run(*args, **kwargs)

  def add_handler(self, handler):
    self._handlers.append(handler)
    handler.connect(self)

  async def dispatch_event(self, event_type, *args, **kwargs):
    for handler in self._handlers:
      result = await handler.handle_event(event_type, *args, **kwargs)
      if result:
        break
      flush_local(self._local)


class EventHandler:

  _bot = None

  @property
  def bot(self):
    return self._bot() if self._bot is not None else None

  @property
  def client(self):
    if self._bot is not None:
      return self._bot()._client
    return None

  @property
  def local(self):
    if self._bot is not None:
      return self._bot()._local
    return None

  def connect(self, bot):
    self._bot = weakref.ref(bot)

  async def handle_event(self, event_type, *args, **kwargs):
    pass


class WeakHandlerWrapper(EventHandler):

  def __init__(self, handler):
    self._handler = weakref.ref(handler)

  @property
  def handler(self):
    return self._handler() if self._handler is not None else None

  def connect(self, bot):
    handler = self.handler
    if handler:
      handler.connect(bot)

  async def handle_event(self, event_type, *args, **kwargs):
    handler = self.handler
    if handler is not None:
      return await handler.handle_event(event_type, *args, **kwargs)
    return False


class MessageHandler(EventHandler):

  async def match_message(self, message):
    return False

  async def handle_message(self, message):
    return False

  async def reply(self, text):
    return await self.client.send_message(self.local.message.channel, text)

  async def handle_event(self, event_type, *args, **kwargs):
    if event_type == 'message' and await self.match_message(args[0]):
      self.local.message = args[0]
      await self.handle_message(args[0])
      return True
    return False


class MessageMultiplexer(MessageHandler):

  def __init__(self, handlers=None, preconditions=None):
    self._handlers = handlers or []
    self.preconditions = preconditions or []

  def add_handler(self, handler):
    self._handlers.append(handler)

  async def match_message(self, message):
    for precond in self.preconditions:
      if not precond(self.bot, message):
        return False
    for handler in self._handlers:
      if await handler.match_message(message):
        self.local.handler = handler
        return True
    return False

  async def handle_message(self, message):
    return await self.local.handler.handle_message(message)

  def connect(self, bot):
    super().connect(bot)
    for handler in self._handlers:
      handler.connect(bot)


class CommandHandler(MessageHandler):

  def __init__(self):
    self._commands = []
    for key in dir(self):
      value = getattr(self, key)
      if isinstance(value, command):
        self._commands.append(value)
    self._commands.sort(key=lambda x: x.order_index)

  preconditions = []

  async def before_command(self, message, command, match):
    pass

  async def match_message(self, message):
    if message.author == self.client.user:
      return False
    for precond in self.preconditions:
      if not precond(self.bot, message):
        return False
    for command in self._commands:
      match = command.match(self.bot, message)
      if match is not None:
        self.local.match = match
        self.local.command = command
        return True

  async def handle_message(self, message):
    match = self.local.match
    await self.before_command(message, self.local.command, match)
    await self.local.command.func(self, *match.args, **match.kwargs)


class command:
  """
  Decorator for methods of the #CommandHandler class that match on
  specific prefixes in a message.
  """

  Match = collections.namedtuple('Match', 'args kwargs')
  _current_order_index = 0

  def __init__(self, prefix=None, regex=None, case_sensitive=False,
               matcher=None, preconditions=None):
    if prefix and not case_sensitive:
      prefix = prefix.lower()
    if isinstance(regex, str):
      regex = re.compile(regex, 0 if case_sensitive else re.I)
    self._func = None
    self._prefix = prefix
    self._regex = regex
    self._matcher = matcher
    self._case_sensitive = case_sensitive
    self._preconditions = preconditions or []
    self._order_index = command._current_order_index
    command._current_order_index += 1

  def __call__(self, func):
    assert asyncio.iscoroutinefunction(func)
    self._func = func
    return self

  def match(self, bot, message):
    for precond in self._preconditions:
      if not precond(bot, message):
        return None
    if self._prefix is not None:
      message = message.content
      if not self._case_sensitive:
        message = message[:len(self._prefix)].lower()
      if message.startswith(self._prefix):
        return self.Match([message[len(self._prefix):]], {})
    elif self._regex is not None:
      message = message.content
      match = self._regex.match(message)
      if match is not None:
        return self.Match(match.groups(), {})
    elif self._matcher is not None:
      return self._matcher(bot, message)
    return None

  @property
  def func(self):
    return self._func

  @property
  def order_index(self):
    return self._order_index


def requires_bot_mention(strip=True):
  """
  A precondition for #CommandHandler implementations. Requires that the bot
  be mentioned before the command can match. If *strip* is `True`, the
  mention will be stripped from the mesasge content.
  """

  def requires_bot_mention_precond(bot, message):
    if not message.content.startswith(bot.client.user.mention):
      return False
    message.content = message.content[len(bot.client.user.mention):].lstrip()
    return True

  return requires_bot_mention_precond


def requires_channel_topic(topic, exact=True):
  """
  A precondition for #CommandHandler implementations. Requires that the
  channel to which the message is sent has the specified *topic* (or
  contains it if *exact* is `False`).
  """

  def requires_channel_topic_precond(bot, message):
    channel_topic = message.channel.topic
    if exact: return channel_topic == topic
    else: return topic in channel_topic

  return requires_channel_topic_precond


def either(*preconditions):
  """
  A precondition that becomes true if any of the specified *preconditions*
  is `True`.
  """

  def either_precondition(bot, message):
    for precond in preconditions:
      if precond(bot, message):
        return True
    return False
  return either_precondition
