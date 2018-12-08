
from quel.core.bot import CommandHandler, command
from quel.provider import available_providers
from quel.models import User
from pony import orm
from .server import PlayError

import json


class PlayCommandHandler(CommandHandler):

  @command(regex='play\s+(.*)')
  async def play(self, url):
    message = self.local.message
    manager = self.bot.manager
    server = await self.bot.manager.get_server_data(message.server)
    with orm.db_session():
      user = User.for_discord_user(message.author)
      try:
        song = await server.queue_song_by_url(user, url,
          join_channel=message.author.voice.voice_channel)
      except PlayError as exc:
        await self.reply(str(exc))
        return
    if song is None:
      await self.reply("I don't know how to play this.")
    else:
      await self.reply("Queued **{}** by **{}**".format(song.title, song.artist))
    return


class ConfigCommandHandler(CommandHandler):

  async def before_command(self, message, command, data):
    self.local.server = await self.bot.manager.get_server_data(message.server)

  @command(regex='config\s+set\s+([\w\d\.]+)\s+(.*)')
  async def config_set(self, key, value):
    provider, key = key.partition('.')[::2]
    if not provider or not key:
      await self.reply('Invalid key. Must be in the format `provider.key`')
      return
    if provider not in available_providers:
      await self.reply('`{}` is not a known provider.'.format(provider))
      return
    with orm.db_session():
      data = self.local.server.get_db_object()
      options = data.get_provider_options(provider)
      options[key] = value
      data.set_provider_options(provider, options)
    await self.reply('Done. Use `config apply` to apply the changes.')

  @command(regex='config\sdel\s+([\w\d.]+)')
  async def command_del(self, key):
    provider, key = key.partition('.')[::2]
    if not provider:
      await self.reply('Invalid key. Must be either `provider` or `provider.key`')
      return
    if provider not in available_providers:
      await self.reply('`{}` is not a known provider.'.format(provider))
      return
    with orm.db_session():
      data = self.local.server.get_db_object()
      if key:
        options = data.get_provider_options(provider)
        options.pop(key, None)
        await self.reply('Done. Use `config apply` to apply the changes.')
      else:
        data.delete_provider_options(provider)
        await self.reply('Configuration for provider `{}` deleted. Use `config apply` to apply the changes.'.format(provider))

  @command(regex='config\s+show(\s+all)?')
  async def config_show(self, all):
    with orm.db_session():
      config = self.local.server.get_db_object().options
      if not all:
        config = config.get('providers', {})
      await self.reply('```\n{}\n```'.format(json.dumps(config, indent=2)))

  @command(regex='config\s+apply')
  async def config_update(self):
    await self.local.server.update_providers()
    await self.reply('Configuration applied.')

  @command(regex='config\s+status')
  async def config_status(self):
    lines = []
    for provider_id, provider_cls in available_providers.items():
      if provider_id in self.local.server.providers:
        msg = 'installed'
      else:
        msg = self.local.server.provider_errors.get(provider_id, 'not installed')
      name = provider_cls.get_provider_name()
      lines.append('{} ({})'.format(name, msg))
    await self.reply('```\n{}\n```'.format('\n'.join(lines)))

  @command(regex='config\s+help')
  async def config_help(self):
    lines = []
    for provider_id, provider_cls in available_providers.items():
      lines.append(provider_cls.get_provider_name())
      if provider_id in self.local.server.providers:
        lines[-1] += ' (installed)'
      elif provider_id in self.local.server.provider_errors:
        lines[-1] += ' ({})'.format(self.local.server.provider_errors[provider_id])
      for option in provider_cls.get_options():
        lines.append('  - {}.{}'.format(provider_id, option))
    await self.reply("Here's a list of the providers available and their options.")
    await self.reply("\n```\n{}\n```".format('\n'.join(lines)))

  @command(regex='reload\s*$')
  async def reload(self):
    await self.reply('Reloading!')
    self.bot.reloader.send_reload()


class FallbackHandler(CommandHandler):

  @command(regex='.*')
  async def fallback(self):
    await self.reply(self.local.message.author.mention + ' ?')
