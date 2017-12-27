
import asyncio
import collections
import discord
import enum
import gmusicapi
import os
import re
import shutil
import urllib.request, urllib.parse
import youtube_dl


class StreamNotCreatedError(Exception):
  pass


class SongTypes(enum.Enum):
  Gmusic = 'gmusic'
  Youtube = 'youtube'


class Song:

  def __init__(self, type, data, user, channel, timestamp=None, message=None, gmusic=None):
    self.type = type
    if type == SongTypes.Gmusic:
      assert isinstance(data, dict) and 'storeId' in data, type(data)
      if not gmusic:
        raise ValueError('Need a gmusic Client for a GMusic song')

      self.title = data['title']
      self.artist = data['artist']
      self.album = data['album']
      self.genre = data['genre']
      self.image = None
      self.song_id = data['storeId']
      self.gmusic_data = data
      self.gmusic = gmusic

      for ref in data['albumArtRef']:
        if 'url' in ref:
          self.image = ref['url']
          break

    elif type == SongTypes.Youtube:
      assert isinstance(data, str), type(data)
      self.title = None
      self.artist = None
      self.album = None
      self.genre = None
      self.image = None
      self.url = data

      # Normalize the Youtube video URL. This will ensure that we extract
      # the video ID also from video URLs that point to a video in a
      # playlist.
      info = urllib.parse.urlparse(self.url)
      if info.netloc != 'youtu.be':
        query = urllib.parse.parse_qs(info.query)
        if not query.get('v'):
          raise ValueError('Invalid Youtube video URL: {!r}'.format(self.url))
        self.url = 'https://youtu.be/' + query['v'][0]

    else:
      raise ValueError('invalid song type: {!r}'.format(type))

    assert isinstance(user, discord.User), type(user)
    self.user = user
    self.channel = channel
    self.timestamp = timestamp
    self.message = message
    self.stream = None

  def __repr__(self):
    return '<Song type={!r} user={!r}>'.format(self.type, self.user.name)

  @property
  def name(self):
    result = self.title or ''
    if self.artist:
      result += ' by {}'.format(self.artist)
    if not result:
      if self.type == SongTypes.Gmusic:
        result = self.song_id
      elif self.type == SongTypes.Youtube:
        result = self.url
    return result

  def create_embed(self):
    if self.stream and self.stream.is_playing():
      state = 'playing'
    elif self.stream and not self.stream.is_done():
      state = 'paused'
    elif self.stream and self.stream.is_done():
      state = 'stopped'
    else:
      state = 'loading'

    embed = discord.Embed()
    embed.timestamp = self.timestamp
    embed.set_author(name=self.user.name, icon_url=self.user.avatar_url)
    if state == 'loading':
      embed.title = '💫 Loading ...'
    elif state == 'playing':
      embed.title = '▶️ Now Playing'
    elif state == 'paused':
      embed.title = '⏸️ Paused'

    if self.type == SongTypes.Gmusic:
      lines = []
      lines.append('**Title** — {}'.format(self.title))
      lines.append('**Artist** — {}'.format(self.artist))
      lines.append('**Album** — {}'.format(self.album))
      lines.append('**Genre** — {}'.format(self.genre))
      embed.description = '\n'.join(lines)
      embed.colour = discord.Colour.orange()
    elif self.type == SongTypes.Youtube:
      embed.description = self.title or self.url
      embed.colour = discord.Colour.red()
    else:
      raise RuntimeError

    if self.image:
      embed.set_image(url=self.image)
    return embed

  async def create_stream(self, config, voice_client, after=None):
    if self.stream:
      raise RuntimeError('Song already has a stream')
    if self.type == SongTypes.Gmusic:
      try:
        url = self.gmusic.get_stream_url(self.song_id)
      except gmusicapi.exceptions.CallFailure as e:
        raise StreamNotCreatedError() from e
      self.stream = voice_client.create_ffmpeg_player(url, after=after)
    elif self.type == SongTypes.Youtube:
      try:
        self.stream = await voice_client.create_ytdl_player(self.url, after=after)
      except youtube_dl.utils.DownloadError as e:
        raise StreamNotCreatedError() from e
    else:
      raise RuntimeError

  async def pull_metadata(self):
    if self.type == SongTypes.Youtube:
      # TODO: Actually do stuff asynchronous here.
      ytdl = youtube_dl.YoutubeDL()
      data = ytdl.extract_info(self.url, download=False)
      self.title = data['title']
      self.image = data['thumbnail']
      self.artist = data['uploader']
      self.genre = next(iter(data.get('categories', [])), None)


class PlayerFactory:

  def __init__(self, client, config, logger):
    self.client = client
    self.config = config
    self.logger = logger
    self.players = []

  def get_player_for_voice_client(self, voice_client):
    """
    This is a normal function.

    Returns the #Player for a given #discord.VoiceClient *voice_client*.
    Creates a new #Player if none exists.
    """

    player = discord.utils.find(
      lambda x: x.voice_client == voice_client,
      self.players)
    if player is None:
      player = Player(self.client, self.config, self.logger, voice_client, self)
      self.players.append(player)
    return player

  async def get_player_for_server(self, server, voice_channel=None):
    """
    This is a coroutine function.

    Searches for the #Player for the server *server*. If the server currently
    has no #Player, #None is returned, unless a *voice_channel* is specified,
    in which case a #Player is created for that channel.

    The player is not automatically moved to the specified *voice_channel*
    if it already exists. Use #Player.voice_client.move_to() instead.
    """

    player = discord.utils.find(
      lambda x: x.voice_client.server == server,
      self.players)
    if voice_channel and not player:
      voice_client = await self.client.join_voice_channel(voice_channel)
      player = self.get_player_for_voice_client(voice_client)
    return player


class Player:
  """
  Wraps around a #discord.VoiceChannel and keeps track of the current stream.
  """

  Factory = PlayerFactory
  GmusicSong = SongTypes.Gmusic
  YoutubeSong = SongTypes.Youtube

  def __init__(self, client, config, logger, voice_client, factory):
    self.client = client
    self.loop = client.loop
    self.config = config
    self.logger = logger
    self.voice_client = voice_client
    self.lock = asyncio.Lock()
    self.current_song = None
    self.process_queue = True
    self.factory = factory
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
    next_song = None
    with await self.lock:
      self.process_queue = True
      if self.current_song and self.current_song.stream:
        self.current_song.stream.resume()
        await self.__update_current_song_message()
      else:
        next_song = self.current_song
        if not next_song and self.queue:
          next_song = self.queue.pop(0)
    if next_song:
      await self.__play_song(next_song)

  async def stop(self):
    with await self.lock:
      self.process_queue = False
    await self.__kill_stream()

  async def skip_song(self):
    with await self.lock:
      self.process_queue = True
    await self.__kill_stream()

  async def disconnect(self):
    if self.voice_client:
      await self.voice_client.disconnect()
    self.voice_client = None
    self.factory.players.remove(self)

  async def __update_current_song_message(self):
    if self.current_song and self.current_song.message:
      await self.client.edit_message(
        self.current_song.message,
        embed=self.current_song.create_embed()
      )

  async def __kill_stream(self):
    next_song = None
    with await self.lock:
      if self.current_song and self.current_song.stream:
        self.current_song.stream.stop()
      try:
        await self.__update_current_song_message()
      except Exception as e:
        self.logger.exception(e)
      self.current_song = None
      if self.process_queue and self.queue:
        next_song = self.queue.pop(0)
    if next_song:
      await self.__play_song(next_song)

  async def __play_song(self, song):
    if await self.is_playing():
      self.logger.error('can not play song, already playing another')
      return False

    with await self.lock:
      if not song.message:
        song.message = await self.client.send_message(song.channel, embed=song.create_embed())
      self.current_song = song

    after = lambda: asyncio.run_coroutine_threadsafe(self.__kill_stream(), self.loop)
    try:
      await song.create_stream(self.config, self.voice_client, after)
    except StreamNotCreatedError as exc:
      self.logger.exception(exc)
      self.current_song = None
      msg = '{} Something went wrong playing  **{}**.'
      msg = msg.format(song.user.mention, song.name)
      await self.client.delete_message(song.message)
      await self.client.send_message(song.channel, msg)
      return False

    song.stream.volume = self.config['general']['music_volume']
    song.stream.start()
    await self.__update_current_song_message()
    return True

  async def queue_song(self, type, data, user, channel, timestamp, gmusic=None):
    with await self.lock:
      song = Song(type, data, user, channel, timestamp, gmusic=gmusic)
      await song.pull_metadata()
      if self.current_song:
        self.queue.append(song)
        return song
    if not await self.__play_song(song):
      return None
    return song


module.exports = Player
