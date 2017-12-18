
import asyncio
import contextlib
import functools
import discord, discord.ext.commands
import logging
import gmusicapi
import os
import nodepy
import random
import re
import signal
import subprocess
import sys
import time
import urllib.parse

import config from './config'
import Player from './player'
import Reloader from './reloader'

logger = logging.getLogger('discord-gmusic-bot')
client = discord.ext.commands.Bot(None, description='Discord GMusic Bot')
gmusic = gmusicapi.Mobileclient(debug_logging=False)
reloader = Reloader()

with open(module.directory.joinpath('resources/thanks.txt')) as fp:
  thanks_urls = list([x.split(',')[1] for x in fp if x.strip()])


def handle_command_prefix(_, message):
  if message.channel.topic and 'discord-gmusic-bot' in message.channel.topic:
    return ''
  else:
    return client.user.mention

client.command_prefix = handle_command_prefix
client.remove_command('help')


async def get_player_for_context(ctx):
  user = ctx.message.author
  channel = user.voice.voice_channel
  if not channel:
    await client.say("{} Join a Voice Channel first.".format(user.mention))
    return None
  return await Player.get_for_channel(client, gmusic, channel)


@client.command(pass_context=True)
async def help(ctx):
  await client.type()
  name = ctx.message.channel.server.me.nick or client.user.name
  icon_url = ctx.message.channel.server.me.avatar_url or client.user.avatar_url
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
    value='Show the first 10 results that match the `<query>`.',
    inline=False
  )
  await client.say(embed=embed)


async def do_queue(ctx, query=None, play_query=None):
  if not query and not play_query:
    query = ctx.message.content.lstrip('queue').strip()
  elif not query:
    query = play_query

  user = ctx.message.author
  if not query:
    player = await Player.get_for_server(user.server)
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
    await client.say(embed=embed)
    return

  player = await get_player_for_context(ctx)
  if not player:
    return

  info = urllib.parse.urlparse(query)
  if info.scheme and info.netloc and info.path:
    if 'youtu' in info.netloc:
      await player.queue_song(Player.YoutubeSong, query, user, ctx.message.timestamp)
    else:
      await client.say('That doesn\'t look like a Youtube URL.')
    return

  results = gmusic.search(query, max_results=10)
  if not results['song_hits']:
    await client.say('{} Sorry, seems like Google Music sucks.'.format(user.mention))
    return

  song = results['song_hits'][0]['track']
  result = await player.queue_song(Player.GmusicSong, song, user, ctx.message.timestamp)
  if result == 'queued' and play_query:
    await client.say('{} I\'ve added *{} - {}* to the queue.'.format(user.mention, song['title'], song['artist']))


@client.command(pass_context=True)
async def queue(ctx):
  await do_queue(ctx)


@client.command(pass_context=True)
async def search(ctx, *query: str):
  user = ctx.message.author
  await client.type()

  query = ' '.join(query)
  results = gmusic.search(query, max_results=10)
  embed = discord.Embed(title='Results for {}'.format(query))
  for song in results['song_hits']:
    song = song['track']
    embed.add_field(
      name=song['title'],
      value='by {}'.format(song['artist']),
      inline=False
    )
  await client.say(embed=embed)


@client.command(pass_context=True)
async def play(ctx):
  player = await get_player_for_context(ctx)
  if not player:
    return

  query = ctx.message.content.lstrip('play').strip()
  if query:
    await do_queue(ctx, play_query=query)
    return

  user = ctx.message.author
  await client.type()
  if not await player.has_current_song() and not player.queue:
    client.say('{} Playing a random song.'.format(user.mention))
    song = random.choice(gmusic.get_promoted_songs())
    await player.queue_song(Player.GmusicSong, song, user, ctx.message.timestamp)
    await player.resume()
  elif not await player.is_playing():
    await player.resume()


@client.command(pass_context=True)
async def pause(ctx):
  player = await get_player_for_context(ctx)
  if player and await player.is_playing():
    logger.info('Pausing playback.')
    await player.pause()


@client.command(pass_context=True)
async def stop(ctx):
  player = await get_player_for_context(ctx)
  if player:
    logger.info('Stopping playback.')
    await player.stop()


@client.command(pass_context=True)
async def skip(ctx):
  player = await get_player_for_context(ctx)
  if player:
    await player.skip_song()
    await player.resume()


@client.command(pass_context=True)
async def reload(ctx):
  if not config.use_reloader:
    client.say('Reloading is disabled.')
  elif not reloader.is_inner():
    client.say('Not inside the reloaded process. OMG')
  else:
    reloader.send_reload()


@client.command(pass_context=True)
async def thanks(ctx):
  url = random.choice(thanks_urls)
  embed = discord.Embed()
  embed.set_image(url=url)
  await client.say(embed=embed)


@client.event
async def on_ready():
  client_id = (await client.application_info()).id
  logger.info('discord-gmusic-bot is ready.')
  logger.info('Add the bot to your Server:')
  logger.info('')
  logger.info('        {}'.format(config.discord_add_url.format(CLIENT_ID=client_id)))
  logger.info('')


def main():
  if config.use_reloader and not reloader.is_inner():
    argv = nodepy.runtime.exec_args + [str(module.filename)]
    reloader.run_forever(argv)
    return

  logging.basicConfig(level=logging.INFO)
  logger.setLevel(logging.INFO)

  # Log-in to the Google Music API.
  if not gmusic.login(config.gmusic_user, config.gmusic_password,
      gmusicapi.Mobileclient.FROM_MAC_ADDRESS):
    logger.error('Unable to authenticate with Google Play Music.')
    asyncio.wait(asyncio.ensure_future(client.close()))
    return 1

  # Load the Opus codec.
  if os.name == 'nt':
    logger.info('Loading {} ...'.format(config.win_opus_dll))
    discord.opus.load_opus(config.win_opus_dll)
  if not discord.opus.is_loaded():
    logger.error('Opus not loaded.')
    return 1

  client.run(config.discord_token)
  logger.info('Bye, bye.')


if require.main == module:
  sys.exit(main())
