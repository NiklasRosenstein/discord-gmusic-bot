
"""
This module implements the #Player class which implements the business logic
for playing music in a Discord channel.
"""


from pony import orm
from quel.core.asyncio_utils import async_local
from quel.models import DiscordServer, QueuedSong
from quel.provider import available_providers

import asyncio
import logging
import urllib.parse
import weakref

DEFAULT_FFMPEG_OPTIONS = '-bufsize 128k'


class ServerManager:

  def __init__(self, client):
    self.servers = {}
    self.client = client

  async def get_server_data(self, server):
    data = self.servers.get(server.id)
    if not data:
      data = ServerData(self, server.id)
      self.servers[server.id] = data
      await data.update_providers()
    return data

  def get_voice_client(self, server):
    return self.get_server_data(server).voice_client

  async def create_voice_client(self, server, voice_channel, move=True):
    data = await self.get_server_data(server)
    if not data.voice_client:
      data.voice_client = await self.client.join_voice_channel(voice_channel)
      data.voice_channel = voice_channel
    elif move:
      await data.voice_client.move_to(voice_channel)
      data.voice_channel = voice_channel
    return data.voice_client

  async def message(self, message):
    channel = getattr(self.locals, 'channel', None)
    if channel:
      await self.client.send_message(channel, message)


class ServerData:
  """
  Represents a server (and the channel) where a stream is currently
  on playback.
  """

  def __init__(self, manager, id):
    self._manager = weakref.ref(manager)
    self.logger = logging.getLogger(__name__ + '.ServerData(id={})'.format(id))
    self.providers = {}
    self.provider_errors = {}
    self.id = id
    self.voice_channel = None
    self.voice_client = None
    self.stream = None
    self.song = None
    self.autoplay = True

  def get_db_object(self):
    return DiscordServer.get_or_create(self.id)

  async def update_providers(self):
    self.providers = {}
    self.provider_errors = {}
    with orm.db_session() as fp:
      self.logger.debug('Reinstalling providers ...')
      server = self.get_db_object()
      for provider_id, provider_cls in available_providers.items():
        options = server.get_provider_options(provider_id)
        need_options = provider_cls.get_options()
        missing_options = [k for k in need_options if k not in options]
        if missing_options:
          self.provider_errors[provider_id] = 'Missing options: ' + str(missing_options)
          continue

        kwargs = {k: options[k] for k in need_options if k in options}
        try:
          provider = provider_cls(**kwargs)
        except Exception as exc:
          self.provider_errors[provider_id] = 'Error creating provider: ' + str(exc)
          continue

        self.providers[provider_id] = provider

  @property
  def manager(self):
    return self._manager()

  async def _song_finished(self, loop):
    self.stream = None
    self.song = None
    if self.autoplay:
      await self.resume()

  async def is_playing(self):
    if self.stream:
      return self.stream.is_playing()
    return False

  async def pause(self):
    if self.stream:
      self.stream.pause()
    self.autoplay = False

  async def resume(self):
    self.autoplay = True
    if self.stream:
      if not self.stream.is_playing():
        self.stream.resume()
      return

    with orm.db_session():
      server = self.get_db_object()
      ffmpeg_options = server.options.get('ffmpeg.options', DEFAULT_FFMPEG_OPTIONS)
      song = server.pop_queue()

    if not song:
      return

    if not self.voice_channel:
      raise PlayError('You have not joined a voice channel.')

    provider = self.providers.get(song.provider_id)
    if not provider:
      raise PlayError('Provider "{}" for song "{}" is not installed.'
        .format(song.provider, song.url))

    loop = asyncio.get_running_loop()
    stream_url = await provider.get_stream_url(song)
    self.stream = self.voice_client.create_ffmpeg_player(
      stream_url,
      options=ffmpeg_options,
      after=lambda: asyncio.run_coroutine_threadsafe(self._song_finished(), loop)
    )

  async def queue_song_by_url(self, user, url, join_channel=None):
    urlinfo = urllib.parse.urlparse(url)
    for provider_id, provider in self.providers.items():
      if provider.matches_url(url, urlinfo):
        break
    else:
      return None

    try:
      song = await provider.resolve(url)
    except Exception as exc:
      self.logger.exception('Error resolving URL "{}"'.format(url))
      return None
    song = QueuedSong(user_id=user.id, provider_id=provider_id, **song.asdict())
    with orm.db_session():
      server = self.get_db_object()
      server.add_to_queue(song)
    if join_channel:
      self.voice_channel = join_channel
      self.voice_client = await self.manager.create_voice_client(
        self, join_channel, move=False)
    await self.resume()
    return song


class PlayError(Exception):
  pass
