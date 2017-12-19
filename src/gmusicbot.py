
import asyncio
import collections
import contextlib
import functools
import discord, discord.ext.commands
import logging
import gmusicapi
import os
import random
import re
import signal
import subprocess
import sys
import time
import toml
import urllib.parse

import Player from './Player'


def async_partial(func, *pargs, **pkwargs):
  assert asyncio.iscoroutinefunction(func), func
  @functools.wraps(func)
  async def wrapper(*args, **kwargs):
    kwargs.update(pkwargs)
    return await func(*(pargs + args), **kwargs)
  return wrapper


class GMusicBot:

  Command = collections.namedtuple('Command', 'name handler')
  COMMANDS = []
  EVENTHANDLERS = []

  @classmethod
  def command(cls, name=None):
    def decorator(func):
      cls.COMMANDS.append(cls.Command(name or func.__name__, func))
      return func
    return decorator

  @classmethod
  def event(cls, func):
    cls.EVENTHANDLERS.append(func)
    return func

  def __init__(self, config, reloader=None):
    self.logger = logging.getLogger('discord-gmusic-bot')
    self.logger.setLevel(logging.INFO)
    self.client = None
    self.gmusic = gmusicapi.Mobileclient(debug_logging=False)
    self.reloader = reloader
    self.config = config
    self.players = Player.Factory(self.client, self.gmusic, self.config, self.logger)

    with module.package.directory.joinpath('resources/thanks.txt').open() as fp:
      thanks_urls = list([x.split(',')[1] for x in fp if x.strip()])

  def run(self):
    # Log-in to the Google Music API.
    if not self.gmusic.login(
        self.config['gmusic']['username'],
        self.config['gmusic']['password'],
        gmusicapi.Mobileclient.FROM_MAC_ADDRESS):
      self.logger.error('Unable to authenticate with Google Play Music.')
      return 1

    # Load the Opus codec.
    if os.name == 'nt':
      dll_name = self.config['windows']['opus_dll']
      self.logger.info('Loading {} ...'.format(dll_name))
      discord.opus.load_opus(dll_name)
    if not discord.opus.is_loaded():
      self.logger.error('Opus not loaded.')
      return 1

    # Initialize the Discord bot client.
    self.client = discord.Client()
    self.client.event(self.on_message)
    for handler in self.EVENTHANDLERS:
      self.client.event(async_partial(handler, self))
    self.players.client = self.client

    # Run the client.
    self.client.run(self.config['discord']['token'])
    self.logger.info('Bye, bye.')
    return 0

  def check_command_prefix(self, message):
    if message.channel.topic and 'discord-gmusic-bot' in message.channel.topic:
      return ''
    else:
      return self.client.user.mention

  async def on_message(self, message):
    prefix = self.check_command_prefix(message)
    if not message.content.startswith(prefix):
      return
    content = message.content[len(prefix):].lstrip()
    for command in self.COMMANDS:
      match = re.match('^{}(\s|$)'.format(re.escape(command.name)), content)
      if match:
        content = content[match.end():].lstrip()
        await command.handler(self, message, content)
        return

  async def get_invite_link(self):
    client_id = (await self.client.application_info()).id
    return self.config['discord']['add_bot_url'].format(CLIENT_ID=client_id)


@GMusicBot.command()
async def help(self, message, query):
  await self.client.send_typing(message.channel)
  name = message.channel.server.me.nick or self.client.user.name
  icon_url = message.channel.server.me.avatar_url or self.client.user.avatar_url
  embed = discord.Embed()
  embed.add_field(
    name='help',
    value='Show this message.',
    inline=False
  )
  embed.add_field(
    name='play',
    value='Resume playing from the queue. If the queue is empty, play a '
          'random song.',
    inline=False
  )
  embed.add_field(
    name='play <query>',
    value='Query can be a Youtube URL or a search query for Google Music. '
          'Adds the Youtube Video or the first song returned by the search '
          'query to the queue.',
    inline=False
  )
  embed.add_field(
    name='queue',
    value='Show the tracks currently in the queue.',
    inline=False
  )
  embed.add_field(
    name='queue <query>',
    value='Alias for `play <query>`.',
    inline=False
  )
  embed.add_field(
    name='pause',
    value='Pause the playback.',
    inline=False
  )
  embed.add_field(
    name='stop',
    value='Stop the playback and remove the curent song from the tip of the queue.',
    inline=False
  )
  embed.add_field(
    name='skip',
    value='Play the next song in the queue.',
    inline=False
  )
  embed.add_field(
    name='search <query>',
    value='Show the first 10 search results from Google Music.',
    inline=False
  )
  embed.add_field(
    name='Invite Link for this Bot',
    value=await self.get_invite_link(),
    inline=False
  )
  await self.client.send_message(message.channel, embed=embed)


@GMusicBot.command()
async def queue(self, message, query, reply_to_user=False):
  user = message.author
  if not query:
    player = await self.players.get_player_for_server(user.server)
    embed = discord.Embed()
    for song in (player.queue if player else []):
      if song.type == Player.GmusicSong:
        embed.add_field(
          name='{} - {}'.format(song.data['title'], song.data['artist']),
          value='added by {}'.format(song.user.mention),
          inline=False
        )
      elif song.type == Player.YoutubeSong:
        embed.add_field(
          name=song.name,
          value='added by {}'.format(song.user.mention),
          inline=False
        )
    await self.client.send_message(message.channel, embed=embed)
    return

  if not message.author.voice.voice_channel:
    await self.client.send_message(message.channel, '{} Join a voice channel, first.'.format(message.author.mention))
    return

  url = query.strip().lstrip('<').rstrip('>')
  info = urllib.parse.urlparse(url)
  if info.scheme and info.netloc and info.path:
    if 'youtu' in info.netloc:
      player = await self.players.get_player_for_voice_channel(message.author.voice.voice_channel)
      song = await player.queue_song(Player.YoutubeSong, url, user, message.channel, message.timestamp)
    else:
      await self.client.send_message(message.channel, 'That doesn\'t look like a Youtube URL.')
      return
  else:
    results = self.gmusic.search(query, max_results=10)
    if not results['song_hits']:
      await self.client.send_message(message.channel, '{} Sorry, seems like Google Music sucks.'.format(user.mention))
      return

    song_data = results['song_hits'][0]['track']
    player = await self.players.get_player_for_voice_channel(message.author.voice.voice_channel)
    song = await player.queue_song(Player.GmusicSong, song_data, user, message.channel, message.timestamp)

  if song and not song.stream and reply_to_user:
    await self.client.send_message(message.channel, '{} I\'ve added **{}** to the queue.'.format(user.mention, song.name))


@GMusicBot.command()
async def search(self, message, query):
  user = message.author
  await self.client.send_typing(message.channel)
  results = self.gmusic.search(query, max_results=10)
  embed = discord.Embed(title='Results for {}'.format(query))
  for song in results['song_hits']:
    song = song['track']
    embed.add_field(
      name=song['title'],
      value='by {}'.format(song['artist']),
      inline=False
    )
  await self.client.send_message(message.channel, embed=embed)


@GMusicBot.command()
async def play(self, message, query):
  if not message.author.voice.voice_channel:
    await self.client.send_message(message.channel, '{} Join a voice channel, first.'.format(message.author.mention))
    return

  player = await self.players.get_player_for_voice_channel(message.author.voice.voice_channel)
  if query:
    await queue(self, message, query, reply_to_user=True)
    return

  user = message.author
  await self.client.send_typing(message.channel)
  if not await player.has_current_song() and not player.queue:
    await self.client.send_message(message.channel, '{} Playing a random song.'.format(user.mention))
    song = random.choice(self.gmusic.get_promoted_songs())
    await player.queue_song(Player.GmusicSong, song, user, message.channel, message.timestamp)
    await player.resume()
  elif not await player.is_playing():
    await player.resume()


@GMusicBot.command()
async def pause(self, message, arg):
  player = await self.players.get_player_for_server(message.server)
  if player and await player.is_playing():
    self.logger.info('Pausing playback.')
    await player.pause()


@GMusicBot.command()
async def stop(self, message, arg):
  player = await self.players.get_player_for_server(message.server)
  if player:
    self.logger.info('Stopping playback.')
    await player.stop()


@GMusicBot.command()
async def skip(self, message, arg):
  player = await self.players.get_player_for_server(message.server)
  if player:
    await player.skip_song()
    await player.resume()


@GMusicBot.command()
async def reload(self, message, arg):
  if not self.config['debug']['use_reloader']:
    await self.client.send_message(message.channel, 'Reloading is disabled.')
  elif not self.reloader.is_inner():
    await self.client.send_message(message.channel, 'Not inside the reloaded process. OMG')
  else:
    self.reloader.send_reload()


@GMusicBot.command()
async def thanks(self, message, arg):
  url = random.choice(thanks_urls)
  embed = discord.Embed()
  embed.set_image(url=url)
  await self.client.send_message(message.channel, embed=embed)


@GMusicBot.event
async def on_ready(self):
  self.logger.info('discord-gmusic-bot is ready.')
  self.logger.info('Add the bot to your Server:')
  self.logger.info('')
  self.logger.info('        {}'.format(await self.get_invite_link()))
  self.logger.info('')


module.exports = GMusicBot
