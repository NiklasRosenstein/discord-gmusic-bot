
from quel.core.bot import MessageMultiplexer, CommandHandler, command


class PlayCommandHandler(CommandHandler):

  @command(regex='play\s+(.*)')
  async def play(self, url):
    await self.reply('Sorry, playing a song is currently not implemented.')


class ConfigCommandHandler(CommandHandler):

  @command(regex='config\s+([\w\d\.]+)\s+(.*)')
  async def config_set_value(self, key, value):
    await self.reply('Sorry, configuring stuff is not yet implemented.')

  @command(regex='config.*')
  async def config_fallback(self):
    await self.reply('Invalid syntax.')
