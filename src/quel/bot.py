
from . import models
from .utils.reloader import Reloader
from .server import ServerManager
from .provider import available_providers
from pony import orm

import discord
import logging
import json


config = None
bot = discord.Client()
logger = logging.getLogger(__name__)
reloader = Reloader()
manager = ServerManager(bot)


@bot.event
async def on_ready():
  logger.info('Ready.')

  client_id = (await bot.application_info()).id
  invite_url = config['botConfig']['inviteUrl'].format(CLIENT_ID=client_id)
  logger.info('Bot Invite URL: {}'.format(invite_url))


@bot.event
async def on_message(message):
  if message.author == bot.user:
    return

  manager.set_local_channel(message.channel)
  server = await manager.get_server_data(message.server)

  if message.content.startswith('set '):
    part = message.content.split(' ', 2)
    key, value = part[1:]
    provider, key = key.partition('.')[::2]
    if not provider or not key:
      await manager.message('Invalid key. Must be in the format `provider.key`')
      return
    if provider not in available_providers:
      await manager.message('`{}` is not a known provider.'.format(provider))
      return
    with orm.db_session():
      data = server.get_db_object()
      options = data.get_provider_options(provider)
      options[key] = value
      data.set_provider_options(provider, options)
    return

  elif message.content == 'update':
    await server.update_providers()
    return

  elif message.content == 'options':
    with orm.db_session():
      options = server.get_db_object().options
    await manager.message('```\n{}\n```'.format(json.dumps(options, indent=2)))
    return

  elif message.content.startswith('https://') or message.content.startswith('http://'):
    with orm.db_session():
      user = models.User.for_discord_user(message.author)
      song = await server.queue_song_by_url(user, message.content,
        join_channel=message.author.voice.voice_channel)
    if song is None:
      await manager.message("I don't know how to play this.")
    else:
      await manager.message("Queued **{}** by **{}**".format(song.title, song.artist))
    return


@bot.event
async def on_error(event_method, *args, **kwargs):
  logger.exception('Exception in {} (args: {}, kwargs: {})'
    .format(event_method, args, kwargs))
  await manager.message('**500 - Internal Server Error**')
