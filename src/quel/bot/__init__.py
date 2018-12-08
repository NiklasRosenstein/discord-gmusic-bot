
from quel.core.bot import Bot, EventHandler, MessageMultiplexer, WeakHandlerWrapper
from quel.core.bot import requires_bot_mention, requires_channel_topic, either
from quel.core.reloader import Reloader
from .handlers import PlayCommandHandler, ConfigCommandHandler, FallbackHandler
from .server import ServerManager

import logging


class Quel(Bot, EventHandler):

  def __init__(self, config):
    super().__init__()
    self.config = config
    self.logger = logging.getLogger('Quel')
    self.reloader = Reloader()
    self.manager = None
    self.add_handler(WeakHandlerWrapper(self))
    self.add_handler(
      MessageMultiplexer(
        handlers=[
          PlayCommandHandler(),
          ConfigCommandHandler(),
          FallbackHandler(),
        ],
        preconditions=[either(
          requires_bot_mention(strip=True),
          requires_channel_topic('Quel', exact=True)
        )]
      )
    )

  async def handle_event(self, event_type, *args, **kwargs):
    if event_type == 'ready':
      await self.on_ready()

  async def on_ready(self):
    self.manager = ServerManager(self.client)

    self.logger.info('Ready.')

    client_id = (await self.client.application_info()).id
    invite_url = self.config['botConfig']['inviteUrl'].format(CLIENT_ID=client_id)
    self.logger.info('Bot Invite URL: {}'.format(invite_url))
