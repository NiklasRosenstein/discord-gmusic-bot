
import asyncio
import contextlib
import functools
import discord, discord.ext.commands
import logging
import gmusicapi
import os
import random
import re
import shutil
import sys
import time
import threading
import urllib.request

import config from './config'
import Player from './player'

logger = logging.getLogger('discord-gmusic-bot')
client = discord.ext.commands.Bot(
  command_prefix=discord.ext.commands.when_mentioned_or('/gmusic '),
  description='Discord GMusic Bot'
)
gmusic = gmusicapi.Mobileclient()


@contextlib.contextmanager
def make_read_pipe(src):
  """
  Create an OS-level readable pipe that is fed from the file-like object
  *src*. Returns a readable file-object.
  """

  pr, pw = os.pipe()
  thread = None
  try:
    fr, fw = os.fdopen(pr, 'rb'), os.fdopen(pw, 'wb')
    thread = threading.Thread(target=shutil.copyfileobj, args=[src, fw])
    thread.start()
    yield fr
  finally:
    if thread:
      thread.join()
    os.close(pr)
    os.close(pw)


def create_song_embed(author, song, timestamp=None, state='loading'):
  lines = []
  lines.append('**Title** — {}'.format(song['title']))
  lines.append('**Artist** — {}'.format(song['artist']))
  lines.append('**Album** — {}'.format(song['album']))
  lines.append('**Genre** — {}'.format(song['genre']))
  embed = discord.Embed(
    timestamp=timestamp,
    description='\n'.join(lines),
    colour=discord.Colour.dark_teal(),
    url='https://google.com' # TODO: URL to play/queue the song again
  )
  embed.set_author(name=author.name, icon_url=author.avatar_url)
  for ref in song['albumArtRef']:
    if 'url' in ref:
      embed.set_image(url=ref['url'])
      break
  if state == 'loading':
    embed.add_field(
      name='Controls',
      value='Loading...'
    )
  elif state == 'playing':
    embed.add_field(
      name='Controls',
      value='[⏸](https://github.com) [⏹️](https://discordapp.com)',
      inline=False
    )
  elif state == 'paused':
    embed.add_field(
      name='Controls',
      value='[▶️](https://google.com) [⏹️](https://discordapp.com)',
      inline=False
    )
  return embed


async def play_song(player, song_id, on_start_playing=None):
  # TODO: We should be able to stream the file directly from the URL to
  #       the create_ffmpeg_player() method, but it'll give an mp3 warning
  #       as it can't determine the full size:
  #
  #       [mp3 @ 0000000000d62340] invalid concatenated file detected - using bitrate for duration
  #
  #       And that seems to be the cause that only a small part of the track
  #       is actually played.
  #
  #       For now, we download every track into a cache folder.
  #       Once we figured out how to properly stream into ffmpeg, we can
  #       use the #mape_pipe() context manager:
  #
  #with make_read_pipe(response) as rp:
  #  player = voice_client.create_ffmpeg_player(rp, pipe=True)

  os.makedirs(config.song_cache_dir, exist_ok=True)
  filename = os.path.join(config.song_cache_dir, song_id + '.mp3')
  if not os.path.isfile(filename):
    url = gmusic.get_stream_url(song_id)
    try:
      response = urllib.request.urlopen(url)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
      logging.error(e)
      return
    with open(filename, 'wb') as fp:
      shutil.copyfileobj(response, fp)
  await player.start_ffmpeg_stream(filename)
  if on_start_playing:
    await on_start_playing()


async def get_player_for_context(ctx):
  user = ctx.message.author
  channel = user.voice.voice_channel
  if not channel:
    await client.say("{} Join a Voice Channel before playing.".format(user.mention))
    return None
  return await Player.get_for_channel(client, channel)


@client.command(pass_context=True)
async def play(ctx):
  client.delete_message(ctx.message)
  player = await get_player_for_context(ctx)
  if not player:
    return

  if player.stream and not await player.is_playing():
    logger.info('Resuming playback.')
    player.resume()
    player.done_callback()
    return

  user = ctx.message.author
  if player.stream:
    await client.say('{} A song is still playing.'.format(user.mention))
    return

  await client.type()
  song = random.choice(gmusic.get_promoted_songs())
  song_message = await client.say(
    embed=create_song_embed(
      user,
      song,
      timestamp=ctx.message.timestamp
    )
  )

  async def update_embed():
    if await player.is_playing():
      state = 'playing'
    elif player.stream:
      state = 'paused'
    else:
      state = 'stopped'
    await client.edit_message(
      song_message,
      embed=create_song_embed(
        user, song, timestamp=ctx.message.timestamp, state=state
      )
    )

  logger.info('Starting playing.')
  await play_song(player, song['storeId'], update_embed)
  player.done_callback = lambda: asyncio.run_coroutine_threadsafe(update_embed(), client.loop)


@client.command(pass_context=True)
async def pause(ctx):
  client.delete_message(ctx.message)
  player = await get_player_for_context(ctx)
  if player and await player.is_playing():
    logger.info('Pausing playback.')
    player.pause()
    player.done_callback()


@client.command(pass_context=True)
async def stop(ctx):
  client.delete_message(ctx.message)
  player = await get_player_for_context(ctx)
  if player and player.stream:
    logger.info('Stopping playback.')
    player.stop()


@client.event
async def on_ready():
  client_id = (await client.application_info()).id
  logger.info('discord-gmusic-bot is ready.')
  logger.info('Add the bot to your Server:')
  logger.info('')
  logger.info('        {}'.format(config.discord_add_url.format(CLIENT_ID=client_id)))
  logger.info('')


def main():
  logging.basicConfig(level=logging.ERROR)
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

  # Run the client in a separate thread, as the asyncio event loop seems
  # to block the keyboard interrupt from being captured in reasonable time.
  client_thread = threading.Thread(target=client.run, args=[config.discord_token])
  client_thread.start()

  # Buys-wait for the client thread to finish, or until an interrupt appears.
  while client_thread.is_alive():
    try:
      time.sleep(0.5)
    except KeyboardInterrupt:
      logger.info('Interrupt -- logging out discord client.')
      asyncio.gather(*asyncio.Task.all_tasks()).cancel()
      asyncio.wait(asyncio.ensure_future(client.logout()))
      break

  logger.info('Waiting for client thread to finish.')
  client_thread.join()
  gmusic.logout()
  logger.info('Bye, bye.')


if require.main == module:
  sys.exit(main())
