
from pony import orm
from quel import db
from quel.db.utils import create_or_update
from quel.core.client import Client
from quel.core.event import event
from quel.core.handlers import on, command
from quel.core.reloader import Reloader
from quel.providers.soundcloud import SoundCloudProvider
from urllib.parse import urlparse

import argparse
import discord
import logging
import json
import os
import sys


client = Client()

providers = [
  SoundCloudProvider()
]

logger = logging.getLogger(__name__)

reloader = Reloader()


@orm.db_session
def get_guild(guild_id=None):
  guild_id = guild_id or event.message.guild.id
  return create_or_update(db.Guild, {'id': guild_id})


@on(client, 'ready')
async def ready():
  logger.info('Loading providers for all servers.')
  for guild in client.guilds:
    await provider_reload(guild)


@command(client, regex='config\s+set\s+([\w\d\.]+)\s+(.*)')
async def config_set(key, value):
  with orm.db_session:
    guild = get_guild()
    guild.config[key] = value
    await provider_reload()


@command(client, regex='config\s+del\s+([\w\d.]+)')
async def config_del(key):
  with orm.db_session:
    guild = get_guild()
    guild.config.pop(key, None)
    await provider_reload()


@command(client, regex='providers?\s+reload')
async def provider_reload(guild=None):
  with orm.db_session:
    guild = get_guild(guild.id if guild else None)
    guild.init_providers(logger, providers, force=True)


@command(client, regex='providers?\s+status')
async def provider_status():
  guild = get_guild()
  if not guild.providers:
    await event.reply('No providers installed.')
  for provider in guild.providers:
    message = provider.error or 'Ok'
    await event.reply('**{}**: {}'.format(provider.provider.name, message))


@command(client, regex='providers?\s+help')
async def provider_help():
  for provider in providers:
    lines = ['- ' + x for x in provider.get_option_names()]
    await event.reply('**{}**\n```\n{}\n```'.format(provider.name, '\n'.join(lines)))


@command(client, regex='search\s+(?:(\w+):\s*)?(.*)')
async def search(provider_name, term):
  with orm.db_session:
    guild = get_guild()
  if provider_name:
    provider_name = provider_name.lower()
    for provider in providers:
      if provider.id.lower() == provider_name or provider.name.lower() == provider_name:
        break
    else:
      await event.reply('"{}" is an unknown provider'.format(provider_name))
      return
    for instance in guild.providers:
      if not instance.error and instance.provider == provider:
        break
    else:
      await event.reply('Provider "{}" is not (properly) installed'.format(provider.name))
      return
    search_providers = [instance]
  else:
    search_providers = [x for x in guild.providers if not x.error]
    if not search_providers:
      await event.reply('No providers available.')
      return

  embed = discord.Embed(title='Results for "{}"'.format(term))
  for provider in search_providers:
    async for song in provider.search(term, 5):
      embed.add_field(name=song.title, value=song.url)
  await event.reply(embed=embed)


@command(client, regex='play\s+(.*)')
async def handle_url(arg):
  guild = get_guild()
  errors = []
  songs = []
  for url in map(str.strip, arg.split(';')):
    urlinfo = urlparse(url)
    if not urlinfo.netloc or not urlinfo.scheme:
      errors.append('Invalid URL `{}`'.format(url))
    else:
      for provider in guild.providers:
        if provider.match_url(url, urlinfo):
          song = await provider.resolve_url(url)
          song = db.QueuedSong(
            user_id=event.message.author.id,
            provider_id=provider.id,
            **song.asdict())
          songs.append(song)
          break
      else:
        errors.append('No provider for URL `{}`'.format(url))
        continue

  if errors:
    await event.reply('\n'.join(errors))

  lines = []
  for song in songs:
    lines.append('**{}** - {}'.format(song.title, song.artist))
    guild.queue_song(song)

  await resume()


@command(client, regex='resume')
async def resume():
  guild = get_guild()

  if guild.voice_client and guild.voice_client.source:
    guild.voice_client.resume()
    return

  if not guild.queue:
    if guild.voice_client:
      await guild.voice_client.disconnect()
      guild.voice_client = None
    return

  if not guild.voice_client:
    voice_state = event.message.author.voice
    voice_channel = voice_state.channel if voice_state else None
    if not voice_channel:
      await event.reply('Join a voice channel and type `resume` to start playing music!')
      return
    guild.voice_client = await voice_channel.connect()

  song = guild.queue.pop(0)
  provider = guild.find_provider(song.provider_id)
  if not provider:
    logger.error('Provider for queued Song no longer exists: {}'.format(song.provider_id))
    return

  stream_url = await provider.get_stream_url(song)
  await guild.start_stream(stream_url)

  user = await client.get_user_info(song.user_id)
  await event.reply('Now playing! **{}** - {} (queued by {})'.format(song.title, song.artist, user.mention))


@command(client, regex='pause')
async def pause():
  guild = get_guild()
  if guild.voice_client and guild.voice_client.is_playing():
    guild.voice_client.pause()


@command(client, regex='skip')
async def pause():
  guild = get_guild()
  if guild.voice_client:
    guild.voice_client.stop()
  await resume()


@command(client, regex='stop')
async def stop():
  guild = get_guild()
  if guild.voice_client:
    guild.voice_client.stop()
    await guild.voice_client.disconnect()
    guild.voice_client = None


@command(client, regex='queue')
async def queue():
  with orm.db_session:
    guild = get_guild()

  embed = discord.Embed(title='Queued songs')
  for song in guild.queue:
    embed.add_field(name=song.title, value=song.artist)
  await event.reply(embed=embed)


@command(client, regex='reload')
async def reload():
  if reloader.is_inner():
    reloader.send_reload()
  else:
    await event.reply('Reloading not enabled.')


"""
@command(client, regex='config\s+conversation')
async def config_conversation():
  user = self.local.message.author
  private_channel = await self.client.start_private_message(user)
  async def reply(message):
    return await self.client.send_message(private_channel, message)
  await reply('Hi! For the next 5 minutes you can send commands to me in '
              'private. Use this to set up credentials for music providers.')
  self.user_for_server[user.id] = self.local.message.server
"""


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--config', default='config.json')
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('-r', '--reload', action='store_true')
  args = parser.parse_args()

  with open(args.config) as fp:
    config = json.load(fp)

  loglevel = logging.INFO if args.verbose else logging.WARNING
  logformat = config.get('logging', {}).get('format')
  if not logformat:
    logformat = '[%(levelname)s %(name)s %(asctime)s]: %(message)s'
  logging.basicConfig(format=logformat, level=loglevel)

  if args.reload and not reloader.is_inner():
    logger.info('Starting reloader ...')
    return reloader.run_forever([sys.executable, '-m', 'quel.main'] + sys.argv[1:])

  logger.info('Binding database ...')
  if 'filename' in config['dbConfig']:
    config['dbConfig']['filename'] = os.path.abspath(config['dbConfig']['filename'])
  db.db.bind(**config['dbConfig'])
  db.db.generate_mapping(create_tables=True)

  logger.info('Starting ...')
  client.run(config['botConfig']['token'])
  logger.info('Bye bye.')


if __name__ == '__main__':
  main()
