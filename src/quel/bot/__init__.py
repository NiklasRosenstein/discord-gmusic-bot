
from quel.core.bot import Bot
from .handlers import PlayCommandHandler, ConfigCommandHandler, MessageMultiplexer
from quel.core.bot import requires_bot_mention, requires_channel_topic, either

import logging


class Quel(Bot):

  def __init__(self, config):
    super().__init__()
    self.config = config
    self.logger = logging.getLogger('Quel')
    self.add_handler(
      MessageMultiplexer(
        handlers=[
          PlayCommandHandler(),
          ConfigCommandHandler(),
        ],
        preconditions=[either(
          requires_bot_mention(strip=True),
          requires_channel_topic('Quel', exact=True)
        )]
      )
    )
