
from . import db
from pony import orm


class QueuedSong(db.Entity):
  server = orm.Required('DiscordServer')
  queued_by = orm.Required('User')
  provider = orm.Required(str)  # the provider ID
  url = orm.Required(str)
  playback_url = orm.Optional(str)  # sometimes the playback url can only be retrieved the moment it should be played
  duration = orm.Optional(int)  # in seconds
  title = orm.Optional(str)
  artist = orm.Optional(str)
  genre = orm.Optional(str)
  image_url = orm.Optional(str)
