
import asyncio
import discord
import logging


class Player:
  """
  Wraps around a #discord.VoiceChannel and keeps track of the current stream.
  """

  players = []

  @classmethod
  def get(cls, loop, voice_client):
    player = discord.utils.find(
      lambda x: x.voice_client == voice_client,
      cls.players)
    if player is None:
      player = cls(loop, voice_client)
      cls.players.append(player)
    return player

  @classmethod
  async def get_for_channel(cls, client, channel):
    # Find the existing voice client for the channel.
    voice_client = discord.utils.find(
      lambda x: x.server == channel.server,
      client.voice_clients)
    if voice_client and voice_client.channel != channel:
      voice_client.move_to(channel)
    elif not voice_client:
      voice_client = await client.join_voice_channel(channel)
    return cls.get(client.loop, voice_client)

  def __init__(self, loop, voice_client):
    self.loop = loop
    self.voice_client = voice_client
    self.stream = None
    self.lock = asyncio.Lock()
    self.done_callback = None
    self.message = None

  @property
  def server(self):
    return self.voice_client.server

  async def is_playing(self):
    with await self.lock:
      return self.stream and self.stream.is_playing()

  def pause(self):
    if self.stream:
      self.stream.pause()

  def resume(self):
    if self.stream:
      self.stream.resume()

  def stop(self):
    asyncio.run_coroutine_threadsafe(self.__kill_stream(), self.loop)

  async def start_ffmpeg_stream(self, *args, **kwargs):
    with await self.lock:
      if self.stream:
        raise RuntimeError('cant start a new stream if another is still playing')
    kwargs['after'] = lambda: asyncio.run_coroutine_threadsafe(self.__kill_stream(), self.loop)
    self.stream = self.voice_client.create_ffmpeg_player(*args, **kwargs)
    self.stream.start()

  async def __kill_stream(self):
    with await self.lock:
      if self.stream:
        self.stream.stop()
        self.stream = None
      if self.done_callback:
        try:
          self.done_callback()
        except Exception as e:
          logging.exception(e)
        finally:
          self.done_callback = None


module.exports = Player
