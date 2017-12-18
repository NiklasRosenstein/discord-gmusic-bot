
import asyncio
import contextlib
import discord
import logging
import gmusicapi
import os
import re
import shutil
import sys
import time
import threading
import urllib.request

import config from './config'
import Player from './player'

logger = logging.getLogger('discord-gmusic-bot')
client = discord.Client()
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


async def play_song(player, song_id):
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


@client.event
async def on_message(message):
  if not re.match('/gmusic(\s|$)', message.content):
    return

  user = message.author
  args = re.split('\s+', message.content, 2)[1:]
  print(args)
  if len(args) == 0:
    await client.send_message(message.channel, "TODO: Show general information about gmusic bot.")
    return
  elif args[0] == 'play':
    if not user.voice.voice_channel:
      await client.add_reaction(message, '🤦')
      await client.send_message(message.channel, "Join a Voice Channel before playing.")
      return
    player = await Player.get_for_channel(client, user.voice.voice_channel)
    if await player.is_playing():
      # TODO: Discord doesn't recogise the warning emoji ..
      #await client.add_reaction(message, '⚠️')
      await client.send_message(message.channel, "reaction: :warning:")
      return
    # TODO: Parse additional arguments to search for songs.
    await client.add_reaction(message, '👍')
    song = gmusic.get_promoted_songs()[0]
    await client.send_message(message.channel, 'Playing: {} by {}'.format(song['title'], song['artist']))
    await play_song(player, song['storeId'])
    return
  else:
    await client.add_reaction(message, '❓')
    return


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
    opus_filename = config.win_opus_dll
    if not os.path.isabs(opus_filename):
      opus_filename = str(module.directory.joinpath(config.win_opus_dll))
    logger.info('Loading {} ...'.format(opus_filename))
    discord.opus.load_opus(opus_filename)
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
