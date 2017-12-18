
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

import config from './config'
import Player from './player'
import Reloader from './reloader'

logger = logging.getLogger('discord-gmusic-bot')
client = discord.ext.commands.Bot(
  command_prefix=discord.ext.commands.when_mentioned_or('/gmusic '),
  description='Discord GMusic Bot'
)
gmusic = gmusicapi.Mobileclient()
reloader = Reloader()


async def get_player_for_context(ctx):
  user = ctx.message.author
  channel = user.voice.voice_channel
  if not channel:
    await client.say("{} Join a Voice Channel first.".format(user.mention))
    return None
  return await Player.get_for_channel(client, gmusic, channel)


@client.command(pass_context=True)
async def queue(ctx, *query: str):
  query = ' '.join(query).strip()
  user = ctx.message.author
  client.delete_message(ctx.message)
  await client.type()

  if (not query or query == 'show'):
    player = await Player.get_for_server(user.server)
    embed = discord.Embed(title='GMusic Queue')
    for song in (player.queue if player else []):
      embed.add_field(
        name='{} - {}'.format(song.data['track'], song.data['arist']),
        value='added by {}'.format(song.user.mention),
        inline=False
      )
    client.say(embed)
    return

  player = await get_player_for_context(ctx)
  if not player:
    return

  results = gmusic.search(query, max_results=1)
  if not results['song_hits']:
    client.say('{} No hits.'.format(user.mention))
    return

  # TODO: Put song on queue instead of playing immediately.
  song = results['song_hits'][0]['track']
  await player.queue_song(song, user, ctx.message.timestamp)


@client.command(pass_context=True)
async def search(ctx, *query: str):
  user = ctx.message.author
  client.delete_message(ctx.message)
  await client.type()

  query = ' '.join(query)
  results = gmusic.search(query, max_results=10)
  embed = discord.Embed(title='Results for {}'.format(query))
  embed.set_author(name=user.name, icon_url=user.avatar_url)
  for song in results['song_hits']:
    song = song['track']
    embed.add_field(
      name=song['title'],
      value='by {}'.format(song['artist']),
      inline=False
    )
  await client.say(embed=embed)


@client.command(pass_context=True)
async def play(ctx, *query: str):
  client.delete_message(ctx.message)
  player = await get_player_for_context(ctx)
  if not player:
    return

  if query:
    await queue.callback(ctx, *query)
    return

  user = ctx.message.author
  await client.type()
  if not await player.has_current_song() and not player.queue:
    client.say('{} Playing a random song.'.format(user.mention))
    song = random.choice(gmusic.get_promoted_songs())
    await player.queue_song(song, user, ctx.message.timestamp)
    await player.resume()
  elif not await player.is_playing():
    await player.resume()


@client.command(pass_context=True)
async def pause(ctx):
  client.delete_message(ctx.message)
  player = await get_player_for_context(ctx)
  if player and await player.is_playing():
    logger.info('Pausing playback.')
    await player.pause()


@client.command(pass_context=True)
async def stop(ctx):
  client.delete_message(ctx.message)
  player = await get_player_for_context(ctx)
  if player:
    logger.info('Stopping playback.')
    await player.stop()


@client.command(pass_context=True)
async def reload(ctx):
  if not config.use_reloader:
    client.say('Reloading is disabled.')
  elif not reloader.is_inner():
    client.say('Not inside the reloaded process. OMG')
  else:
    reloader.send_reload()


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
