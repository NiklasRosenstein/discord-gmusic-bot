
import asyncio
import collections
import discord
import logging
import os
import urllib.request
import shutil

import config from './config'


class Song:

  def __init__(self, data, user, timestamp=None, message=None, stream=None):
    assert isinstance(data, dict) and 'storeId' in data, type(data)
    assert isinstance(user, discord.User), type(user)
    self.data = data
    self.user = user
    self.timestamp = timestamp
    self.message = message
    self.stream = stream

  def create_embed(self):
    if self.stream and self.stream.is_playing():
      state = 'playing'
    elif self.stream and not self.stream.is_done():
      state = 'paused'
    elif self.stream and self.stream.is_done():
      state = 'stopped'
    else:
      state = 'loading'

    lines = []
    lines.append('**Title** — {}'.format(self.data['title']))
    lines.append('**Artist** — {}'.format(self.data['artist']))
    lines.append('**Album** — {}'.format(self.data['album']))
    lines.append('**Genre** — {}'.format(self.data['genre']))
    embed = discord.Embed(
      timestamp=self.timestamp,
      description='\n'.join(lines),
      colour=discord.Colour.dark_teal(),
      url='https://google.com' # TODO: URL to play/queue the song again
    )
    embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
    for ref in self.data['albumArtRef']:
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


class Player:
  """
  Wraps around a #discord.VoiceChannel and keeps track of the current stream.
  """

  players = []

  @classmethod
  def get(cls, client, gmusic, voice_client):
    player = discord.utils.find(
      lambda x: x.voice_client == voice_client,
      cls.players)
    if player is None:
      player = cls(client, gmusic, voice_client)
      cls.players.append(player)
    return player

  @classmethod
  async def get_for_channel(cls, client, gmusic, channel):
    # Find the existing voice client for the channel.
    voice_client = discord.utils.find(
      lambda x: x.server == channel.server,
      client.voice_clients)
    if voice_client and voice_client.channel != channel:
      voice_client.move_to(channel)
    elif not voice_client:
      voice_client = await client.join_voice_channel(channel)
    return cls.get(client, gmusic, voice_client)

  @classmethod
  async def get_for_server(cls, server):
    return discord.utils.find(
      lambda x: x.voice_client.server == server,
      cls.players)

  def __init__(self, client, gmusic, voice_client):
    self.client = client
    self.loop = client.loop
    self.gmusic = gmusic
    self.voice_client = voice_client
    self.lock = asyncio.Lock()
    self.current_song = None
    self.process_queue = True
    self.queue = []

  @property
  def server(self):
    return self.voice_client.server

  async def has_current_song(self):
    with await self.lock:
      return bool(self.current_song)

  async def is_playing(self):
    with await self.lock:
      if self.current_song and self.current_song.stream:
        return self.current_song.stream.is_playing()
    return False

  async def pause(self):
    with await self.lock:
      if self.current_song and self.current_song.stream:
        self.process_queue = False
        self.current_song.stream.pause()
        await self.__update_current_song_message()

  async def resume(self):
    with await self.lock:
      if self.current_song and self.current_song.stream:
        self.process_queue = True
        self.current_song.stream.resume()
        await self.__update_current_song_message()

  async def stop(self):
    with await self.lock:
      self.process_queue = False
    await self.__kill_stream()
    with await self.lock:
      await self.__update_current_song_message()

  async def __start_ffmpeg_stream(self, *args, **kwargs):
    with await self.lock:
      if self.current_song and self.current_song.stream:
        raise RuntimeError('cant start a new stream if another is still playing')
      kwargs['after'] = lambda: asyncio.run_coroutine_threadsafe(self.__kill_stream(), self.loop)
      self.current_song.stream = self.voice_client.create_ffmpeg_player(*args, **kwargs)
      self.current_song.stream.start()

  async def __update_current_song_message(self):
    if self.current_song and self.current_song.message:
      await self.client.edit_message(
        self.current_song.message,
        embed=self.current_song.create_embed()
      )

  async def __kill_stream(self):
    with await self.lock:
      if self.current_song and self.current_song.stream:
        self.current_song.stream.stop()
      try:
        await self.__update_current_song_message()
      except Exception as e:
        logging.exception(e)
      self.current_song = None

  async def __play_song(self, song):
    if await self.is_playing():
      logging.error('can not play song, already playing another')
      return False

    with await self.lock:
      if not song.message:
        song.message = await self.client.say(embed=song.create_embed())
      self.current_song = song

    song_id = song.data['storeId']
    os.makedirs(config.song_cache_dir, exist_ok=True)
    filename = os.path.join(config.song_cache_dir, song_id + '.mp3')
    if not os.path.isfile(filename):
      url = self.gmusic.get_stream_url(song_id)
      try:
        response = urllib.request.urlopen(url)
      except (urllib.error.URLError, urllib.error.HTTPError) as e:
        logging.error(e)
        return
      with open(filename, 'wb') as fp:
        shutil.copyfileobj(response, fp)

    logging.info('Starting playback.')
    await self.__start_ffmpeg_stream(filename)
    await self.__update_current_song_message()

  async def queue_song(self, song_data, user, timestamp):
    with await self.lock:
      song = Song(song_data, user, timestamp)
      if self.current_song:
        self.queue.append(song)
        play_immediately = False
      else:
        play_immediately = True
    if play_immediately:
      logging.info('Immediately playing')
      return await self.__play_song(song)


module.exports = Player
