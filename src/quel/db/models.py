
from . import db
from .utils import durable_member
from quel.providers import ErrorProviderInstance, Song as _Song
from pony import orm

import asyncio
import datetime
import discord


class QueuedSong(_Song):
  user_id: str
  provider_id: str
  date_queued: str = lambda: str(datetime.datetime.now())


class Guild(db.Entity):
  id = orm.PrimaryKey(int, size=64)
  config = orm.Required(orm.Json, lazy=True)
  initialized = durable_member(bool)
  providers = durable_member(list)
  queue = durable_member(list)
  voice_client = durable_member(lambda: None)
  volume = durable_member(lambda: 0.5)

  def __init__(self, id, config=None):
    super().__init__(id=id, config=config or {})

  def init_providers(self, logger, providers, force=False):
    if self.initialized and not force:
      return
    self.providers = []
    for provider in providers:
      options = {k: self.config.get(provider.id + '.' + k)
                 for k in provider.get_option_names()}
      try:
        instance = provider.instantiate(options)
      except BaseException as exc:
        logger.exception('Exception instantiating provider "{}"'.format(provider.name))
        instance = ErrorProviderInstance(provider, '{}: {}'.format(type(exc).__name__, str(exc)))
      self.providers.append(instance)
    self.initialized = True

  def find_provider(self, provider_id):
    for provider in self.providers:
      if not provider.error and provider.id == provider_id:
        return provider
    return None

  def queue_song(self, song):
    assert isinstance(song, QueuedSong)
    self.queue.append(song)

  async def start_stream(self, stream_url):
    assert self.voice_client
    loop = asyncio.get_running_loop()
    source = discord.FFmpegPCMAudio(stream_url, options='-bufsize 128k')
    source = discord.PCMVolumeTransformer(source, self.volume)
    self.voice_client.play(source)

  def set_volume(self, volume):
    volume = max(0.0, min(1.0, float(volume)))
    self.volume = volume
    if self.voice_client and self.voice_client.source:
      self.voice_client.source.volume = volume
