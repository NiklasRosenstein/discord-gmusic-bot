
from pony import orm
from . import db
from .utils import get_or_create
from quel.provider.base import Song as _Song
from typing import *

import datetime
import nr.types.named


class QueuedSong(_Song):
  version: int = 1
  user_id: str
  provider_id: str
  date_queued: str = lambda: str(datetime.datetime.now())


class DiscordServer(db.Entity):
  id = orm.PrimaryKey(str)
  options = orm.Required(orm.Json, lazy=True)
  queue = orm.Required(orm.Json, lazy=True)

  @classmethod
  def get_or_create(cls, id):
    return get_or_create(cls, {'id': id}, options={}, queue=[])

  def pop_queue(self) -> Optional[QueuedSong]:
    while self.queue:
      song = self.queue.pop(0)  # TODO @NiklasRosensteinw will pony recognize the change in the list?
      if song['version'] == QueuedSong.version:
        return QueuedSong(**song)
    return None

  def add_to_queue(self, song: QueuedSong):
    assert isinstance(song, QueuedSong), type(song)
    self.queue.append(song.asdict())  # TODO @NiklasRosenstein

  def iter_queue(self) -> Iterable[QueuedSong]:
    for song in self.queue:
      if song['version'] == QueuedSong.version:
        yield QueudSong(**song)

  def get_provider_options(self, provider_id):
    providers = self.options.get('providers', {})
    return providers.get(provider_id, {})

  def set_provider_options(self, provider_id, options):
    providers = self.options.setdefault('providers', {})
    providers[provider_id] = options
